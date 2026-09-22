#sf2_player_fluidsynth.py
# REQUIRES pyfluidsynth and mido libraries

import sys
import time
import os
import threading
import subprocess
import atexit
import fluidsynth
import mido
from pathlib import Path
from sf2_player_settings import save_settings, load_settings

fs = None

# --- REVERB EFFECT CONFIGURATION (jalv + pipewire/pw-link) ---
REVERB_PLUGIN_URI = "http://drobilla.net/plugins/fomp/reverb"
# jalv registers its JACK/pipewire client using the plugin's short name.
# This matched "reverb:in_l" / "reverb:out_l" in your manual pw-link tests.
REVERB_CLIENT_NAME = "reverb"
# fluidsynth's jack driver defaults to a client named "fluidsynth"
FLUIDSYNTH_CLIENT_NAME = "fluidsynth"
# Name of your DAC's pipewire sink node (from `pw-link -o` / `pw-cli ls Node`).
# Update this if your card shows up under a different node name.
DAC_SINK_NAME = "alsa_output.platform-soc_sound.stereo-fallback"

jalv_process = None

# Keep track of state globally
current_bank = 0
current_program = 0
current_instrument_name = ''
current_sf_id = 0 
current_gain = 0.5

# --- MIDI FILTER & TRANSPOSE CONFIGURATION ---
TARGET_MIDI_CHANNEL = 0  
input_filter_channel = None  # None = OMNI (accept all channels)
midi_transpose = 0

midi_thread_running = False

sf2_directory = '/usr/share/sounds/sf2/'
nbr_sf2_files = 1 # when we read the list we will update this
current_sf2_name = 'unknown'


def find_launchkey_port():
    """Dynamically find the keyboard port name to avoid strict string mismatches."""
    ports = mido.get_input_names()
    print(f"Available MIDI input ports: {ports}")
    for port in ports:
        if 'Launchkey' in port:
            return port
    # Fallback to the first available port if any exist
    if ports:
        return ports[0]
    return None

def midi_listener_thread():
    """Background thread that captures USB MIDI, applies filters/transposition, and plays notes."""
    global midi_thread_running
    
    time.sleep(1.0) # Brief pause for port registration
    
    port_name = find_launchkey_port()
    if not port_name:
        print("MIDI Listener Error: No MIDI input ports found! Is the keyboard plugged in?")
        return

    try:
        print(f"Opening MIDI input port: {port_name}")
        with mido.open_input(port_name) as inport:
            midi_thread_running = True
            for msg in inport:
                if not midi_thread_running:
                    break
                
                # 1. MIDI Channel Filter Logic
                if input_filter_channel is not None:
                   if hasattr(msg, 'channel') and msg.channel != input_filter_channel:
                       continue 
                
                dest_channel = TARGET_MIDI_CHANNEL

                # 2. Transpose & Event Routing Logic
                if msg.type == 'note_on':
                    # print('note on')
                    new_note = max(0, min(127, msg.note + midi_transpose))
                    if msg.velocity > 0:
                        fs.noteon(dest_channel, new_note, msg.velocity)
                    else:
                        fs.noteoff(dest_channel, new_note)
                        
                elif msg.type == 'note_off':
                    new_note = max(0, min(127, msg.note + midi_transpose))
                    fs.noteoff(dest_channel, new_note)
                    
                elif msg.type == 'control_change':
                    fs.cc(dest_channel, msg.control, msg.value)
                    
                elif msg.type == 'pitchwheel':
                    fs.pitch_bend(dest_channel, msg.pitch)
                    
    except Exception as e:
        print(f"MIDI Listener Error: {e}")
        midi_thread_running = False

