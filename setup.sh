#!/bin/bash

# Local Scout AI Agent Setup Script
# This script sets up the Local Scout AI Agent environment.

# Print colored status messages
print_status() {
    echo -e "\e[1;34m[*] $1\e[0m"
}

print_success() {
    echo -e "\e[1;32m[+] $1\e[0m"
}

print_error() {
    echo -e "\e[1;31m[-] $1\e[0m"
}

# Check for Python 3.8+
print_status "Checking Python version..."
if command -v python3 >/dev/null 2>&1; then
    python_version=$(python3 --version | cut -d ' ' -f 2)
    python_major=$(echo $python_version | cut -d '.' -f 1)
    python_minor=$(echo $python_version | cut -d '.' -f 2)
    
    if [ $python_major -ge 3 ] && [ $python_minor -ge 8 ]; then
        print_success "Python $python_version found."
    else
        print_error "Python 3.8+ is required, but found $python_version."
        exit 1
    fi
else
    print_error "Python 3 not found. Please install Python 3.8+."
    exit 1
fi

# Create virtual environment
print_status "Creating Python virtual environment..."
if [ -d "venv" ]; then
    print_status "Virtual environment already exists. Skipping creation."
else
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        print_error "Failed to create virtual environment."
        exit 1
    fi
    print_success "Virtual environment created."
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    print_error "Failed to activate virtual environment."
    exit 1
fi
print_success "Virtual environment activated."

# Install dependencies
print_status "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    print_error "Failed to install dependencies."
    exit 1
fi
print_success "Dependencies installed."

# Create necessary directories
print_status "Creating directories..."
mkdir -p data/logs data/memory data/tasks data/plots models

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    print_status "Creating .env file..."
    cp .env.example .env
    print_success ".env file created. Please edit it with your configuration."
fi

# Download the model if it doesn't exist
print_status "Checking for LLM model..."
model_path=$(grep "LLM_MODEL_PATH" .env | cut -d '=' -f 2)
if [ -z "$model_path" ]; then
    model_path="./models/llama-2-7b-chat.gguf"
fi

if [ ! -f "$model_path" ]; then
    print_status "LLM model not found. Downloading..."
    python3 scripts/download_model.py
    if [ $? -ne 0 ]; then
        print_error "Failed to download LLM model."
        exit 1
    fi
    print_success "LLM model downloaded."
else
    print_success "LLM model already exists."
fi

print_status "Setting up installation..."
chmod +x main.py scripts/download_model.py

print_success "Setup completed successfully!"
print_status "To start the agent, run: ./main.py"
print_status "For more information, see the README.md file."