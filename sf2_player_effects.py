# sf2_player_effects.py

import subprocess
import atexit
import time

# --- Configuration Constants ---
FLUIDSYNTH_CLIENT_NAME = "fluidsynth"
DAC_SINK_NAME = "alsa_output.platform-soc_sound.stereo-fallback"

REVERB_PLUGIN_URI = "http://drobilla.net/plugins/fomp/reverb"
REVERB_CLIENT_NAME = "reverb"

CHORUS_PLUGIN_URI = "http://drobilla.net/plugins/fomp/cs_chorus1"
CHORUS_CLIENT_NAME = "CS Chorus 1"

jalv_reverb_process = None
jalv_chorus_process = None

# Track all possible links for clean switching
ALL_POSSIBLE_LINKS = [
    (f"{FLUIDSYNTH_CLIENT_NAME}:left", f"{DAC_SINK_NAME}:playback_FL"),
    (f"{FLUIDSYNTH_CLIENT_NAME}:right", f"{DAC_SINK_NAME}:playback_FR"),
    (f"{FLUIDSYNTH_CLIENT_NAME}:left", f"{REVERB_CLIENT_NAME}:in_l"),
    (f"{FLUIDSYNTH_CLIENT_NAME}:right", f"{REVERB_CLIENT_NAME}:in_r"),
    (f"{REVERB_CLIENT_NAME}:out_l", f"{DAC_SINK_NAME}:playback_FL"),
    (f"{REVERB_CLIENT_NAME}:out_r", f"{DAC_SINK_NAME}:playback_FR"),
    (f"{FLUIDSYNTH_CLIENT_NAME}:left", f"{CHORUS_CLIENT_NAME}:in"),
    (f"{FLUIDSYNTH_CLIENT_NAME}:right", f"{CHORUS_CLIENT_NAME}:in"),
    (f"{CHORUS_CLIENT_NAME}:out", f"{DAC_SINK_NAME}:playback_FL"),
    (f"{CHORUS_CLIENT_NAME}:out", f"{DAC_SINK_NAME}:playback_FR"),
    (f"{CHORUS_CLIENT_NAME}:out", f"{REVERB_CLIENT_NAME}:in_l"),
    (f"{CHORUS_CLIENT_NAME}:out", f"{REVERB_CLIENT_NAME}:in_r"),
]

