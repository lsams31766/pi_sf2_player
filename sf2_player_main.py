#sf2_player_main.py
'''
  Main code for PI ZERO SF2 Player project
'''
import time

from sf2_player_ui import init_buttons, home_screen, splash_screen
from sf2_player_fluidsynth import init_fluidsynth

init_buttons()
splash_screen()
init_fluidsynth()
time.sleep(2)
home_screen()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nProgram stopped by user.")