def _ensure_pipewire_jack_wrapper():
    """fluidsynth's jack driver links against the system's libjack, which on
    a pipewire-only system (no real jackd installed) needs pipewire's JACK
    shim on the library path - that's what `pw-jack` sets up. If we don't
    look wrapped already, re-exec this same process under pw-jack so you
    never have to remember to type it yourself.
    """
    if os.environ.get("SF2_PLAYER_PW_JACK_WRAPPED") == "1":
        return  # already wrapped on a previous exec - don't loop
    ld_path = os.environ.get("LD_LIBRARY_PATH", "")
    if "pipewire" in ld_path and "jack" in ld_path:
        return  # something already put pipewire's jack shim on the path

    print("Relaunching under pw-jack so fluidsynth can reach pipewire's JACK layer...")
    env = os.environ.copy()
    env["SF2_PLAYER_PW_JACK_WRAPPED"] = "1"
    try:
        os.execvpe("pw-jack", ["pw-jack", sys.executable] + sys.argv, env)
    except FileNotFoundError:
        print("Warning: 'pw-jack' not found on PATH (is pipewire-jack installed?). "
              "Continuing without it - the jack driver will likely fail to start. "
              "You can also run this manually as: pw-jack python3 <your_script>.py")

def init_fluidsynth():
    global fs, current_sf_id, current_bank, current_program, current_instrument_name, \
        current_sf2_name, current_gain, input_filter_channel, midi_transpose

    _ensure_pipewire_jack_wrapper()

    settings = load_settings()
    fs = fluidsynth.Synth()
    # Switched from the "alsa" driver to "jack" so pipewire's JACK layer can
    # see fluidsynth's ports and we can pw-link them to the reverb effect.
    fs.setting('audio.jack.autoconnect', 0)  # we wire it up ourselves
    fs.setting('audio.period-size', 128)
    fs.setting('audio.periods', 2)
    fs.setting('synth.sample-rate', 44100.0)
    fs.setting('midi.driver', 'alsa_seq')  # Valid driver reinstated

    fs.start(driver="jack")

    #  small 6 MB soundfont
    sf_path = "/usr/share/sounds/sf2/"
    #current_sf2_name = "default-GM.sf2"
    current_sf2_name = settings.get('soundfont_filename', 'default-GM.sf2')
    # alternate sf2 much bigger in size
    #sf_path = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
    sf_id = fs.sfload( os.path.join(sf_path,current_sf2_name))
    temp_filter = settings.get('midi_channel', 'OMNI')
    if temp_filter == "OMNI":
        input_filter_channel = None
    else:
        input_filter_channel = int(temp_filter) - 1 # 0 based
    midi_transpose = settings.get('transpose',0)

    if sf_id == -1:
        print(f"Error: Could not load SoundFont at {sf_path}")
        exit(1)

    current_sf_id = sf_id
    current_bank = 0
    current_program = 0
    fs.program_select(0, current_sf_id, current_bank, current_program)
    try:
        name_query = fs.sfpreset_name(current_sf_id, current_bank, current_program)
        if name_query:
            current_instrument_name = name_query
    except Exception:
        pass
    print(f"SoundFont initialized with {current_instrument_name}")

    current_gain = settings.get('master_volume',0.5)
    fs.setting('synth.gain', current_gain)

    # Start our custom Python MIDI processing thread in the background
    t = threading.Thread(target=midi_listener_thread, daemon=True)
    t.start()

    # Launch the reverb effect and wire fluidsynth -> reverb -> DAC
    start_reverb_effect()

    try:
        print("Setting PipeWire default sink volume to 1.8...")
        subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "1.8"], check=True)
    except Exception as e:
        print(f"Warning: Could not set system volume via wpctl: {e}")


    print("\n--- Setup Complete! Play your Novation Launchkey 61 ---")
    print("Press Ctrl+C to stop the script.")

