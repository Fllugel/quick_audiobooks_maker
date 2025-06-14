from pathlib import Path
from pydub import AudioSegment

class AudioPlayer:
    def __init__(self):
        self.generated_files = []
        self.current_audio_index = 0
        self.is_playing = False
        self.last_played_audio = None
        self.current_output_dir = None
    
    def set_output_dir(self, output_dir):
        """Set the current output directory."""
        self.current_output_dir = output_dir
    
    def set_generated_files(self, files):
        """Set the list of generated audio files."""
        self.generated_files = files
        self.current_audio_index = 0
    
    def get_current_audio(self):
        """Get the current audio file to play."""
        if not self.generated_files:
            return None
        return self.generated_files[self.current_audio_index]
    
    def next_audio(self):
        """Move to the next audio file."""
        if not self.generated_files:
            return None
        self.current_audio_index = (self.current_audio_index + 1) % len(self.generated_files)
        return self.get_current_audio()
    
    def previous_audio(self):
        """Move to the previous audio file."""
        if not self.generated_files:
            return None
        self.current_audio_index = (self.current_audio_index - 1) % len(self.generated_files)
        return self.get_current_audio()
    
    def get_audio_info(self):
        """Get information about the current audio file."""
        if not self.generated_files:
            return "No audio files loaded"
            
        try:
            current_file = Path(self.generated_files[self.current_audio_index])
            # Try to extract section number from filename, fallback to filename if pattern not found
            try:
                section_num = current_file.stem.split('_')[1]
                return f"Playing Section {section_num} ({self.current_audio_index + 1}/{len(self.generated_files)})"
            except IndexError:
                return f"Playing {current_file.stem} ({self.current_audio_index + 1}/{len(self.generated_files)})"
        except Exception as e:
            return f"Error getting audio info: {str(e)}"
    
    def concatenate_audio_files(self):
        """Concatenate all generated audio files into a single file."""
        if not self.generated_files or not self.current_output_dir:
            return None, "No audio files to concatenate."
        
        try:
            # Create a temporary file for the concatenated audio
            temp_output = self.current_output_dir / "temp_concatenated.wav"
            final_output = self.current_output_dir / "complete_audiobook.wav"
            
            # Load and concatenate all audio files
            combined = AudioSegment.empty()
            for audio_file in self.generated_files:
                audio = AudioSegment.from_wav(audio_file)
                combined += audio
            
            # Export the concatenated audio
            combined.export(temp_output, format="wav")
            
            # Move the temporary file to the final location
            if final_output.exists():
                final_output.unlink()
            temp_output.rename(final_output)
            
            return str(final_output), "Audio files concatenated successfully!"
            
        except Exception as e:
            return None, f"Error concatenating audio files: {str(e)}" 