def start_effects_containers(max_wait=5.0, poll_interval=0.25):
    """Launch both reverb and chorus jalv containers in the background."""
    global jalv_reverb_process, jalv_chorus_process

    print(f"Starting effects containers...")
    try:
        jalv_reverb_process = subprocess.Popen(
            ["pw-jack", "jalv", REVERB_PLUGIN_URI],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError as e:
        print(f"Could not launch reverb jalv ({e}).")

    try:
        jalv_chorus_process = subprocess.Popen(
            ["pw-jack", "jalv", CHORUS_PLUGIN_URI],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError as e:
        print(f"Could not launch chorus jalv ({e}).")

    atexit.register(stop_effects_containers)

    # Wait for ports of both plugins to appear
    success = True
    success &= _wait_for_ports(REVERB_CLIENT_NAME, ["in_l", "in_r", "out_l", "out_r"], max_wait, poll_interval)
    success &= _wait_for_ports(CHORUS_CLIENT_NAME, ["in", "out"], max_wait, poll_interval)

    if success:
        print("Effects containers initialized successfully.")
    else:
        print("Warning: Some effect ports failed to appear.")

def set_effect_configuration(config_name):
    """
    Switch effect routing dynamically at runtime.
    Supported configurations:
      1) 'none'          -> Dry signal to DAC
      2) 'reverb'        -> Fluidsynth -> Reverb -> DAC
      3) 'chorus'        -> Fluidsynth -> Chorus -> DAC
      4) 'chorus_reverb' -> Fluidsynth -> Chorus -> Reverb -> DAC
    """
    print(f"\n[Effects] Switching configuration to: '{config_name}'")
    
    # Step 1: Tear down all existing known connections to avoid conflicts
    for src, dst in ALL_POSSIBLE_LINKS:
        _pw_unlink(src, dst)

    ok = True

    # Step 2: Establish new connections based on requested configuration
    if config_name == 'none':
        ok &= _pw_link(f"{FLUIDSYNTH_CLIENT_NAME}:left", f"{DAC_SINK_NAME}:playback_FL")
        ok &= _pw_link(f"{FLUIDSYNTH_CLIENT_NAME}:right", f"{DAC_SINK_NAME}:playback_FR")

    elif config_name == 'reverb':
        ok &= _pw_link(f"{FLUIDSYNTH_CLIENT_NAME}:left", f"{REVERB_CLIENT_NAME}:in_l")
        ok &= _pw_link(f"{FLUIDSYNTH_CLIENT_NAME}:right", f"{REVERB_CLIENT_NAME}:in_r")
        ok &= _pw_link(f"{REVERB_CLIENT_NAME}:out_l", f"{DAC_SINK_NAME}:playback_FL")
        ok &= _pw_link(f"{REVERB_CLIENT_NAME}:out_r", f"{DAC_SINK_NAME}:playback_FR")

    elif config_name == 'chorus':
        ok &= _pw_link(f"{FLUIDSYNTH_CLIENT_NAME}:left", f"{CHORUS_CLIENT_NAME}:in")
        ok &= _pw_link(f"{FLUIDSYNTH_CLIENT_NAME}:right", f"{CHORUS_CLIENT_NAME}:in")
        ok &= _pw_link(f"{CHORUS_CLIENT_NAME}:out", f"{DAC_SINK_NAME}:playback_FL")
        ok &= _pw_link(f"{CHORUS_CLIENT_NAME}:out", f"{DAC_SINK_NAME}:playback_FR")

    elif config_name == 'chorus_reverb': 
        ok &= _pw_link(f"{FLUIDSYNTH_CLIENT_NAME}:left", f"{CHORUS_CLIENT_NAME}:in")
        ok &= _pw_link(f"{FLUIDSYNTH_CLIENT_NAME}:right", f"{CHORUS_CLIENT_NAME}:in")
        ok &= _pw_link(f"{CHORUS_CLIENT_NAME}:out", f"{REVERB_CLIENT_NAME}:in_l")
        ok &= _pw_link(f"{CHORUS_CLIENT_NAME}:out", f"{REVERB_CLIENT_NAME}:in_r")
        ok &= _pw_link(f"{REVERB_CLIENT_NAME}:out_l", f"{DAC_SINK_NAME}:playback_FL")
        ok &= _pw_link(f"{REVERB_CLIENT_NAME}:out_r", f"{DAC_SINK_NAME}:playback_FR")
    else:
        print(f"Error: Unknown configuration '{config_name}'. Defaulting to 'none'.")
        set_effect_configuration('none')  
        return

    if ok:
        print(f"Configuration '{config_name}' applied successfully.")
    else:
        print(f"Warning: Configuration '{config_name}' applied with some routing errors.")

# --- Shared DRY Helper Functions ---

def _wait_for_ports(client_name, port_suffixes, max_wait, poll_interval):
    needed = {f"{client_name}:{suf}" for suf in port_suffixes}
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            out_ports = [p.strip() for p in subprocess.run(["pw-link", "-o"], capture_output=True, text=True, check=True).stdout.splitlines()]
            in_ports = [p.strip() for p in subprocess.run(["pw-link", "-i"], capture_output=True, text=True, check=True).stdout.splitlines()]
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
            
        available = set(out_ports) | set(in_ports)
        if needed.issubset(available):
            return True
        time.sleep(poll_interval)
    return False

def _pw_link(src, dst):
    try:
        subprocess.run(["pw-link", src, dst], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        print(f"  linked {src} -> {dst}")
        return True
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode().strip() if e.stderr else str(e)
        print(f"  Warning: could not link {src} -> {dst}: {stderr}")
        return False

def _pw_unlink(src, dst):
    try:
        subprocess.run(["pw-link", "-d", src, dst], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False  # Ignore if the link wasn't active

def stop_effects_containers():
    global jalv_reverb_process, jalv_chorus_process
    for proc, name in [(jalv_reverb_process, "reverb"), (jalv_chorus_process, "chorus")]:
        if proc and proc.poll() is None:
            print(f"Stopping {name} effect (jalv)...")
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
