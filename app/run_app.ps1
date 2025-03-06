# This runner script can be used in windows to quickly run the app

# Navigate to the desired directory using $HOME
cd "$HOME\Documents\RTS"

# Set the PowerShell execution policy to allow running scripts
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

# Activate the virtual environment
.\venv\Scripts\Activate.ps1

# Navigate to the app directory
cd .\SQLLMengine\llm-engine\app

# Run the application
uvicorn app:app --reload --host 127.0.0.1 --port 8000
