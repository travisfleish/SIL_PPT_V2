#!/usr/bin/env python3
"""
Setup script for the Sports Innovation Lab web frontend
Installs dependencies and prepares the environment
"""

import os
import sys
import subprocess
from pathlib import Path


def setup_frontend():
    """Setup the frontend environment"""
    print("🚀 Setting up Sports Innovation Lab Frontend")
    print("=" * 50)

    # Check Python version
    if sys.version_info < (3, 7):
        print("❌ Error: Python 3.7+ required")
        return False

    # Install required packages
    packages = [
        'flask>=2.0.0',
        'flask-cors>=3.0.0',
        'python-dotenv>=0.19.0'
    ]

    print("\n📦 Installing required packages...")
    for package in packages:
        print(f"   Installing {package}...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

    # Create frontend directories
    dirs = ['backend', 'frontend', 'logs']
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"✅ Created directory: {dir_name}/")

    # Create .env file if not exists
    env_file = Path('.env')
    if not env_file.exists():
        print("\n📝 Creating .env file...")
        env_content = """# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# CORS Settings
CORS_ORIGINS=*

# File Upload Settings
MAX_CONTENT_LENGTH=16777216  # 16MB

# Job Settings
JOB_TIMEOUT=600  # 10 minutes
JOB_CLEANUP_HOURS=24  # Clean up jobs older than 24 hours
"""
        env_file.write_text(env_content)
        print("✅ Created .env file")

    # Create run scripts
    create_run_scripts()

    print("\n✅ Frontend setup complete!")
    print("\nTo start the application:")
    print("1. Run the backend:  python backend/app.py")
    print("2. Open frontend:    Open frontend/index.html in your browser")
    print("\nOr use the convenience scripts:")
    print("   Windows: run_frontend.bat")
    print("   Linux/Mac: ./run_frontend.sh")

    return True


def create_run_scripts():
    """Create platform-specific run scripts"""

    # Windows batch file
    bat_content = """@echo off
echo Starting Sports Innovation Lab Frontend...
echo.

REM Start Flask backend
start "SIL Backend" cmd /k "cd backend && python app.py"

REM Wait a moment for server to start
timeout /t 3 /nobreak > nul

REM Open browser
start "" "http://localhost:5000"
start "" "frontend/index.html"

echo.
echo Frontend started!
echo Backend running at http://localhost:5000
echo.
pause
"""

    Path('run_frontend.bat').write_text(bat_content)

    # Unix shell script
    sh_content = """#!/bin/bash
echo "Starting Sports Innovation Lab Frontend..."
echo

# Start Flask backend
cd backend && python app.py &
BACKEND_PID=$!

# Wait for server to start
sleep 3

# Open browser (cross-platform)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open "http://localhost:5000"
    open "frontend/index.html"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    xdg-open "http://localhost:5000" 2>/dev/null || echo "Please open http://localhost:5000 in your browser"
    xdg-open "frontend/index.html" 2>/dev/null
fi

echo
echo "Frontend started!"
echo "Backend running at http://localhost:5000 (PID: $BACKEND_PID)"
echo
echo "Press Ctrl+C to stop the backend server"

# Wait for Ctrl+C
trap "kill $BACKEND_PID" INT
wait $BACKEND_PID
"""

    sh_file = Path('run_frontend.sh')
    sh_file.write_text(sh_content)

    # Make shell script executable
    if sys.platform != 'win32':
        os.chmod(sh_file, 0o755)


def create_docker_setup():
    """Create Docker configuration for easy deployment"""

    dockerfile_content = """FROM python:3.9-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "backend/app.py"]
"""

    Path('Dockerfile').write_text(dockerfile_content)

    compose_content = """version: '3.8'

services:
  sil-frontend:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
    volumes:
      - ./output:/app/output
      - ./logs:/app/logs
    restart: unless-stopped
"""

    Path('docker-compose.yml').write_text(compose_content)

    print("✅ Created Docker configuration files")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Setup Sports Innovation Lab Frontend')
    parser.add_argument('--docker', action='store_true', help='Also create Docker configuration')

    args = parser.parse_args()

    success = setup_frontend()

    if success and args.docker:
        create_docker_setup()
        print("\nDocker setup complete! Run with: docker-compose up")