def start_reverb_effect(max_wait=5.0, poll_interval=0.25):
    """Launch jalv hosting the fomp reverb LV2 plugin, then use pw-link to
    patch fluidsynth's output through the reverb and into the DAC, matching:
        pw-jack jalv http://drobilla.net/plugins/fomp/reverb
        pw-link fluidsynth:left "reverb:in_l"
        pw-link fluidsynth:right "reverb:in_r"
        pw-link "reverb:out_l" alsa_output...:playback_FL
        pw-link "reverb:out_r" alsa_output...:playback_FR
    """
    global jalv_process

    print(f"Starting reverb effect: {REVERB_PLUGIN_URI}")
    try:
        # "pw-jack" is prefixed so this works even if the main script itself
        # wasn't launched under pw-jack. It's harmless to prefix it twice.
        jalv_process = subprocess.Popen(
            ["pw-jack", "jalv", REVERB_PLUGIN_URI],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError as e:
        print(f"Could not launch jalv ({e}). Is jalv installed? Skipping reverb.")
        return

    atexit.register(stop_reverb_effect)

    if not _wait_for_ports(REVERB_CLIENT_NAME, ["in_l", "in_r", "out_l", "out_r"],
                            max_wait, poll_interval):
        print("Warning: reverb ports never appeared - skipping pw-link wiring. "
              "Check that jalv started correctly (try running it manually).")
        return

    ok = True
    ok &= _pw_link(f"{FLUIDSYNTH_CLIENT_NAME}:left", f"{REVERB_CLIENT_NAME}:in_l")
    ok &= _pw_link(f"{FLUIDSYNTH_CLIENT_NAME}:right", f"{REVERB_CLIENT_NAME}:in_r")
    ok &= _pw_link(f"{REVERB_CLIENT_NAME}:out_l", f"{DAC_SINK_NAME}:playback_FL")
    ok &= _pw_link(f"{REVERB_CLIENT_NAME}:out_r", f"{DAC_SINK_NAME}:playback_FR")

    if ok:
        print("Reverb connected: fluidsynth -> reverb -> DAC")
    else:
        print("Reverb effect started but one or more pw-link connections failed "
              "(see warnings above). Check port names with `pw-link -o -i`.")

def _wait_for_ports(client_name, port_suffixes, max_wait, poll_interval):
    """Poll `pw-link` port listings until the given client's ports show up."""
    needed = {f"{client_name}:{suf}" for suf in port_suffixes}
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            out_ports = subprocess.run(["pw-link", "-o"], capture_output=True,
                                        text=True, check=True).stdout.split()
            in_ports = subprocess.run(["pw-link", "-i"], capture_output=True,
                                       text=True, check=True).stdout.split()
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"pw-link port listing failed: {e}")
            return False
        available = set(out_ports) | set(in_ports)
        if needed.issubset(available):
            return True
        time.sleep(poll_interval)
    return False

