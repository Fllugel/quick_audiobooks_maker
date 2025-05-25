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
from datetime import datetime

class AudiobookUI:
    def __init__(self):
        self.processor = TTSProcessor()
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
                    # Get text while preserving sentence structure
                    text = elem.get_text(separator=' ', strip=True)
                    if text:
                        paragraphs.append(text)
            
            # Join paragraphs with double newlines to create clear paragraph breaks
            text = "\n\n".join(paragraphs)
            
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
            return None, "Please upload a text file.", ""
        
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
                label="Select Sections to Process"
            )
            
            # Return the checkbox group and the status
            status_msg = f"Loaded {len(self.processor.get_sections())} sections successfully!"
            if dir_exists and not force_create:
                status_msg += " (Using existing output directory)"
            elif force_create:
                status_msg += " (Created new output directory)"
            return sections_checkbox, status_msg, safe_name
            
        except Exception as e:
            return None, f"Error: {str(e)}", ""
    
    def generate_audio(self, selected_sections, voice_display_name, speed, progress=gr.Progress()):
        """Generate audio for selected sections."""
        if not selected_sections:
            return None, "No sections selected."

        try:
            # Convert display name back to voice ID
            voice_id = self.voice_choices.get(voice_display_name)
            if not voice_id:
                return None, "Invalid voice selection."

            # Get the section numbers from the checkbox selections (e.g., "Section 1: preview..." -> 1)
            section_numbers_to_process = []
            for section_label in selected_sections:
                match = re.match(r"Section (\d+):", section_label)
                if match:
                    section_numbers_to_process.append(int(match.group(1)))

            # Sort section numbers to process in order
            section_numbers_to_process.sort()
            self.total_sections = len(section_numbers_to_process)

            # Reset files and index to start from the beginning
            self.generated_files = []  # Reset generated files list
            self.is_generating = True
            self.current_section_index = 0  # Start from the first section

            processed_count = 0
            # Iterate through sorted section numbers
            for section_idx in section_numbers_to_process:
                if not self.is_generating:
                    progress(processed_count / self.total_sections, desc=f"Stopped at section {section_idx}")
                    return self.generated_files, f"Generation stopped. Last processed: Section {section_idx-1}"

                idx = section_idx - 1  # Convert to 0-based index
                section_text = self.processor.get_section(idx)
                if section_text is None:
                    continue
                    
                output_path = self.current_output_dir / f"section_{section_idx}.wav"
                self.processor.generate_speech(
                    section_text,
                    output_path,
                    voice=voice_id,
                    speed=speed
                )
                self.generated_files.append(str(output_path))
                self.current_section_index = section_idx  # Update to the last processed section number
                processed_count += 1
                progress(processed_count / self.total_sections, desc=f"Processing Section {section_idx}")

            self.is_generating = False
            last_section = self.processor.get_last_generated_section()
            if processed_count > 0:
                return self.generated_files, f"Generated {len(self.generated_files)} audio files successfully! Last section: {last_section + 1}"
            else:
                return self.generated_files, "All selected sections already processed."

        except Exception as e:
            self.is_generating = False
            return None, f"Error: {str(e)}"
    
    def stop_generation(self):
        """Stop the current generation process."""
        self.is_generating = False
        return "Generation stopped. Click 'Continue Generation' to resume."
    
    def continue_generation(self, selected_sections, voice_display_name, speed, progress=gr.Progress()):
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
                    
                output_path = self.current_output_dir / f"section_{section_idx}.wav"
                self.processor.generate_speech(
                    section_text,
                    output_path,
                    voice=voice_id,
                    speed=speed
                )
                self.generated_files.append(str(output_path))
                self.current_section_index = section_idx
                processed_count += 1
                progress(processed_count / self.total_sections, desc=f"Processing Section {section_idx}")

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
            # Create new directory with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_output_dir = self.base_output_dir / f"{safe_name}_{timestamp}"
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
    
    def regenerate_section(self, section_number, voice_display_name, speed, progress=gr.Progress()):
        """Regenerate a specific section."""
        if not section_number:
            return None, "Please enter a section number."
        
        try:
            # Convert display name back to voice ID
            voice_id = self.voice_choices.get(voice_display_name)
            if not voice_id:
                return None, "Invalid voice selection."

            section_idx = int(section_number) - 1  # Convert to 0-based index
            output_path = self.current_output_dir / f"section_{section_number}.wav"
            
            progress(0, desc="Starting regeneration...")
            if self.processor.regenerate_section(section_idx, output_path, voice_id, speed):
                progress(1, desc="Regeneration complete")
                return self.generated_files, f"Successfully regenerated section {section_number}"
            else:
                return self.generated_files, f"Invalid section number: {section_number}"
                
        except ValueError:
            return self.generated_files, "Please enter a valid section number."
        except Exception as e:
            return self.generated_files, f"Error: {str(e)}"

    def regenerate_from_section(self, start_section, voice_display_name, speed, progress=gr.Progress()):
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
                
                output_path = self.current_output_dir / f"section_{section_idx + 1}.wav"
                if self.processor.regenerate_section(section_idx, output_path, voice_id, speed):
                    output_files.append(str(output_path))
                    processed_count += 1
                    progress(processed_count / total_sections, desc=f"Processing Section {section_idx + 1}")
            
            if output_files:
                return output_files, f"Successfully regenerated sections from {start_section} onwards"
            else:
                return self.generated_files, f"Invalid section number: {start_section}"
                
        except ValueError:
            return self.generated_files, "Please enter a valid section number."
        except Exception as e:
            return self.generated_files, f"Error: {str(e)}"
    
    def create_ui(self):
        """Create and return the Gradio interface."""
        with gr.Blocks(title="Kokoro Audiobook Generator", css="""
            .gradio-container { 
                max-width: 100% !important; 
            }
            .sections-container { 
                height: 800px !important; 
                overflow-y: auto !important;
                max-height: 800px !important;
            }
            .sections-container > div {
                max-height: none !important;
            }
        """) as interface:
            gr.Markdown("<div style='margin-top: 20px;'></div>")  # Add spacing
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
                    
                    gr.Markdown("### Generation Controls")
                    with gr.Row():
                        generate_btn = gr.Button("Generate Audio", variant="primary")
                        stop_btn = gr.Button("Stop Generation", variant="stop")
                        continue_btn = gr.Button("Continue Generation", variant="secondary")
                    
                    gr.Markdown("### Regeneration Controls")
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
                    load_status = gr.Textbox(label="Status")
            
            # Event handlers
            def handle_file_upload(file):
                if file is None:
                    return None, "Please upload a text file.", ""
                
                # Get the original filename without extension
                book_name = Path(file.name).stem
                output_dir = self.base_output_dir / re.sub(r'[<>:"/\\|?*]', '_', book_name)
                
                if output_dir.exists():
                    # Show confirmation dialog
                    gr.Info("Output directory already exists. Do you want to overwrite it?")
                    return gr.update(visible=True), gr.update(visible=True), file
                else:
                    return self.load_file(file, False)
            
            confirm_btn = gr.Button("Yes, Overwrite", variant="stop", visible=False)
            cancel_btn = gr.Button("No, Use Existing", variant="secondary", visible=False)
            
            file_input.change(
                fn=handle_file_upload,
                inputs=[file_input],
                outputs=[confirm_btn, cancel_btn, file_input]
            )
            
            confirm_btn.click(
                fn=lambda x: self.load_file(x, True),
                inputs=[file_input],
                outputs=[sections_checkbox, load_status, output_folder]
            )
            
            cancel_btn.click(
                fn=lambda x: self.load_file(x, False),
                inputs=[file_input],
                outputs=[sections_checkbox, load_status, output_folder]
            )
            
            update_folder_btn.click(
                fn=self.update_output_dir,
                inputs=[output_folder],
                outputs=[load_status]
            )
            
            generate_btn.click(
                fn=self.generate_audio,
                inputs=[sections_checkbox, voice_dropdown, speed_slider],
                outputs=[generate_status]
            )
            
            stop_btn.click(
                fn=self.stop_generation,
                inputs=[],
                outputs=[generate_status]
            )
            
            continue_btn.click(
                fn=self.continue_generation,
                inputs=[sections_checkbox, voice_dropdown, speed_slider],
                outputs=[generate_status]
            )
            
            regenerate_section_btn.click(
                fn=self.regenerate_section,
                inputs=[section_number, voice_dropdown, speed_slider],
                outputs=[generate_status]
            )
            
            regenerate_from_btn.click(
                fn=self.regenerate_from_section,
                inputs=[section_number, voice_dropdown, speed_slider],
                outputs=[generate_status]
            )
        
        return interface

def main():
    ui = AudiobookUI()
    interface = ui.create_ui()
    interface.launch(share=True)

if __name__ == "__main__":
    main() 