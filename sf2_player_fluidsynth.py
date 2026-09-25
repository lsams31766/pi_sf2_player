#sf2_player_fluidsynth.py
# REQUIRES pyfluidsynth and mido libraries
import sys
import time
import os
import threading
import subprocess
import fluidsynth
import mido
from pathlib import Path
from sf2_player_settings import save_settings, load_settings
from sf2_player_controls import load_default_reverb_settings, load_default_chorus_settings

fs = None

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
nbr_sf2_files = 1 
current_sf2_name = 'unknown'


def find_launchkey_port():
    """Dynamically find the keyboard port name to avoid strict string mismatches."""
    ports = mido.get_input_names()
    print(f"Available MIDI input ports: {ports}")
    for port in ports:
        if 'Launchkey' in port:
            return port
    if ports:
        return ports[0]
    return None

def midi_listener_thread():
    """Background thread that captures USB MIDI, applies filters/transposition, and plays notes."""
    global midi_thread_running
    
    time.sleep(1.0)
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
                
                if input_filter_channel is not None:
                   if hasattr(msg, 'channel') and msg.channel != input_filter_channel:
                       continue 
                
                dest_channel = TARGET_MIDI_CHANNEL

                if msg.type == 'note_on':
                    #print('none on')
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
    if os.environ.get("SF2_PLAYER_PW_JACK_WRAPPED") == "1":
        return
    ld_path = os.environ.get("LD_LIBRARY_PATH", "")
    if "pipewire" in ld_path and "jack" in ld_path:
        return

    print("Relaunching under pw-jack so fluidsynth can reach pipewire's JACK layer...")
    env = os.environ.copy()
    env["SF2_PLAYER_PW_JACK_WRAPPED"] = "1"
    try:
        os.execvpe("pw-jack", ["pw-jack", sys.executable] + sys.argv, env)
    except FileNotFoundError:
        print("Warning: 'pw-jack' not found on PATH.")

def init_fluidsynth(effect_callback=None):
    """
    Initializes FluidSynth and starts MIDI listening.
    effect_callback: Optional function (like start_reverb_effect or start_chorus_effect) 
                     to wire audio routing after startup.
    """
    global fs, current_sf_id, current_bank, current_program, current_instrument_name, \
        current_sf2_name, current_gain, input_filter_channel, midi_transpose

    _ensure_pipewire_jack_wrapper()

    settings = load_settings()
    fs = fluidsynth.Synth()
    fs.setting('audio.jack.autoconnect', 0)
    fs.setting('audio.period-size', 128)
    fs.setting('audio.periods', 2)
    fs.setting('synth.sample-rate', 44100.0)
    fs.setting('midi.driver', 'alsa_seq')

    fs.start(driver="jack")

    sf_path = "/usr/share/sounds/sf2/"
    current_sf2_name = settings.get('soundfont_filename', 'default-GM.sf2')
    sf_id = fs.sfload(os.path.join(sf_path, current_sf2_name))
    
    temp_filter = settings.get('midi_channel', 'OMNI')
    if temp_filter == "OMNI":
        input_filter_channel = None
    else:
        input_filter_channel = int(temp_filter) - 1
    midi_transpose = settings.get('transpose', 0)

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

    current_gain = settings.get('master_volume', 0.5)
    fs.setting('synth.gain', current_gain)

    # Start MIDI listener thread
    t = threading.Thread(target=midi_listener_thread, daemon=True)
    t.start()

    # Execute passed audio effect callback if provided
    if effect_callback:
        effect_callback()

    try:
        print("Setting PipeWire default sink volume to 1.8...")
        subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "1.8"], check=True)
    except Exception as e:
        print(f"Warning: Could not set system volume via wpctl: {e}")

    print("\n--- Setup Complete! Play your Novation Launchkey 61 ---")
    print("Press Ctrl+C to stop the script.")

def previous_preset():
    global current_program, current_bank, current_sf_id, fs, current_instrument_name
    if current_program > 0:
        current_program -= 1
    else:
        print("Reached minimum program (0).")
        return

    if fs and current_sf_id > 0:
        fs.program_select(0, current_sf_id, current_bank, current_program)
        print(f"previous preset -> Switched to Bank: {current_bank}, Program: {current_program}")
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
    if input_filter_channel is None:
        return 'OMNI'
    return str(input_filter_channel + 1)

def lower_midi_chan():
    global input_filter_channel
    if input_filter_channel is None:
        input_filter_channel = 15 
    elif input_filter_channel > 0:
        input_filter_channel -= 1
    else:
        input_filter_channel = None 
    print(f"MIDI Filter Channel set to: {get_midi_chan_display()}")

def raise_midi_chan():
    global input_filter_channel
    if input_filter_channel is None:
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
    full_path = os.path.join(sf2_directory, filename) 
    current_sf_id = fs.sfload(full_path)
    fs.program_select(0, current_sf_id, 0, 0)
    fs.sfunload(old_sf_id)
    current_bank = 0 
    current_program = 0
    lookup_prog_name()

def get_current_prog_details():
    return current_bank, current_program, current_instrument_name

def save_settings_to_file(current_reverb_settings, current_chorus_settings, reverb_enabled, chorus_enabled):
    if current_reverb_settings == []:
        temp_reverb_settings = load_default_reverb_settings()
    else:
        temp_reverb_settings = current_reverb_settings
    if current_chorus_settings == []:
        temp_chorus_settings = load_default_chorus_settings()
    else:
        temp_chorus_settings = current_chorus_settings
    current_settings = {
        "master_volume": round(current_gain, 2),
        "midi_channel": get_midi_chan_display(),
        "transpose": midi_transpose,
        "soundfont_filename": current_sf2_name,
        "reverb_enabled":reverb_enabled,
        "chorus_enabled":chorus_enabled,
        "reverb":temp_reverb_settings,
        "chorus":temp_chorus_settings
    }
    save_settings(current_settings)