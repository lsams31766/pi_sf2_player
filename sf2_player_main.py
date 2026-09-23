#sf2_player_main.py
'''
  Main code for PI ZERO SF2 Player project
'''
import time

from sf2_player_ui import init_buttons, home_screen, splash_screen
from sf2_player_fluidsynth import init_fluidsynth
from sf2_player_effects import start_effects_containers, set_effect_configuration


init_buttons()
splash_screen()
init_fluidsynth(effect_callback=start_effects_containers)
time.sleep(2)
set_effect_configuration('chorus_reverb')
home_screen()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nProgram stopped by user.")
