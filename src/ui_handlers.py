import gradio as gr
from pathlib import Path
import re

class UIEventHandlers:
    def __init__(self, ui):
        self.ui = ui
    
    def handle_file_upload(self, file):
        """Handle file upload event."""
        if file is None:
            return gr.update(value=[]), gr.update(choices=["No sections available"], value="No sections available"), None, ""
        
        # Load the file, which also processes and splits the text into sections internally
        _, name = self.ui.load_file(file, True)
        
        # Get the raw sections and raw text after file processing
        sections_data = self.ui.processor.get_sections()
        raw_text_content = self.ui.processor.get_raw_text()
        
        # Create Gradio components for the sections
        section_components = self._create_section_components(sections_data)
        
        current_audio = None
        track_choices = ["No sections available"]
        selected_track_value = "No sections available"

        if self.ui.audio_player.generated_files:
            current_audio = self.ui.audio_player.get_current_audio()
            track_choices = [f"Section {i+1}" for i in range(len(self.ui.audio_player.generated_files))]
            if track_choices:
                selected_track_value = track_choices[0]

        return (
            gr.update(value=section_components, visible=True),
            gr.update(choices=track_choices, value=selected_track_value),
            current_audio,
            raw_text_content
        )
    
    def handle_generation_complete(self, files, status):
        """Handle generation completion event."""
        if files and len(files) > 0:
            self.ui.audio_player.set_generated_files(files)
            current_audio = self.ui.audio_player.get_current_audio()
            track_choices = [f"Section {i+1}" for i in range(len(files))]
            return current_audio, status, gr.update(choices=track_choices, value=track_choices[0])
        return None, status, gr.update(choices=["No sections available"], value="No sections available")
    
    def handle_stop_generation(self):
        """Handle stop generation event."""
        status = self.ui.audio_generator.stop_generation()
        if self.ui.audio_player.generated_files:
            current_audio = self.ui.audio_player.get_current_audio()
            track_choices = [f"Section {i+1}" for i in range(len(self.ui.audio_player.generated_files))]
            return status, current_audio, gr.update(choices=track_choices, value=track_choices[self.ui.audio_player.current_audio_index])
        return status, None, gr.update(choices=["No sections available"], value="No sections available")
    
    def handle_next(self):
        """Handle next audio event."""
        next_audio = self.ui.audio_player.next_audio()
        if not self.ui.audio_player.generated_files:
            return None, gr.update(choices=["No sections available"], value="No sections available")
        track_choices = [f"Section {i+1}" for i in range(len(self.ui.audio_player.generated_files))]
        return next_audio, gr.update(choices=track_choices, value=track_choices[self.ui.audio_player.current_audio_index])
    
    def handle_previous(self):
        """Handle previous audio event."""
        prev_audio = self.ui.audio_player.previous_audio()
        if not self.ui.audio_player.generated_files:
            return None, gr.update(choices=["No sections available"], value="No sections available")
        track_choices = [f"Section {i+1}" for i in range(len(self.ui.audio_player.generated_files))]
        return prev_audio, gr.update(choices=track_choices, value=track_choices[self.ui.audio_player.current_audio_index])
    
    def on_track_selected(self, track_name):
        """Handle track selection event."""
        if not track_name or not self.ui.audio_player.generated_files or track_name == "No sections available":
            return None, gr.update(choices=["No sections available"], value="No sections available")
            
        try:
            # Extract section number from "Section X" format
            section_num = int(track_name.split("Section")[1].strip()) - 1
            
            if 0 <= section_num < len(self.ui.audio_player.generated_files):
                self.ui.audio_player.current_audio_index = section_num
                current_audio = self.ui.audio_player.get_current_audio()
                track_choices = [f"Section {i+1}" for i in range(len(self.ui.audio_player.generated_files))]
                return current_audio, gr.update(choices=track_choices, value=track_choices[section_num])
            else:
                return None, gr.update(choices=["No sections available"], value="No sections available")
        except Exception as e:
            return None, gr.update(choices=["No sections available"], value="No sections available")
    
    def handle_concatenation(self):
        """Handle audio concatenation event."""
        output_file, status = self.ui.audio_player.concatenate_audio_files()
        if output_file:
            return {
                self.ui.download_btn: gr.update(visible=True, value=output_file),
                self.ui.download_status: gr.update(visible=True, value=status)
            }
        return {
            self.ui.download_btn: gr.update(visible=False),
            self.ui.download_status: gr.update(visible=True, value=status)
        }
    
    def toggle_rvc_controls(self, use_rvc):
        """Toggle RVC controls visibility."""
        return {
            self.ui.rvc_model: gr.update(visible=use_rvc),
            self.ui.f0_up_key: gr.update(visible=use_rvc),
            self.ui.f0_method: gr.update(visible=use_rvc),
            self.ui.index_rate: gr.update(visible=use_rvc)
        }
    
    def update_rvc_models(self):
        """Update RVC models list."""
        models = self.ui.rvc_processor.get_available_models()
        self.ui.rvc_model_choices = {model["name"]: model["path"] for model in models}
        return gr.update(choices=list(self.ui.rvc_model_choices.keys()))
    
    def _create_section_components(self, sections):
        """Helper to create data for Gradio Dataframe from sections."""
        dataframe_data = []
        for i, section in enumerate(sections):
            dataframe_data.append([f"Section {i+1}", section])
        return dataframe_data

    def handle_raw_text_processing(self, text):
        """Handle raw text processing."""
        if not text:
            return gr.update(value=[["", ""]]) # Return empty dataframe data
        
        # Process the raw text
        self.ui.processor.split_text(text)
        sections = self.ui.processor.get_sections()
        
        # Create and return components for each section
        return {
            self.ui.sections_list: gr.update(value=self._create_section_components(sections), visible=True)
        }
    
    def handle_text_update(self, text):
        """Handle text update and section refresh."""
        if not text:
            return gr.update(value=[["", ""]]) # Return empty dataframe data
        
        try:
            # Process the raw text
            self.ui.processor.split_text(text)
            sections = self.ui.processor.get_sections()
            
            # Create and return components for each section
            return {
                self.ui.sections_list: gr.update(value=self._create_section_components(sections), visible=True)
            }
        except Exception as e:
            return gr.update(value=[["Error processing text:", str(e)]]) 