# Kokoro Audiobooks

A simple application that converts text files to audiobooks using Kokoro TTS and voice conversion.

## Features
- Load and process text files
- Split text into manageable parts
- Convert text to speech using Kokoro TTS
- Apply voice conversion using RVC

## Setup
1. Create a virtual environment:
```bash
python -m venv .venv
```

2. Activate the virtual environment:
- Windows:
```bash
.venv\Scripts\activate
```
- Linux/Mac:
```bash
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage
1. Place your text file in the input directory
2. Run the application:
```bash
python main.py
```

## Requirements
- Python 3.8 or higher
- CUDA-compatible GPU (recommended for faster processing) 