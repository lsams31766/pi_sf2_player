import json
from pathlib import Path

default_settings = {
    "master_volume": 0.5,
    "midi_channel": "OMNI",
    "transpose": 0,
    "soundfont_filename": "default-GM.sf2"
}

# Define a safe path in the user's home directory (or use Path.home() / "sf2_settings.json")
SETTINGS_FILE = Path("/home/larry/python_code/sf2_settings.json")

def load_settings():
    """Load settings from file, or return defaults if file doesn't exist."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                print("Loading saved settings...")
                return json.load(f)
        except Exception as e:
            print(f"Error loading settings: {e}. Using defaults.")
    else:
        print("No saved settings found. Using defaults.")
    
    return default_settings.copy()

def save_settings(settings):
    """Save the current settings dictionary to the file."""
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
        print("Settings saved successfully!")
    except Exception as e:
        print(f"Error saving settings: {e}")
