"""
Text-to-Speech processor for converting text to audio using Kokoro.
"""
from pathlib import Path
import torch
from kokoro import KPipeline
import soundfile as sf
import numpy as np
import warnings
from dataclasses import dataclass
from typing import Dict, List, Optional

# Suppress specific warnings
warnings.filterwarnings("ignore", category=UserWarning, module="torch.nn.modules.rnn")
warnings.filterwarnings("ignore", category=FutureWarning, module="torch.nn.utils.weight_norm")
warnings.filterwarnings("ignore", message="words count mismatch")

@dataclass
class Speaker:
    name: str
    region: str  # 'US' or 'UK'
    gender: str  # 'female' or 'male'
    grade: str   # Quality grade (A, B, C, etc.)
    traits: List[str]
    lang_code: str  # 'a' for US English, 'b' for UK English

class TTSProcessor:
    # Define available speakers
    SPEAKERS = {
        # US English Speakers
        'af_heart': Speaker('Heart', 'US', 'female', 'A', ['❤️'], 'a'),
        'af_bella': Speaker('Bella', 'US', 'female', 'A-', ['🔥'], 'a'),
        'af_nicole': Speaker('Nicole', 'US', 'female', 'B-', ['🎧'], 'a'),
        'af_alloy': Speaker('Alloy', 'US', 'female', 'C', [], 'a'),
        'af_aoede': Speaker('Aoede', 'US', 'female', 'C+', [], 'a'),
        'af_jessica': Speaker('Jessica', 'US', 'female', 'D', [], 'a'),
        'af_kore': Speaker('Kore', 'US', 'female', 'C+', [], 'a'),
        'af_nova': Speaker('Nova', 'US', 'female', 'C', [], 'a'),
        'af_river': Speaker('River', 'US', 'female', 'D', [], 'a'),
        'af_sarah': Speaker('Sarah', 'US', 'female', 'C+', [], 'a'),
        'af_sky': Speaker('Sky', 'US', 'female', 'C-', [], 'a'),
        'am_adam': Speaker('Adam', 'US', 'male', 'F+', [], 'a'),
        'am_echo': Speaker('Echo', 'US', 'male', 'D', [], 'a'),
        'am_eric': Speaker('Eric', 'US', 'male', 'D', [], 'a'),
        'am_fenrir': Speaker('Fenrir', 'US', 'male', 'C+', [], 'a'),
        'am_liam': Speaker('Liam', 'US', 'male', 'D', [], 'a'),
        'am_michael': Speaker('Michael', 'US', 'male', 'C+', [], 'a'),
        'am_onyx': Speaker('Onyx', 'US', 'male', 'D', [], 'a'),
        'am_puck': Speaker('Puck', 'US', 'male', 'C+', [], 'a'),
        'am_santa': Speaker('Santa', 'US', 'male', 'D-', [], 'a'),
        
        # UK English Speakers
        'bf_alice': Speaker('Alice', 'UK', 'female', 'D', [], 'b'),
        'bf_emma': Speaker('Emma', 'UK', 'female', 'B-', [], 'b'),
        'bf_isabella': Speaker('Isabella', 'UK', 'female', 'C', [], 'b'),
        'bf_lily': Speaker('Lily', 'UK', 'female', 'D', [], 'b'),
        'bm_daniel': Speaker('Daniel', 'UK', 'male', 'D', [], 'b'),
        'bm_fable': Speaker('Fable', 'UK', 'male', 'C', [], 'b'),
        'bm_george': Speaker('George', 'UK', 'male', 'C', [], 'b'),
        'bm_lewis': Speaker('Lewis', 'UK', 'male', 'D+', [], 'b'),
    }

    def __init__(self):
        self.sections = []
        self.last_generated_section = -1
        self.pipeline = None
        self.current_lang_code = 'a'  # Default to US English
        
        # Initialize the TTS model
        self._initialize_model()

    @property
    def available_voices(self) -> List[str]:
        """Get list of available voice IDs for UI compatibility."""
        return list(self.SPEAKERS.keys())

    def get_voice_display_name(self, voice_id: str) -> str:
        """Get a display-friendly name for a voice."""
        speaker = self.get_speaker_info(voice_id)
        if speaker:
            gender_emoji = '🚺' if speaker.gender == 'female' else '🚹'
            return f"[{speaker.region}] {voice_id} ({speaker.grade}) {gender_emoji}"
        return voice_id

    def _initialize_model(self):
        """Initialize the Kokoro TTS model."""
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Using device: {device}")
            
            # Initialize Kokoro pipeline with explicit repo_id and lang_code
            self.pipeline = KPipeline(
                lang_code=self.current_lang_code or 'a',  # Default to US English if None
                repo_id='hexgrad/Kokoro-82M'
            )
            print("TTS model initialized successfully")
        except Exception as e:
            print(f"Error initializing TTS model: {str(e)}")
            self.pipeline = None

    def get_speaker_info(self, speaker_id: str) -> Optional[Speaker]:
        """Get information about a specific speaker."""
        return self.SPEAKERS.get(speaker_id)

    def list_speakers(self, region: Optional[str] = None, gender: Optional[str] = None, min_grade: Optional[str] = None) -> Dict[str, Speaker]:
        """List available speakers with optional filtering."""
        filtered_speakers = {}
        
        for speaker_id, speaker in self.SPEAKERS.items():
            if region and speaker.region != region:
                continue
            if gender and speaker.gender != gender:
                continue
            if min_grade and self._grade_to_value(speaker.grade) < self._grade_to_value(min_grade):
                continue
            filtered_speakers[speaker_id] = speaker
            
        return filtered_speakers

    def _grade_to_value(self, grade: str) -> int:
        """Convert grade to numeric value for comparison."""
        grade_map = {
            'A+': 12, 'A': 11, 'A-': 10,
            'B+': 9, 'B': 8, 'B-': 7,
            'C+': 6, 'C': 5, 'C-': 4,
            'D+': 3, 'D': 2, 'D-': 1,
            'F+': 0, 'F': -1
        }
        return grade_map.get(grade, -2)

    def split_text(self, text):
        """Split text into manageable sections."""
        # Simple splitting by paragraphs
        self.sections = [section.strip() for section in text.split('\n\n') if section.strip()]
        return len(self.sections)
    
    def get_sections(self):
        """Get all sections."""
        return self.sections
    
    def get_section(self, index):
        """Get a specific section by index."""
        if 0 <= index < len(self.sections):
            return self.sections[index]
        return None
    
    def get_last_generated_section(self):
        """Get the index of the last generated section."""
        return self.last_generated_section
    
    def generate_speech(self, text, output_path, voice="af_heart", speed=1.0):
        """Generate speech from text using Kokoro."""
        if self.pipeline is None:
            print("Attempting to reinitialize TTS model...")
            self._initialize_model()
            if self.pipeline is None:
                print("Failed to initialize TTS model")
                return False
            
        try:
            # Get speaker info
            speaker = self.get_speaker_info(voice)
            if not speaker:
                print(f"Unknown speaker: {voice}")
                return False

            # Check if we need to switch language
            if speaker.lang_code != self.current_lang_code:
                self.current_lang_code = speaker.lang_code
                self._initialize_model()
                if self.pipeline is None:
                    print("Failed to reinitialize TTS model with new language")
                    return False

            # Generate speech using Kokoro
            generator = self.pipeline(text, voice=voice, speed=speed)
            
            # Save to file
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Get the first (and only) audio segment
            for _, _, audio in generator:
                # Convert to audio file
                sf.write(str(output_path), audio, 24000)  # Kokoro uses 24kHz sample rate
                break  # We only need the first segment
            
            return True
        except Exception as e:
            print(f"Error generating speech: {str(e)}")
            return False
    
    def regenerate_section(self, section_idx, output_path, voice="af_heart", speed=1.0):
        """Regenerate a specific section."""
        section_text = self.get_section(section_idx)
        if section_text is None:
            return False
            
        success = self.generate_speech(section_text, output_path, voice, speed)
        if success:
            self.last_generated_section = section_idx
        return success
    
    def regenerate_from_section(self, start_idx, output_dir, voice="af_heart", speed=1.0):
        """Regenerate all sections from a specific index onwards."""
        output_files = []
        for i in range(start_idx, len(self.sections)):
            output_path = Path(output_dir) / f"section_{i+1}.wav"
            if self.regenerate_section(i, output_path, voice, speed):
                output_files.append(str(output_path))
        return output_files 