def _pw_link(src, dst):
    try:
        subprocess.run(["pw-link", src, dst], check=True,
                        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        print(f"  linked {src} -> {dst}")
        return True
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode().strip() if e.stderr else str(e)
        print(f"  Warning: could not link {src} -> {dst}: {stderr}")
        return False

def stop_reverb_effect():
    """Tear down the jalv reverb process (registered with atexit)."""
    global jalv_process
    if jalv_process and jalv_process.poll() is None:
        print("Stopping reverb effect (jalv)...")
        jalv_process.terminate()
        try:
            jalv_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            jalv_process.kill()

def previous_preset():
    global current_program, current_bank, current_sf_id, fs, current_instrument_name
    if current_program > 0:
        current_program -= 1
    else:
        print("Reached minimum program (0).")
        return None, None, None

    if fs and current_sf_id > 0:
        fs.program_select(0, current_sf_id, current_bank, current_program)
        print(f"previous preset -> Switched to Bank: {current_bank}, Program: {current_program}")
        instrument_name = f"Program {current_program}"
        try:
            name_query = fs.sfpreset_name(current_sf_id, current_bank, current_program)
            if name_query:
                current_instrument_name = name_query
        except Exception:
            pass

def next_preset():
    global current_program, current_bank, current_sf_id, fs, current_instrument_name
    if current_program < 127:
        current_program += 1
    else:
        print("Reached maximum program (127).")
        return

    if fs and current_sf_id > 0:
        fs.program_select(0, current_sf_id, current_bank, current_program)
        print(f"next pressed -> Switched to Bank: {current_bank}, Program: {current_program}")
        instrument_name = f"Program {current_program}"
        try:
            name_query = fs.sfpreset_name(current_sf_id, current_bank, current_program)
            if name_query:
                current_instrument_name = name_query
        except Exception:
            pass

def get_current_preset_details():
    return current_bank, current_program, current_instrument_name

def get_gain():
    return current_gain 

def set_gain(fValue):
    fs.setting('synth.gain', fValue)

def lower_gain():
    global current_gain
    if current_gain < 0.01:
        return 
    current_gain -= 0.1
    if current_gain < 0:
        current_gain = 0.0
    set_gain(current_gain)

def raise_gain():
    global current_gain
    if current_gain >= 1.0:
        return 
    current_gain += 0.1
    if current_gain > 1.0:
        current_gain = 1.0
    set_gain(current_gain)

def get_midi_chan_display():
    if input_filter_channel == None:
        return 'OMNI'
    return str(input_filter_channel + 1)

def lower_midi_chan():
    global input_filter_channel
    if input_filter_channel is None: # OMNI
        input_filter_channel = 15 
    elif input_filter_channel > 0:
        input_filter_channel -= 1
    else:
        input_filter_channel = None 
    print(f"MIDI Filter Channel set to: {get_midi_chan_display()}")

def raise_midi_chan():
    global input_filter_channel
    if input_filter_channel is None: # OMNI
        input_filter_channel = 0 
    elif input_filter_channel < 15:
        input_filter_channel += 1
    else:
        input_filter_channel = None 
    print(f"MIDI Filter Channel set to: {get_midi_chan_display()}")

def get_transpose():
    return midi_transpose

def raise_midi_transpose():
    global midi_transpose
    if midi_transpose < 12:
        midi_transpose += 1
    print(f"Transpose set to: {midi_transpose:+d} semitones")

def lower_midi_transpose():
    global midi_transpose
    if midi_transpose > -12:
        midi_transpose -= 1
    print(f"Transpose set to: {midi_transpose:+d} semitones")

def get_sf2_filenames():
    global nbr_sf2_files
    directory_path = Path(sf2_directory)
    # Use .glob() to find files matching the extension, then extract just the name
    file_names = [file.name for file in directory_path.glob("*.sf2")]
    nbr_sf2_files = len(file_names)
    return file_names

def get_nbr_sf2_files():
    return nbr_sf2_files

def lookup_prog_name():
    global current_instrument_name
    try:
        name_query = fs.sfpreset_name(current_sf_id, current_bank, current_program)
        if name_query:
            current_instrument_name = name_query
    except Exception:
        pass

def get_sf_file_index():
    files = get_sf2_filenames()
    for index, f in enumerate(files):
        if f == current_sf2_name:
            return index 
    return 0
        
def load_sf2_file(selected_sf2_index):
    global current_sf_id, current_bank, current_program, current_instrument_name, current_sf2_name
    filename = get_sf2_filenames()[selected_sf2_index]
    current_sf2_name = filename
    old_sf_id = current_sf_id
    # Load the new SoundFont file (returns a new unique ID)
    full_path = os.path.join(sf2_directory, filename) 
    current_sf_id = fs.sfload(full_path)
    # Select the program mapping using the new SoundFont ID
    # Parameters: (channel, sfid, bank, preset)
    fs.program_select(0, current_sf_id, 0, 0)
    # 4. Unload the old SoundFont to free up Raspberry Pi memory
    fs.sfunload(old_sf_id)
    current_bank = 0 
    current_program = 0
    lookup_prog_name()

def get_current_prog_details():
    return current_bank, current_program, current_instrument_name

def save_settings_to_file():
    print('save_settings_to_file')
    current_settings = {
    "master_volume": round(current_gain, 2),
    "midi_channel": get_midi_chan_display(),
    "transpose": midi_transpose,
    "soundfont_filename": current_sf2_name
    }
    save_settings(current_settings)
