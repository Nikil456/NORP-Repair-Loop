# This runner script can be quickly used to use venv 

# Navigate to the desired directory using $HOME
cd "$HOME\Documents\RTS"

# Set the PowerShell execution policy to allow running scripts
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

# Activate the virtual environment
.\venv\Scripts\Activate.ps1

# Navigate to the app directory
cd .\SQLLMengine\llm-engine\app
