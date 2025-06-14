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
from .file_processor import FileProcessor
from .audio_player import AudioPlayer
from .audio_generator import AudioGenerator
from .ui_handlers import UIEventHandlers
from .ui_layout import UILayout
from datetime import datetime
from pydub import AudioSegment
import io

class AudiobookUI:
    def __init__(self):
        # Initialize processors
        self.processor = TTSProcessor()
        self.rvc_processor = RVCProcessor()
        
        # Create voice choices with display names
        self.voice_choices = {
            self.processor.get_voice_display_name(voice_id): voice_id
            for voice_id in self.processor.available_voices
        }
        self.available_voices = list(self.voice_choices.keys())
        
        # Initialize components
        self.file_processor = FileProcessor()
        self.audio_player = AudioPlayer()
        self.audio_generator = AudioGenerator(self.processor, self.rvc_processor)
        
        # Create RVC models directory
        self.rvc_models_dir = Path("rvc_models")
        self.rvc_models_dir.mkdir(exist_ok=True)
        
        # Initialize RVC model choices
        self.rvc_model_choices = {}
        self.update_rvc_models()
        
        # Initialize UI components
        self.handlers = UIEventHandlers(self)
        self.layout = UILayout(self)
        
        # Initialize RVC control attributes
        self.rvc_model = None
        self.f0_up_key = None
        self.f0_method = None
        self.index_rate = None
        
        # Initialize download components
        self.download_btn = None
        self.download_status = None
        
        # Initialize sections list component
        self.sections_list = None
        
        # Initialize status bar component
        self.generate_status = None
    
    def update_rvc_models(self):
        """Update the list of available RVC models."""
        models = self.rvc_processor.get_available_models()
        self.rvc_model_choices = {model["name"]: model["path"] for model in models}
        return list(self.rvc_model_choices.keys())
    
    def load_file(self, file, force_create=False):
        """Load and split the text file into sections."""
        if file is None:
            return None, ""
        
        try:
            # Get the original filename without extension
            book_name = Path(file.name).stem
            
            # Create output directory
            self.current_output_dir, safe_name, dir_exists = self.file_processor.create_output_directory(book_name, force_create)
            
            # Set output directory for components
            self.audio_player.set_output_dir(self.current_output_dir)
            self.audio_generator.set_output_dir(self.current_output_dir)
            
            # Handle different file types
            file_path = Path(file.name)
            if file_path.suffix.lower() == '.epub':
                # Extract images from EPUB first
                self.file_processor.extract_images_from_epub(file_path, self.current_output_dir)
                # Extract and process text using built-in functionality
                content = self.file_processor.extract_text_from_epub(file_path)
            else:
                # Read text file content
                content = self.file_processor.read_text_file(file_path)
            
            # Split into sections using processor's split_text
            self.processor.split_text(content)
            
            # Format sections for display
            formatted_sections = "\n\n".join([f"Section {i+1}:\n{section}" for i, section in enumerate(self.processor.get_sections())])
            
            return formatted_sections, safe_name
            
        except Exception as e:
            return None, ""
    
    def update_output_dir(self, folder_name):
        """Update the output directory name."""
        if not folder_name:
            return "Please enter a folder name."
        
        try:
            # Clean the folder name
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', folder_name)
            # Create new directory without timestamp
            new_output_dir = self.file_processor.base_output_dir / safe_name
            new_output_dir.mkdir(exist_ok=True)
            
            # If we have an existing output dir and it's empty, remove it
            if self.current_output_dir and self.current_output_dir.exists():
                if not any(self.current_output_dir.iterdir()):
                    self.current_output_dir.rmdir()
            
            self.current_output_dir = new_output_dir
            self.audio_player.set_output_dir(new_output_dir)
            self.audio_generator.set_output_dir(new_output_dir)
            return f"Output folder updated to: {self.current_output_dir}"
        except Exception as e:
            return f"Error updating folder name: {str(e)}"
    
    def create_ui(self):
        """Create the Gradio interface."""
        return self.layout.create_ui()