# Flow State - Next Generation Music Player 🎵

Flow State is an advanced, feature-rich, AI-powered music player designed for an immersive and intelligent listening experience. It goes beyond traditional players by integrating advanced audio visualizations, real-time collaboration features, voice control, and smart music discovery.

![Flow State Concept Banner](https://placehold.co/1200x300/1e1e1e/00ffff?text=Flow+State+Music+Player&font=montserrat)
*(Conceptual banner - replace with actual screenshot when UI is more complete)*

## ✨ Core Vision

To create a music experience that is:
- **Immersive:** Through GPU-accelerated audio visualizations and synchronized lyrics.
- **Intelligent:** With AI-powered recommendations, automatic music analysis (BPM, key, mood), and intuitive search.
- **Connected:** Featuring real-time collaborative listening sessions and mobile remote control.
- **Customizable:** Offering a themable interface and an extensible plugin system for effects and visualizers.
- **Performant:** Utilizing modern Python techniques, background processing with `asyncio` and `threading`/`multiprocessing`, efficient libraries like `sounddevice` for audio and `moderngl` for visuals.

## 🚀 Getting Started

### Prerequisites:
*   **Python:** 3.8 or higher.
*   **FFmpeg:** Required for audio export features and potentially some audio analysis tasks. Must be installed and accessible in your system's PATH.
*   **System Dependencies:** (Vary by OS - the setup script provides guidance)
    *   **Linux:** `python3-tk`, `portaudio19-dev`, `libsndfile1`. (e.g., `sudo apt-get install python3-tk portaudio19-dev ffmpeg libsndfile1`)
    *   **macOS:** `portaudio`, `ffmpeg`, `libsndfile` (e.g., via Homebrew: `brew install portaudio ffmpeg libsndfile`)
    *   **Windows:** Python from python.org usually includes Tkinter. FFmpeg needs to be downloaded and its `bin` folder added to PATH. Microsoft C++ Build Tools might be needed for some Python packages.

### Installation & Setup:
1.  **Clone or Download:** Get the project files.
    ```bash
    # git clone <repository_url> # If using git
    # cd flow-state-project
    ```
2.  **Run Setup Script:** This script will guide you through creating a virtual environment and installing dependencies.
    ```bash
    python flow_state_setup.py
    ```
    Follow the on-screen prompts. This will:
    *   Check your Python version.
    *   Create a Python virtual environment (e.g., in a `flow_state_venv` folder).
    *   Install Python packages from `requirements.txt`.
    *   Create convenient run scripts (`run_flow_state_music_player.bat` or `run_flow_state_music_player.sh`).

### Running Flow State:
*   **Recommended:** Use the generated run script from the project root directory:
    *   Windows: `run_flow_state_music_player.bat`
    *   Linux/macOS: `./run_flow_state_music_player.sh`
*   **Manual Alternative:**
    1.  Activate the virtual environment:
        *   Windows: `.\\flow_state_venv\\Scripts\\activate`
        *   Linux/macOS: `source flow_state_venv/bin/activate`
    2.  Run the launcher:
        ```bash
        python flow_state_launcher.py
        ```

### Development Mode:
To launch individual modules for testing or development (if supported by launcher):
```bash
python flow_state_launcher.py --dev