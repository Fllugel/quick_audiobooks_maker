import re
from pathlib import Path
import gradio as gr

class AudioGenerator:
    def __init__(self, processor, rvc_processor, output_dir=None):
        self.processor = processor
        self.rvc_processor = rvc_processor
        self.current_output_dir = output_dir
        self.is_generating = False
        self.current_section_index = 0
        self.total_sections = 0
        self.generated_files = []
    
    def set_output_dir(self, output_dir):
        """Set the current output directory."""
        self.current_output_dir = output_dir
    
    def generate_audio(self, sections_text, voice_display_name, speed, use_rvc, rvc_model_name, f0_up_key, f0_method, index_rate, progress=gr.Progress()):
        """Generate audio for sections."""
        if sections_text is None or sections_text.empty:
            return [], "No sections to process."

        try:
            # Convert display name back to voice ID
            voice_id = voice_display_name  # The display name is already the voice ID in TTSProcessor
            if not voice_id:
                return [], "Invalid voice selection."

            # Get all sections
            sections = self.processor.get_sections()
            if not sections:
                return [], "No sections available."

            # Reset files and index to start from the beginning
            self.generated_files = []
            self.is_generating = True
            self.current_section_index = 0
            self.total_sections = len(sections)

            # Load RVC model if enabled
            if use_rvc and rvc_model_name:
                rvc_model_path = self.rvc_processor.model_choices.get(rvc_model_name)
                if not rvc_model_path:
                    return [], "Invalid RVC model selection"
                if not self.rvc_processor.load_model(rvc_model_path):
                    return [], "Failed to load RVC model"

            processed_count = 0
            # Process each section
            for idx, section_text in enumerate(sections):
                if not self.is_generating:
                    return self.generated_files, f"Generation stopped at section {self.current_section_index}"

                section_number = idx + 1
                # Generate initial audio
                temp_output = self.current_output_dir / f"temp_section_{section_number}.wav"
                final_output = self.current_output_dir / f"section_{section_number}.wav"
                
                # Remove any existing files
                if temp_output.exists():
                    temp_output.unlink()
                if final_output.exists():
                    final_output.unlink()
                
                # Generate speech and check if it was successful
                if not self.processor.generate_speech(
                    section_text,
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
                            temp_output.unlink()
                    else:
                        # If RVC conversion fails, use the original file
                        if temp_output.exists():
                            temp_output.rename(final_output)
                else:
                    # If RVC is not enabled, just rename the temp file
                    if temp_output.exists():
                        temp_output.rename(final_output)
                
                if final_output.exists():
                    self.generated_files.append(str(final_output))
                    self.current_section_index = section_number
                    processed_count += 1
                    progress(processed_count / self.total_sections, desc=f"Processing section {section_number}")

            if processed_count > 0:
                return self.generated_files, f"Audio generation completed successfully! Generated {processed_count} sections."
            else:
                return [], "Failed to generate any audio sections."

        except Exception as e:
            return [], f"Error during audio generation: {str(e)}"
    
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
            voice_id = voice_display_name  # The display name is already the voice ID in TTSProcessor
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
            return [], f"Error: {str(e)}"
    
    def regenerate_section(self, section_number, voice_display_name, speed, use_rvc, rvc_model_name, f0_up_key, f0_method, index_rate, progress=gr.Progress()):
        """Regenerate a specific section."""
        if not section_number:
            return None, "Please enter a section number."
        
        try:
            # Convert display name back to voice ID
            voice_id = voice_display_name  # The display name is already the voice ID in TTSProcessor
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
                        temp_output.unlink()
                else:
                    # If RVC conversion fails, use the original file
                    if temp_output.exists():
                        if final_output.exists():
                            final_output.unlink()
                        temp_output.rename(final_output)
            else:
                # If RVC is not enabled, just rename the temp file
                if temp_output.exists():
                    if final_output.exists():
                        final_output.unlink()
                    temp_output.rename(final_output)
            
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
            voice_id = voice_display_name  # The display name is already the voice ID in TTSProcessor
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
                            temp_output.unlink()
                    else:
                        # If RVC conversion fails, use the original file
                        if temp_output.exists():
                            if final_output.exists():
                                final_output.unlink()
                            temp_output.rename(final_output)
                else:
                    # If RVC is not enabled, just rename the temp file
                    if temp_output.exists():
                        if final_output.exists():
                            final_output.unlink()
                        temp_output.rename(final_output)
                
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