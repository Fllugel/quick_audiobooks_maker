# Quick Audiobooks Maker

A sample application that converts text files to audiobooks using Kokoro TTS and voice conversion technology. This tool combines advanced text-to-speech capabilities with voice conversion to create natural-sounding audiobooks with customizable voices.

## Features
- Load and process text files (supports various formats (tested for .txt and .epub))
- Intelligent text splitting for optimal processing
- High-quality text-to-speech conversion using Kokoro TTS
- Voice conversion using RVC (Retrieval-based Voice Conversion)

## Prerequisites
- Python 3.10 (highly recommended use such python version)
- CUDA-compatible GPU (recommended for faster processing)
- NVIDIA drivers installed
- CUDA Toolkit 11.8 installed on your system
- FFmpeg installed on your system (required for audio concatenation)

### FFmpeg Installation
FFmpeg is required for concatenating audio files into a complete audiobook:

1. **Windows**
   ```bash
   winget install ffmpeg
   ```
   or download from [FFmpeg Official Website](https://ffmpeg.org/download.html)

2. **Linux**
   ```bash
   sudo apt update
   sudo apt install ffmpeg
   ```

3. **macOS**
   ```bash
   brew install ffmpeg
   ```

### CUDA Installation
For GPU acceleration to work properly, you need to install CUDA Toolkit 11.8:

1. **Check GPU Compatibility**
   - Visit [NVIDIA CUDA GPUs](https://developer.nvidia.com/cuda-gpus) to verify if your GPU supports CUDA
   - Ensure your GPU has at least 4GB VRAM for optimal performance

2. **Install NVIDIA Drivers**
   - Download and install the latest NVIDIA drivers from [NVIDIA Driver Downloads](https://www.nvidia.com/Download/index.aspx)
   - Restart your computer after installation

3. **Install CUDA Toolkit 11.8**
   - Download CUDA Toolkit 11.8 from [NVIDIA CUDA Downloads](https://developer.nvidia.com/cuda-11-8-0-download-archive)
   - Follow the installation instructions for your operating system
   - Add CUDA to your system PATH if not done automatically

Note: If you don't have a CUDA-compatible GPU or prefer not to install CUDA, the application will still work using CPU, but processing will be significantly slower.

## Quick Start
The easiest way to get started is to use our automated setup scripts:

### Windows
Simply run:
```bash
start.bat
```
This will:
- Create a virtual environment
- Install all required dependencies
- Set up CUDA support
- Create necessary directories

### Linux/Mac
First, make the script executable:
```bash
chmod +x start.sh
```
Then run:
```bash
./start.sh
```

## Manual Setup
If you prefer to set up manually, follow these steps:

### 1. Create and Activate Virtual Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate
```

### 2. Install CUDA Dependencies
For Windows:
```bash
pip install torch==2.1.1+cu118 torchaudio==2.1.1+cu118 --index-url https://download.pytorch.org/whl/cu118
```

For Linux:
```bash
pip install torch==2.1.1+cu118 torchaudio==2.1.1+cu118 --index-url https://download.pytorch.org/whl/cu118
```

### 3. Install Project Dependencies
```bash
pip install -r requirements.txt
```

## Usage
1. Place your text file in the input directory
2. Configure voice settings (optional)
3. Run the application:
```bash
python main.py
```

## RVC Models
The application supports voice conversion using RVC (Retrieval-based Voice Conversion) models. To use voice conversion:

1. **Model Placement**
   - Place your RVC model files (`.pth` files) in the `rvc_models` directory
   - Each model should be in its own subdirectory within `rvc_models`

2. **Model Structure**
   ```
   rvc_models/
   ├── model_name_1/
   │   ├── model_name.pth
   │   └── model_name.index
   ├── model_name_2/
   │   ├── model_name.pth
   │   └── model_name.index
   ```

Note: You can obtain RVC models from various sources or train your own using the RVC framework.

## Contributing
Contributions are welcome! Feel free to submit pull requests or open issues for bugs and feature requests.
