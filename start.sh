#!/bin/bash

echo "Kokoro Audiobooks Setup and Startup Script"
echo "========================================"

# Check if Python 3.10 is installed
if ! command -v python3.10 &> /dev/null; then
    echo "Python 3.10 is not installed! Please install Python 3.10."
    exit 1
fi

# Check if this is first run by looking for .venv
if [ ! -d ".venv" ]; then
    echo "First time setup detected..."
    echo "Creating virtual environment..."
    python3.10 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment!"
        exit 1
    fi

    # Activate virtual environment
    echo "Activating virtual environment..."
    source .venv/bin/activate

    # Check for CUDA installation
    echo "Checking for CUDA installation..."
    if ! command -v nvidia-smi &> /dev/null; then
        echo "NVIDIA drivers not found. Checking for CUDA..."
        if ! command -v nvcc &> /dev/null; then
            echo "CUDA not found. Installing CPU-only version..."
            pip install torch torchaudio
        else
            echo "CUDA found. Installing CUDA version..."
            pip install torch==2.1.1+cu118 torchaudio==2.1.1+cu118 --index-url https://download.pytorch.org/whl/cu118
        fi
    else
        echo "NVIDIA GPU found. Installing CUDA version..."
        pip install torch==2.1.1+cu118 torchaudio==2.1.1+cu118 --index-url https://download.pytorch.org/whl/cu118
    fi

    # Install project dependencies
    echo "Installing project dependencies..."
    pip install -r requirements.txt

    echo
    echo "Setup completed successfully!"
else
    # Just activate the environment and run
    source .venv/bin/activate
fi

echo
echo "Starting Kokoro Audiobooks..."
python main.py

echo 