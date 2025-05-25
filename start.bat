@echo off
echo Starting Kokoro Audiobook Generator...

:: Activate virtual environment
call .venv\Scripts\activate.bat

:: Run the program
python main.py

:: Keep the window open if there's an error
if errorlevel 1 (
    echo.
    echo An error occurred. Press any key to exit...
    pause > nul
)

:: Deactivate virtual environment
call deactivate 