@echo off
echo Kokoro Audiobooks Setup and Startup Script
echo ========================================

:: Check if Python 3.10 is installed using py launcher
py -3.10 --version >nul 2>&1
if errorlevel 1 (
    echo Python 3.10 is not installed! Please install Python 3.10.
    echo You can download it from: https://www.python.org/downloads/release/python-3100/
    pause
    exit /b 1
)

:: Check if this is first run by looking for .venv
if not exist .venv (
    echo First time setup detected...
    echo Creating virtual environment...
    py -3.10 -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment!
        pause
        exit /b 1
    )

    :: Activate virtual environment
    echo Activating virtual environment...
    call .venv\Scripts\activate

    :: Check for CUDA installation
    echo Checking for CUDA installation...
    nvidia-smi >nul 2>&1
    if errorlevel 1 (
        echo NVIDIA drivers not found. Checking for CUDA...
        nvcc --version >nul 2>&1
        if errorlevel 1 (
            echo CUDA not found. Installing CPU-only version...
            pip install torch torchaudio
        ) else (
            echo CUDA found. Installing CUDA version...
            pip install torch==2.1.1+cu118 torchaudio==2.1.1+cu118 --index-url https://download.pytorch.org/whl/cu118
        )
    ) else (
        echo NVIDIA GPU found. Installing CUDA version...
        pip install torch==2.1.1+cu118 torchaudio==2.1.1+cu118 --index-url https://download.pytorch.org/whl/cu118
    )

    :: Install project dependencies
    echo Installing project dependencies...
    pip install -r requirements.txt

    echo.
    echo Setup completed successfully!
) else (
    :: Just activate the environment and run
    call .venv\Scripts\activate
)

echo.
echo Starting Kokoro Audiobooks...
python main.py

echo.
pause 