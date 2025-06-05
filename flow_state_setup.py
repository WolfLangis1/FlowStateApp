#!/usr/bin/env python3
"""
Flow State Music Player - Setup Script
Automated setup for development and basic user environments.
For broader distribution, consider tools like PyInstaller, cx_Freeze, or Briefcase.
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path
import logging

# Configure logger for setup script specifically
setup_logger = logging.getLogger("FlowStateSetup")
setup_logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - [Setup] - %(message)s')
# Add console handler for setup script
ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(formatter)
if not setup_logger.handlers: # Avoid adding multiple handlers if script is re-imported/run
    setup_logger.addHandler(ch)
setup_logger.propagate = False # Prevent double logging if root logger is also configured

class FlowStateSetup:
    def __init__(self):
        self.platform_system = platform.system()
        self.python_version_info = sys.version_info
        self.script_dir = Path(__file__).parent.resolve()
        self.venv_name = "flow_state_venv" # More specific venv name
        self.venv_path = self.script_dir / self.venv_name
        self.requirements_file_path = self.script_dir / "requirements.txt"

    def check_python_version(self):
        """Check if Python version is compatible."""
        setup_logger.info(f"Python Version: {sys.version.splitlines()[0]}")
        if self.python_version_info < (3, 8): # Requirement is Python 3.8+
            setup_logger.error("Flow State requires Python 3.8 or higher. Please upgrade your Python installation.")
            sys.exit(1)
        setup_logger.info("Python version check: OK.")

    def check_system_dependencies(self):
        """Provide guidance on system-level dependencies."""
        setup_logger.info("--- System Dependency Guidance ---")
        if self.platform_system == "Linux":
            setup_logger.info("On Linux, ensure the following (or equivalents for your distro) are installed:")
            setup_logger.info("  - python3-tk (for Tkinter GUI)")
            setup_logger.info("  - portaudio19-dev (for PyAudio/sounddevice microphone access)")
            setup_logger.info("  - ffmpeg (for audio conversion/export)")
            setup_logger.info("  - libsndfile1 (for soundfile library)")
            setup_logger.info("Example for Debian/Ubuntu: sudo apt-get update && sudo apt-get install -y python3-tk portaudio19-dev ffmpeg libsndfile1")
        elif self.platform_system == "Darwin": # macOS
            setup_logger.info("On macOS, ensure Homebrew is installed (https://brew.sh/), then consider:")
            setup_logger.info("  - brew install python-tk (if system Python's Tk is old/problematic, though usually not needed with brew's python)")
            setup_logger.info("  - brew install portaudio")
            setup_logger.info("  - brew install ffmpeg")
            setup_logger.info("  - brew install libsndfile") # For soundfile
        elif self.platform_system == "Windows":
            setup_logger.info("On Windows:")
            setup_logger.info("  - Python installer from python.org usually includes Tkinter.")
            setup_logger.info("  - PortAudio: Python packages like sounddevice often bundle PortAudio or use precompiled wheels that include it.")
            setup_logger.info("  - FFmpeg: Download from ffmpeg.org, extract, and add its 'bin' folder to your system's PATH environment variable.")
            setup_logger.info("  - Microsoft C++ Build Tools or Visual C++ Redistributable might be needed for compiling some Python packages if wheels are not available.")
        setup_logger.info("These are common dependencies. Some Python packages might have others during `pip install`.")
        setup_logger.info("--- End System Dependency Guidance ---")

    def create_or_confirm_virtual_env(self) -> Path:
        setup_logger.info(f"Setting up virtual environment: '{self.venv_path.name}' at {self.script_dir}")
        if self.venv_path.is_dir() and (self.venv_path / "pyvenv.cfg").exists():
            setup_logger.info(f"Virtual environment '{self.venv_path.name}' already exists.")
            # Optionally, ask to recreate or update dependencies within it.
            # For now, assume using existing is fine.
        else:
            setup_logger.info(f"Creating new virtual environment '{self.venv_path.name}'...")
            try:
                subprocess.check_call([sys.executable, "-m", "venv", str(self.venv_path)])
                setup_logger.info("Virtual environment created successfully.")
            except subprocess.CalledProcessError as e:
                setup_logger.error(f"Failed to create virtual environment: {e}")
                setup_logger.error("Please check your Python installation and 'venv' module.")
                sys.exit(1)
            except Exception as e_gen:
                setup_logger.error(f"An unexpected error occurred creating virtual environment: {e_gen}", exc_info=True)
                sys.exit(1)
        return self.venv_path

    def get_venv_paths(self) -> Tuple[Path, Path]:
        """Get platform-specific pip and python paths within the venv."""
        if self.platform_system == "Windows":
            python_exe = self.venv_path / "Scripts" / "python.exe"
            pip_exe = self.venv_path / "Scripts" / "pip.exe"
        else: # Linux/macOS
            python_exe = self.venv_path / "bin" / "python"
            pip_exe = self.venv_path / "bin" / "pip"
        
        if not python_exe.exists() or not pip_exe.exists():
            setup_logger.error(f"Python/pip executables not found in venv path: {self.venv_path}")
            setup_logger.error("The virtual environment may be corrupted or was not created correctly.")
            sys.exit(1)
        return python_exe, pip_exe

    def install_python_dependencies(self) -> bool:
        """Install Python dependencies from requirements.txt into the venv."""
        python_exe, pip_exe = self.get_venv_paths()

        if not self.requirements_file_path.exists():
            setup_logger.error(f"'{self.requirements_file_path.name}' not found in {self.script_dir}. Cannot install dependencies.")
            return False

        setup_logger.info(f"Installing Python dependencies from '{self.requirements_file_path.name}' using '{pip_exe}'...")
        try:
            setup_logger.info("Upgrading pip, setuptools, and wheel...")
            subprocess.check_call([str(python_exe), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
            
            setup_logger.info(f"Installing packages from {self.requirements_file_path.name}...")
            subprocess.check_call([str(pip_exe), "install", "-r", str(self.requirements_file_path)])
            setup_logger.info("Python dependencies installed successfully.")
            return True
        except subprocess.CalledProcessError as e:
            setup_logger.error(f"Failed to install Python dependencies: {e}")
            setup_logger.error("Ensure your virtual environment is active if running pip manually, "
                               "or that system dependencies (compilers, dev headers like portaudio19-dev) are met.")
            return False
        except Exception as e_gen:
            setup_logger.error(f"An unexpected error occurred installing dependencies: {e_gen}", exc_info=True)
            return False

    def create_run_scripts(self):
        """Create platform-specific run scripts that activate venv and launch the app."""
        setup_logger.info("Creating run scripts...")
        # Relative paths from the script_dir (where run scripts will be located)
        venv_rel_path_part = self.venv_name # e.g., "flow_state_venv"
        launcher_rel_path = "flow_state_launcher.py" # Relative to self.script_dir

        if self.platform_system == "Windows":
            # For .bat, %~dp0 expands to the drive and path of the batch script itself
            python_in_venv_rel_for_bat = f"{venv_rel_path_part}\\Scripts\\python.exe"
            activate_script_rel_for_bat = f"{venv_rel_path_part}\\Scripts\\activate.bat"
            script_content = f'''@echo off
echo Activating virtual environment from %~dp0 ...
call "%~dp0{activate_script_rel_for_bat}"
if errorlevel 1 (
    echo Failed to activate virtual environment. Ensure setup was successful.
    pause
    exit /b 1
)
echo Starting Flow State Music Player...
"%~dp0{python_in_venv_rel_for_bat}" "%~dp0{launcher_rel_path}" %*
echo Flow State exited. Press any key to close.
pause >nul
'''
            script_path = self.script_dir / "run_flow_state.bat"
        else: # Linux/macOS
            # For .sh, SCRIPT_DIR gets the directory of the script itself
            python_in_venv_rel_for_sh = f"{venv_rel_path_part}/bin/python"
            activate_script_rel_for_sh = f"{venv_rel_path_part}/bin/activate"
            script_content = f'''#!/bin/bash
# Get the directory where the script is located, even if called via symlink
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${{BASH_SOURCE[0]}}" || readlink "${{BASH_SOURCE[0]}}" || echo "${{BASH_SOURCE[0]}}")")" &>/dev/null && pwd)"

VENV_ACTIVATE="$SCRIPT_DIR/{activate_script_rel_for_sh}"
PYTHON_EXEC="$SCRIPT_DIR/{python_in_venv_rel_for_sh}"
LAUNCHER_SCRIPT="$SCRIPT_DIR/{launcher_rel_path}"

if [ ! -f "$VENV_ACTIVATE" ]; then
    echo "Error: Virtual environment activation script not found at $VENV_ACTIVATE" >&2
    echo "Please run the setup script (e.g., python flow_state_setup.py) first." >&2
    exit 1
fi
if [ ! -f "$PYTHON_EXEC" ]; then
    echo "Error: Python executable not found in venv at $PYTHON_EXEC" >&2
    exit 1
fi
if [ ! -f "$LAUNCHER_SCRIPT" ]; then
    echo "Error: Launcher script not found at $LAUNCHER_SCRIPT" >&2
    exit 1
fi

echo "Activating virtual environment..."
source "$VENV_ACTIVATE"

echo "Starting Flow State Music Player..."
"$PYTHON_EXEC" "$LAUNCHER_SCRIPT" "$@"
EXIT_CODE=$?

# Deactivate venv (optional, happens on shell exit anyway for sourced scripts)
if type deactivate &>/dev/null; then
    # echo "Deactivating virtual environment..." # Optional message
    deactivate &>/dev/null
fi

echo "Flow State exited with code $EXIT_CODE."
# read -p "Press Enter to close window..." # Uncomment for explicit pause on Linux/macOS if run in new terminal
exit $EXIT_CODE
'''
            script_path = self.script_dir / "run_flow_state.sh"
            
        try:
            with open(script_path, 'w', newline='\n') as f: # Ensure LF line endings for .sh
                f.write(script_content)
            if self.platform_system != "Windows":
                os.chmod(script_path, 0o755) # Make executable (rwxr-xr-x)
            setup_logger.info(f"Created run script: {script_path.name}")
        except IOError as e:
            setup_logger.error(f"Failed to create run script {script_path.name}: {e}")
        except Exception as e_gen:
            setup_logger.error(f"An unexpected error occurred creating run script {script_path.name}: {e_gen}", exc_info=True)


    def run_full_setup(self):
        """Runs the complete setup process, prompting the user."""
        setup_logger.info("--- Flow State Music Player Setup Initiated ---")
        self.check_python_version()
        self.check_system_dependencies()

        try:
            self.create_or_confirm_virtual_env()
        except SystemExit: # If venv creation failed and exited
            return # Stop setup

        if self.requirements_file_path.exists():
            if input("\nInstall/update Python dependencies from 'requirements.txt'? (y/n): ").strip().lower() == 'y':
                if not self.install_python_dependencies():
                    setup_logger.warning("Dependency installation failed or was skipped. The application may not run correctly.")
            else:
                setup_logger.info("Skipping Python dependency installation as per user choice.")
        else:
            setup_logger.error(f"'{self.requirements_file_path.name}' not found. Cannot install Python dependencies.")
            setup_logger.info("Please ensure 'requirements.txt' is in the same directory as this setup script, or install dependencies manually.")

        if input("\nCreate run scripts (e.g., run_flow_state.bat/sh)? (y/n): ").strip().lower() == 'y':
            self.create_run_scripts()
        
        # Application data directories are created by the launcher on its first run.
        setup_logger.info("--- Setup Process Finished ---")
        run_script_name = "run_flow_state.sh" if self.platform_system != "Windows" else "run_flow_state.bat"
        setup_logger.info(f"\nTo run {self.app_name}:")
        setup_logger.info(f"  1. Navigate to the project directory: cd \"{self.script_dir}\"")
        setup_logger.info(f"  2. Execute the run script: ./{run_script_name} (or {run_script_name} on Windows)")
        setup_logger.info("\nAlternatively, to run manually:")
        if self.platform_system == "Windows":
            setup_logger.info(f"  1. Open a command prompt and run: \"{self.venv_path / 'Scripts' / 'activate.bat'}\"")
        else:
            setup_logger.info(f"  1. Open a terminal and run: source \"{self.venv_path / 'bin' / 'activate'}\"")
        setup_logger.info(f"  2. Then run: python \"{self.script_dir / 'flow_state_launcher.py'}\"")
        setup_logger.info("\nFor development mode, add --dev or -d argument to the launcher script.")
        setup_logger.info(f"\n🎉 Enjoy Flow State!")

if __name__ == "__main__":
    setup_manager = FlowStateSetup()
    setup_manager.run_full_setup()