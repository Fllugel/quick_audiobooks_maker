import gradio as gr
from pathlib import Path
import os
import re
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import shutil
import subprocess
import tempfile
from .tts_processor import TTSProcessor
from .s2s_processor import RVCProcessor
from datetime import datetime

class AudiobookUI:
    def __init__(self):
        self.processor = TTSProcessor()
        self.rvc_processor = RVCProcessor()
        # Create voice choices with display names
        self.voice_choices = {
            self.processor.get_voice_display_name(voice_id): voice_id
            for voice_id in self.processor.available_voices
        }
        self.available_voices = list(self.voice_choices.keys())
        self.current_output_dir = None
        self.generated_files = []
        self.is_generating = False
        self.current_section_index = 0
        self.total_sections = 0
        # Create base output directory
        self.base_output_dir = Path("audiobooks")
        self.base_output_dir.mkdir(exist_ok=True)
        # Create RVC models directory
        self.rvc_models_dir = Path("rvc_models")
        self.rvc_models_dir.mkdir(exist_ok=True)
        # Initialize RVC model choices
        self.rvc_model_choices = {}
        self.update_rvc_models()
    
    def create_output_directory(self, book_name, force_create=False):
        """Create a directory for the book output."""
        # Clean the book name to make it filesystem-safe
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', book_name)
        output_dir = self.base_output_dir / safe_name
        
        # Check if directory exists
        if output_dir.exists() and not force_create:
            return output_dir, safe_name, True  # Return True to indicate directory exists
        else:
            if output_dir.exists():
                # Remove existing directory and its contents
                shutil.rmtree(output_dir)
            output_dir.mkdir(exist_ok=True)
            # Create images subdirectory
            images_dir = output_dir / "images"
            images_dir.mkdir(exist_ok=True)
            return output_dir, safe_name, False  # Return False to indicate new directory
    
    def extract_text_from_epub(self, epub_path):
        """Extract text from EPUB file preserving document order and paragraph structure."""
        try:
            book = epub.read_epub(epub_path)
            
            # Build a map from spine IDs to items for quick lookup
            id_map = {item.get_id(): item for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT)}
            
            paragraphs = []
            # Process items in spine order to maintain reading sequence
            for spine_id, _ in book.spine:
                item = id_map.get(spine_id)
                if not item:
                    continue
                    
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                
                # Process elements in document order, preserving the sequence of headings and paragraphs
                for elem in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']):
                    # Get text while preserving paragraph structure
                    text = elem.get_text(separator=' ', strip=True)
                    if text:
                        # Add extra newline for headings to ensure they start new paragraphs
                        if elem.name.startswith('h'):
                            paragraphs.append('\n' + text + '\n')
                        else:
                            paragraphs.append(text)
            
            # Join paragraphs with double newlines to create clear paragraph breaks
            text = '\n\n'.join(paragraphs)
            
            # Clean up any excessive whitespace within paragraphs
            text = re.sub(r'[ \t]+', ' ', text)  # Normalize spaces within lines
            text = re.sub(r'\n{3,}', '\n\n', text)  # Remove excessive paragraph breaks
            text = text.strip()
            
            return text
            
        except Exception as e:
            print(f"Error extracting text from EPUB: {str(e)}")
            return ""
    
    def extract_images_from_epub(self, epub_path, output_dir):
        """Extract images from EPUB file and save them to the output directory."""
        book = epub.read_epub(epub_path)
        images_dir = output_dir / "images"
        images_dir.mkdir(exist_ok=True)
        
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_IMAGE:
                # Get the filename from the path and clean it
                filename = Path(item.get_name()).name
                # Create a safe filename by removing any problematic characters
                safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                image_path = images_dir / safe_filename
                try:
                    with open(image_path, 'wb') as f:
                        f.write(item.get_content())
                except Exception as e:
                    print(f"Warning: Could not save image {filename}: {str(e)}")
    
    def load_file(self, file, force_create=False):
        """Load and split the text file into sections."""
        if file is None:
            return None, ""
        
        try:
            # Get the original filename without extension
            book_name = Path(file.name).stem
            
            # Create output directory
            self.current_output_dir, safe_name, dir_exists = self.create_output_directory(book_name, force_create)
            
            # Handle different file types
            file_path = Path(file.name)
            if file_path.suffix.lower() == '.epub':
                # Extract images from EPUB first
                self.extract_images_from_epub(file_path, self.current_output_dir)
                # Extract and process text using built-in functionality
                content = self.extract_text_from_epub(file_path)
            else:
                # Read text file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            # Split into sections using processor's split_text
            self.processor.split_text(content)
            
            # Create a list of section choices with text previews
            section_choices = []
            for i, section in enumerate(self.processor.get_sections()):
                # Get first 1000 characters of the section for preview
                preview = section[:1000].replace('\n', ' ').strip()
                if len(section) > 1000:
                    preview += "..."
                section_choices.append(f"Section {i+1}: {preview}")
            
            # Create checkbox group for selection
            sections_checkbox = gr.CheckboxGroup(
                choices=section_choices,
                value=section_choices,  # Select all by default
                label="Select Sections to Process",
                elem_classes=["sections-container"]
            )
            
            return sections_checkbox, safe_name
            
        except Exception as e:
            return None, ""
    
    def generate_audio(self, selected_sections, voice_display_name, speed, use_rvc, rvc_model_name, f0_up_key, f0_method, index_rate, progress=gr.Progress()):
        """Generate audio for selected sections."""
        if not selected_sections:
            return None, "No sections selected."

        try:
            # Convert display name back to voice ID
            voice_id = self.voice_choices.get(voice_display_name)
            if not voice_id:
                return None, "Invalid voice selection."

            # Get the section numbers from the checkbox selections
            section_numbers_to_process = []
            for section_label in selected_sections:
                match = re.match(r"Section (\d+):", section_label)
                if match:
                    section_numbers_to_process.append(int(match.group(1)))

            # Sort section numbers to process in order
            section_numbers_to_process.sort()
            self.total_sections = len(section_numbers_to_process)

            # Reset files and index to start from the beginning
            self.generated_files = []
            self.is_generating = True
            self.current_section_index = 0

            # Load RVC model if enabled
            if use_rvc and rvc_model_name:
                rvc_model_path = self.rvc_model_choices.get(rvc_model_name)
                if not rvc_model_path:
                    return None, "Invalid RVC model selection"
                if not self.rvc_processor.load_model(rvc_model_path):
                    return None, "Failed to load RVC model"

            processed_count = 0
            # Iterate through sorted section numbers
            for section_idx in section_numbers_to_process:
                if not self.is_generating:
                    return None, f"Generation stopped at section {self.current_section_index}"

                idx = section_idx - 1  # Convert to 0-based index
                section_text = self.processor.get_section(idx)
                if section_text is None:
                    continue
                    
                # Generate initial audio
                temp_output = self.current_output_dir / f"temp_section_{section_idx}.wav"
                final_output = self.current_output_dir / f"section_{section_idx}.wav"
                
                # Generate speech and check if it was successful
                if not self.processor.generate_speech(
                    section_text,
                    temp_output,
                    voice=voice_id,
                    speed=speed
                ):
                    print(f"Failed to generate speech for section {section_idx}")
                    continue
                
                # Check if temp file exists before proceeding
                if not temp_output.exists():
                    print(f"Temporary file not created for section {section_idx}")
                    continue
                
                # Apply RVC if enabled
                if use_rvc and rvc_model_name:
                    if self.rvc_processor.convert_audio(
                        temp_output,
                        final_output,
                        f0_up_key=f0_up_key,
                        f0_method=f0_method,
                        index_rate=index_rate
                    ):
                        # Remove temporary file after successful conversion
                        if temp_output.exists():
                            try:
                                temp_output.unlink()
                            except Exception as e:
                                print(f"Warning: Could not remove temporary file: {str(e)}")
                    else:
                        # If RVC conversion fails, use the original file
                        if temp_output.exists():
                            try:
                                if final_output.exists():
                                    final_output.unlink()
                                temp_output.rename(final_output)
                            except Exception as e:
                                print(f"Warning: Could not rename temporary file: {str(e)}")
                else:
                    # If RVC is not enabled, just rename the temp file
                    if temp_output.exists():
                        try:
                            if final_output.exists():
                                final_output.unlink()
                            temp_output.rename(final_output)
                        except Exception as e:
                            print(f"Warning: Could not rename temporary file: {str(e)}")
                
                if final_output.exists():
                    self.generated_files.append(str(final_output))
                    self.current_section_index = section_idx
                    processed_count += 1
                    progress(processed_count / self.total_sections, desc=f"Processing section {section_idx}")

            if processed_count > 0:
                return None, f"Audio generation completed successfully! Generated {processed_count} sections."
            else:
                return None, "Failed to generate any audio sections."

        except Exception as e:
            return None, f"Error during audio generation: {str(e)}"
    
    def stop_generation(self):
        """Stop the current generation process."""
        self.is_generating = False
        if self.current_section_index > 0:
            return f"Generation stopped at section {self.current_section_index}"
        return "Generation stopped"
    
    def continue_generation(self, selected_sections, voice_display_name, speed, use_rvc, rvc_model_name, f0_up_key, f0_method, index_rate, progress=gr.Progress()):
        """Continue generation from where it was stopped."""
        if not selected_sections:
            return None, "No sections selected."
        
        try:
            # Convert display name back to voice ID
            voice_id = self.voice_choices.get(voice_display_name)
            if not voice_id:
                return None, "Invalid voice selection."

            # Get the section numbers from the checkbox selections
            section_numbers_to_process = []
            for section_label in selected_sections:
                match = re.match(r"Section (\d+):", section_label)
                if match:
                    section_num = int(match.group(1))
                    if section_num > self.current_section_index:
                        section_numbers_to_process.append(section_num)

            if not section_numbers_to_process:
                return self.generated_files, "No remaining sections to process."

            # Sort section numbers to process in order
            section_numbers_to_process.sort()
            self.total_sections = len(section_numbers_to_process)

            self.is_generating = True
            processed_count = 0

            for section_idx in section_numbers_to_process:
                if not self.is_generating:
                    progress(processed_count / self.total_sections, desc=f"Stopped at section {section_idx}")
                    return self.generated_files, f"Generation stopped. Last processed: Section {section_idx-1}"

                idx = section_idx - 1  # Convert to 0-based index
                section_text = self.processor.get_section(idx)
                if section_text is None:
                    continue
                    
                # Generate initial audio
                temp_output = self.current_output_dir / f"temp_section_{section_idx}.wav"
                final_output = self.current_output_dir / f"section_{section_idx}.wav"
                
                self.processor.generate_speech(
                    section_text,
                    temp_output,
                    voice=voice_id,
                    speed=speed
                )
                
                # Apply RVC if enabled
                if use_rvc and rvc_model_name:
                    if self.rvc_processor.convert_audio(
                        temp_output,
                        final_output,
                        f0_up_key=f0_up_key,
                        f0_method=f0_method,
                        index_rate=index_rate
                    ):
                        # Remove temporary file after successful conversion
                        temp_output.unlink()
                    else:
                        # If RVC conversion fails, use the original file
                        temp_output.rename(final_output)
                else:
                    # If RVC is not enabled, just rename the temp file
                    temp_output.rename(final_output)
                
                self.generated_files.append(str(final_output))
                self.current_section_index = section_idx
                processed_count += 1
                progress(processed_count / self.total_sections, desc=f"Processing section {section_idx}")

            self.is_generating = False
            if processed_count > 0:
                return self.generated_files, f"Generated {processed_count} additional audio files successfully! Last section: {section_idx}"
            else:
                return self.generated_files, "No new sections were processed."

        except Exception as e:
            self.is_generating = False
            return None, f"Error: {str(e)}"
    
    def update_output_dir(self, folder_name):
        """Update the output directory name."""
        if not folder_name:
            return "Please enter a folder name."
        
        try:
            # Clean the folder name
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', folder_name)
            # Create new directory without timestamp
            new_output_dir = self.base_output_dir / safe_name
            new_output_dir.mkdir(exist_ok=True)
            
            # If we have an existing output dir and it's empty, remove it
            if self.current_output_dir and self.current_output_dir.exists():
                if not any(self.current_output_dir.iterdir()):
                    self.current_output_dir.rmdir()
            
            self.current_output_dir = new_output_dir
            return f"Output folder updated to: {self.current_output_dir}"
        except Exception as e:
            return f"Error updating folder name: {str(e)}"
    
    def get_selected_section_text(self, selected_sections):
        """Get the text content of the first selected section."""
        if not selected_sections:
            return "No section selected."
        
        try:
            # Get the section number from the first selected item
            first_selected_label = selected_sections[0]
            match = re.match(r"Section (\d+):", first_selected_label)
            if match:
                section_num = int(match.group(1))
                idx = section_num - 1 # Convert to 0-based index
                section_text = self.processor.get_section(idx)
                if section_text is not None:
                    return section_text
                else:
                    return "Invalid section selected."
            else:
                return "Could not parse selected section."
        except Exception as e:
            return f"Error getting section text: {str(e)}"
    
    def regenerate_section(self, section_number, voice_display_name, speed, use_rvc, rvc_model_name, f0_up_key, f0_method, index_rate, progress=gr.Progress()):
        """Regenerate a specific section."""
        if not section_number:
            return None, "Please enter a section number."
        
        try:
            # Convert display name back to voice ID
            voice_id = self.voice_choices.get(voice_display_name)
            if not voice_id:
                return None, "Invalid voice selection."

            section_idx = int(section_number) - 1  # Convert to 0-based index
            temp_output = self.current_output_dir / f"temp_section_{section_number}.wav"
            final_output = self.current_output_dir / f"section_{section_number}.wav"
            
            progress(0, desc="Starting regeneration...")
            
            # Generate speech to temporary file
            if not self.processor.generate_speech(
                self.processor.get_section(section_idx),
                temp_output,
                voice=voice_id,
                speed=speed
            ):
                return self.generated_files, f"Failed to generate speech for section {section_number}"
            
            # Apply RVC if enabled
            if use_rvc and rvc_model_name:
                if self.rvc_processor.convert_audio(
                    temp_output,
                    final_output,
                    f0_up_key=f0_up_key,
                    f0_method=f0_method,
                    index_rate=index_rate
                ):
                    # Remove temporary file after successful conversion
                    if temp_output.exists():
                        try:
                            temp_output.unlink()
                        except Exception as e:
                            print(f"Warning: Could not remove temporary file: {str(e)}")
                else:
                    # If RVC conversion fails, use the original file
                    if temp_output.exists():
                        try:
                            if final_output.exists():
                                final_output.unlink()
                            temp_output.rename(final_output)
                        except Exception as e:
                            print(f"Warning: Could not rename temporary file: {str(e)}")
            else:
                # If RVC is not enabled, just rename the temp file
                if temp_output.exists():
                    try:
                        if final_output.exists():
                            final_output.unlink()
                        temp_output.rename(final_output)
                    except Exception as e:
                        print(f"Warning: Could not rename temporary file: {str(e)}")
            
            progress(1, desc="Regeneration complete")
            return self.generated_files, f"Successfully regenerated section {section_number}"
                
        except ValueError:
            return self.generated_files, "Please enter a valid section number."
        except Exception as e:
            return self.generated_files, f"Error: {str(e)}"

    def regenerate_from_section(self, start_section, voice_display_name, speed, use_rvc, rvc_model_name, f0_up_key, f0_method, index_rate, progress=gr.Progress()):
        """Regenerate all sections from a specific section onwards."""
        if not start_section:
            return None, "Please enter a starting section number."
        
        try:
            # Convert display name back to voice ID
            voice_id = self.voice_choices.get(voice_display_name)
            if not voice_id:
                return None, "Invalid voice selection."

            start_idx = int(start_section) - 1  # Convert to 0-based index
            total_sections = len(self.processor.get_sections()) - start_idx
            processed_count = 0
            
            output_files = []
            for section_idx in range(start_idx, len(self.processor.get_sections())):
                if not self.is_generating:
                    progress(processed_count / total_sections, desc=f"Stopped at section {section_idx + 1}")
                    return output_files, f"Regeneration stopped. Last processed: Section {section_idx}"
                
                section_number = section_idx + 1
                temp_output = self.current_output_dir / f"temp_section_{section_number}.wav"
                final_output = self.current_output_dir / f"section_{section_number}.wav"
                
                # Generate speech to temporary file
                if not self.processor.generate_speech(
                    self.processor.get_section(section_idx),
                    temp_output,
                    voice=voice_id,
                    speed=speed
                ):
                    print(f"Failed to generate speech for section {section_number}")
                    continue
                
                # Apply RVC if enabled
                if use_rvc and rvc_model_name:
                    if self.rvc_processor.convert_audio(
                        temp_output,
                        final_output,
                        f0_up_key=f0_up_key,
                        f0_method=f0_method,
                        index_rate=index_rate
                    ):
                        # Remove temporary file after successful conversion
                        if temp_output.exists():
                            try:
                                temp_output.unlink()
                            except Exception as e:
                                print(f"Warning: Could not remove temporary file: {str(e)}")
                    else:
                        # If RVC conversion fails, use the original file
                        if temp_output.exists():
                            try:
                                if final_output.exists():
                                    final_output.unlink()
                                temp_output.rename(final_output)
                            except Exception as e:
                                print(f"Warning: Could not rename temporary file: {str(e)}")
                else:
                    # If RVC is not enabled, just rename the temp file
                    if temp_output.exists():
                        try:
                            if final_output.exists():
                                final_output.unlink()
                            temp_output.rename(final_output)
                        except Exception as e:
                            print(f"Warning: Could not rename temporary file: {str(e)}")
                
                if final_output.exists():
                    output_files.append(str(final_output))
                    processed_count += 1
                    progress(processed_count / total_sections, desc=f"Processing Section {section_number}")
            
            if output_files:
                return output_files, f"Successfully regenerated sections from {start_section} onwards"
            else:
                return self.generated_files, f"Invalid section number: {start_section}"
                
        except ValueError:
            return self.generated_files, "Please enter a valid section number."
        except Exception as e:
            return self.generated_files, f"Error: {str(e)}"
    
    def update_rvc_models(self):
        """Update the list of available RVC models."""
        models = self.rvc_processor.get_available_models()
        self.rvc_model_choices = {model["name"]: model["path"] for model in models}
        return list(self.rvc_model_choices.keys())

    def create_ui(self):
        """Create the Gradio interface."""
        with gr.Blocks(title="Kokoro Audiobook Generator", css="""
            .gradio-container { 
                max-width: 100% !important; 
            }
            .sections-container { 
                height: 1200px !important; 
                overflow-y: auto !important;
                max-height: 1200px !important;
            }
            .sections-container > div {
                max-height: none !important;
            }
            .sections-container label {
                min-height: 24px !important;
                display: block !important;
                margin-bottom: 4px !important;
                width: 100% !important;
            }
            .sections-container .checkbox-group {
                display: flex !important;
                flex-direction: column !important;
            }
        """) as interface:
            gr.Markdown("<div style='margin-top: 20px;'></div>")  
            gr.Markdown("# 🎧 Kokoro Audiobook Generator")
            
            with gr.Row():
                # Left column: Settings
                with gr.Column(scale=1):
                    file_input = gr.File(
                        label="Upload Text File",
                        file_types=[".txt", ".epub"]
                    )
                    output_folder = gr.Textbox(
                        label="Output Folder Name",
                        placeholder="Will be set to book name when file is loaded"
                    )
                    with gr.Row():
                        update_folder_btn = gr.Button("Update Folder Name", variant="secondary")
                    
                    gr.Markdown("### Voice Settings")
                    voice_dropdown = gr.Dropdown(
                        choices=self.available_voices,
                        value=self.available_voices[0],
                        label="Select Voice"
                    )
                    speed_slider = gr.Slider(
                        minimum=0.5,
                        maximum=2.0,
                        value=1.0,
                        step=0.1,
                        label="Speech Speed"
                    )
                    
                    gr.Markdown("### RVC Settings")
                    with gr.Group():
                        use_rvc = gr.Checkbox(label="Enable RVC Voice Conversion", value=False)
                        rvc_model = gr.Dropdown(
                            choices=self.update_rvc_models(),
                            label="RVC Model",
                            visible=False
                        )
                        f0_up_key = gr.Slider(
                            minimum=-12,
                            maximum=12,
                            value=0,
                            step=1,
                            label="Pitch Shift (semitones)",
                            visible=False
                        )
                        f0_method = gr.Dropdown(
                            choices=["harvest", "crepe", "rmvpe", "pm"],
                            value="rmvpe",
                            label="Pitch Extraction Method",
                            visible=False
                        )
                        index_rate = gr.Slider(
                            minimum=0.0,
                            maximum=1.0,
                            value=0.5,
                            step=0.1,
                            label="Index Rate",
                            visible=False
                        )
                    
                    gr.Markdown("### Generation Controls")
                    with gr.Row():
                        generate_btn = gr.Button("Generate Audio", variant="primary")
                        stop_btn = gr.Button("Stop Generation", variant="stop")
                        continue_btn = gr.Button("Continue Generation", variant="secondary")
                    
                    with gr.Accordion("Regeneration Controls", open=False):
                        with gr.Row():
                            with gr.Column(scale=1):
                                section_number = gr.Number(
                                    label="Section Number",
                                    precision=0
                                )
                            with gr.Column(scale=2):
                                with gr.Row():
                                    regenerate_section_btn = gr.Button("Regenerate This Section", variant="secondary")
                                    regenerate_from_btn = gr.Button("Regenerate From This Section", variant="secondary")
                    
                    generate_status = gr.Textbox(label="Generation Status")
                
                # Right column: Sections
                with gr.Column(scale=2):
                    # CheckboxGroup for selecting sections by number
                    sections_checkbox = gr.CheckboxGroup(
                        choices=[],
                        value=[],
                        label="Select Sections to Process",
                        elem_classes=["sections-container"]
                    )
            
            # Event handlers
            def handle_file_upload(file):
                if file is None:
                    return None, ""
                return self.load_file(file, True)
            
            file_input.change(
                fn=handle_file_upload,
                inputs=[file_input],
                outputs=[sections_checkbox, output_folder]
            )
            
            update_folder_btn.click(
                fn=self.update_output_dir,
                inputs=[output_folder],
                outputs=[generate_status]
            )
            
            # Show/hide RVC controls based on checkbox
            def toggle_rvc_controls(use_rvc):
                return {
                    rvc_model: gr.update(visible=use_rvc),
                    f0_up_key: gr.update(visible=use_rvc),
                    f0_method: gr.update(visible=use_rvc),
                    index_rate: gr.update(visible=use_rvc)
                }
            
            use_rvc.change(
                fn=toggle_rvc_controls,
                inputs=[use_rvc],
                outputs=[rvc_model, f0_up_key, f0_method, index_rate]
            )
            
            # Update RVC models list when directory changes
            def update_rvc_models():
                models = self.rvc_processor.get_available_models()
                self.rvc_model_choices = {model["name"]: model["path"] for model in models}
                return gr.update(choices=list(self.rvc_model_choices.keys()))
            
            rvc_model.change(
                fn=update_rvc_models,
                inputs=[],
                outputs=[rvc_model]
            )
            
            generate_btn.click(
                fn=self.generate_audio,
                inputs=[
                    sections_checkbox,
                    voice_dropdown,
                    speed_slider,
                    use_rvc,
                    rvc_model,
                    f0_up_key,
                    f0_method,
                    index_rate
                ],
                outputs=[generate_status]
            )
            
            stop_btn.click(
                fn=self.stop_generation,
                inputs=[],
                outputs=[generate_status]
            )
            
            continue_btn.click(
                fn=self.continue_generation,
                inputs=[
                    sections_checkbox,
                    voice_dropdown,
                    speed_slider,
                    use_rvc,
                    rvc_model,
                    f0_up_key,
                    f0_method,
                    index_rate
                ],
                outputs=[generate_status]
            )
            
            regenerate_section_btn.click(
                fn=self.regenerate_section,
                inputs=[section_number, voice_dropdown, speed_slider, use_rvc, rvc_model, f0_up_key, f0_method, index_rate],
                outputs=[generate_status]
            )
            
            regenerate_from_btn.click(
                fn=self.regenerate_from_section,
                inputs=[section_number, voice_dropdown, speed_slider, use_rvc, rvc_model, f0_up_key, f0_method, index_rate],
                outputs=[generate_status]
            )
        
        return interface

def main():
    ui = AudiobookUI()
    interface = ui.create_ui()
    interface.launch(share=True)

if __name__ == "__main__":
    main() 