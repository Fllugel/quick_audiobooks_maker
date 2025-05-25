@echo off
echo Kokoro Audiobooks Setup and Startup Script
echo ========================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed! Please install Python 3.10 or higher.
    pause
    exit /b 1
)

REM Check if this is first run by looking for .venv
if not exist .venv (
    echo First time setup detected...
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment!
        pause
        exit /b 1
    )

    REM Activate virtual environment
    echo Activating virtual environment...
    call .venv\Scripts\activate

    REM Check for CUDA installation
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

    REM Install project dependencies
    echo Installing project dependencies...
    pip install -r requirements.txt

    echo.
    echo Setup completed successfully!
) else (
    REM Just activate the environment and run
    call .venv\Scripts\activate
)

echo.
echo Starting Kokoro Audiobooks...
python main.py

echo.
pause 