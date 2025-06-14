import os
from pathlib import Path
from rvc_python.infer import RVCInference
import torch
from fairseq.data.dictionary import Dictionary
import warnings
import shutil
import time

# Suppress specific PyTorch deprecation warnings
warnings.filterwarnings("ignore", message="torch.nn.utils.weight_norm is deprecated")
warnings.filterwarnings("ignore", message="TypedStorage is deprecated")

class RVCProcessor:
    def __init__(self):
        self.rvc = None
        self.model_path = None
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.disabled = False
        self.model_choices = {}  # Initialize model choices dictionary
        
    def set_disabled(self, disabled=True):
        """Set whether RVC processing is disabled."""
        self.disabled = disabled
        
    def load_model(self, model_path):
        """Load an RVC model."""
        if self.disabled:
            return True
            
        try:
            if not self.rvc:
                self.rvc = RVCInference(device=self.device)
            
            # Load the model
            self.rvc.load_model(model_path)
            self.model_path = model_path
            return True
        except Exception as e:
            print(f"Error loading RVC model: {str(e)}")
            return False
            
    def convert_audio(self, input_path, output_path, f0_up_key=0, f0_method="harvest", index_rate=0.5):
        """Convert audio using the loaded RVC model."""
        try:
            if self.disabled:
                # If RVC is disabled, just copy the input file to output
                try:
                    # Ensure any existing files are properly closed and removed
                    if os.path.exists(output_path):
                        try:
                            os.remove(output_path)
                        except PermissionError:
                            # If we can't remove it, try to wait a bit and try again
                            time.sleep(0.5)
                            os.remove(output_path)
                    
                    # Use copyfile instead of copy2 to avoid metadata copying issues
                    shutil.copyfile(input_path, output_path)
                    return True
                except Exception as e:
                    print(f"Error during file copy: {str(e)}")
                    return False
                
            if not self.rvc or not self.model_path:
                raise Exception("No RVC model loaded")
            
            # Set RVC parameters
            self.rvc.f0method = f0_method
            self.rvc.f0up_key = f0_up_key
            self.rvc.index_rate = index_rate
            self.rvc.filter_radius = 3
            self.rvc.resample_sr = 0
            self.rvc.rms_mix_rate = 0.25
            self.rvc.protect = 0.33
                
            self.rvc.infer_file(
                str(input_path),
                str(output_path)
            )
            return True
        except Exception as e:
            return False
            
    def get_available_models(self, models_dir="rvc_models"):
        """Get list of available RVC models."""
        models = []
        models_path = Path(models_dir)
        
        if not models_path.exists():
            return models
            
        for model_dir in models_path.iterdir():
            if model_dir.is_dir():
                # Look for any .pth files in the subfolder
                pth_files = list(model_dir.glob("*.pth"))
                
                if pth_files:  # Only process if .pth file exists
                    model_name = model_dir.name  # Use folder name as model name
                    pth_file = pth_files[0]  # Take the first .pth file
                    
                    # Look for any .index file in the same directory
                    index_files = list(model_dir.glob("*.index"))
                    has_index = len(index_files) > 0
                    
                    # Create display name with index status
                    display_name = model_name
                    if not has_index:
                        display_name += " (No Index)"
                        
                    # Store both the display name and the actual file path
                    models.append({
                        "name": display_name,
                        "path": str(pth_file)
                    })
        
        # Update model choices dictionary
        self.model_choices = {model["name"]: model["path"] for model in models}
        return models 