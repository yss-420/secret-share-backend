#!/bin/bash

# Secret Share Bot - Dependency Installation Script
# This script installs dependencies in the correct order to avoid conflicts

echo "Installing Secret Share Bot dependencies..."

# Step 1: Install core dependencies first
echo "Installing core dependencies..."
pip install python-telegram-bot==21.0.1
pip install python-dotenv==1.0.0
pip install requests==2.31.0
pip install aiohttp==3.9.1

# Step 2: Install database
echo "Installing database dependencies..."
pip install supabase==2.3.4

# Step 3: Install AI/ML packages
echo "Installing AI/ML dependencies..."
pip install replicate==0.22.0
pip install elevenlabs==0.2.26
pip install pydub==0.25.1

# Step 4: Install utilities
echo "Installing utility packages..."
pip install Pillow==10.1.0
pip install numpy==1.24.3

# Step 5: Install development packages (optional)
echo "Installing development packages..."
pip install pytest==7.4.3
pip install pytest-asyncio==0.21.1

echo "Dependency installation complete!"
echo "Run 'pip freeze > requirements_installed.txt' to see what was actually installed." 