#sf2_player_ui.py
# show menus using the ST7789 display
# SEENGREAT module used for LCD and buttons
# config.py sets up the GPIO assignments
# REQUIRES: PIL, RPi.GPIO librarys

import spidev as SPI
import logging
import config  # LCD and IO pin definitions for SEENGREAT display/keys
import ST7789
import time
from PIL import Image, ImageDraw, ImageFont
from gpiozero import Button
from sf2_player_fluidsynth import next_preset, previous_preset, get_gain, set_gain, \
    lower_gain, raise_gain, lower_midi_chan, raise_midi_chan, \
    get_midi_chan_display, get_transpose, raise_midi_transpose, lower_midi_transpose,\
    get_sf2_filenames, get_nbr_sf2_files, load_sf2_file, \
    get_current_prog_details, save_settings_to_file, get_sf_file_index

#locations of menu items
HOME_BANK_X = 5
HOME_BANK_Y = 5
HOME_PROG_X = 5
HOME_PROG_Y = 45
HOME_PROG_NAME_X = 5
HOME_PROG_NAME_Y = 90
HOME_INFO_1_Y = 160
HOME_INFO_2_Y = 200
HOME_BTN_1_X = 5
HOME_BTN_2_X = 105
HOME_BTN_LINE_Y = 200

MENU_TITLE_X = 75
HOME_TITLE_Y = 5
HOME_SELECTION_X = 5
HOME_SEL1_Y = 45
HOME_SEL_Y_OFFSET = 40

#screens
SCRN_HOME = 1
SCRN_MENU = 2
SCRN_GLOBAL = 3
SCRN_LOAD_SF = 4
cur_screen = SCRN_HOME
cur_menu_selection = 0
nbr_menu_items = 4

GLBL_PARAM_VOL = 0
GLBL_PARAM_MIDI_CH = 1
GLBL_PARAM_TRANSPOSE = 2
cur_global_selection = GLBL_PARAM_VOL

logging.basicConfig(level=logging.DEBUG)

disp = ST7789.ST7789()
disp.Init()
disp.clear()
disp.bl_DutyCycle(100)
Font1 = ImageFont.truetype("Font/Font02.ttf",32)

home_bank = 0
home_program = 1
home_preset_name = 'Piano 1'

selected_sf2_index = -1 # will get updated in sf screen

def handle_home_screen(n):
    global cur_screen, home_bank, home_program, home_preset_name 
    if n == config.KEY1_PIN:
        # goto to menu screen
        cur_screen = SCRN_MENU
        menu_screen()
    if n == config.KEY_DOWN_PIN:
        # next program
        next_preset()
        home_screen()
    if n == config.KEY_UP_PIN:
        #previous program
        previous_preset()
        home_screen()

def handle_menu_screen(n):
    global cur_menu_selection,  cur_global_selection, cur_screen
    if n == config.KEY_DOWN_PIN:
        cur_menu_selection += 1
        if cur_menu_selection == 4:
            cur_menu_selection = 3
        menu_screen() # update it
    if n == config.KEY_UP_PIN:
        cur_menu_selection -= 1
        if cur_menu_selection < 0:
            cur_menu_selection = 0
        menu_screen() # update it
    if n == config.KEY_PRESS_PIN:
        if cur_menu_selection < 3:
            # items 0,1,2 are global params
            # item 3 is load soundfont
            cur_global_selection = cur_menu_selection
            cur_screen = SCRN_GLOBAL
            global_param_screen()
        if cur_menu_selection == 3:
            cur_screen = SCRN_LOAD_SF
            load_sf_screen()

def handle_global_screen(n):
    global cur_menu_selection,  cur_global_selection, cur_screen
    if cur_global_selection == GLBL_PARAM_VOL:
        if n == config.KEY_DOWN_PIN:
            lower_gain()
            global_param_screen()
        if n == config.KEY_UP_PIN:
            raise_gain()
            global_param_screen()
    if cur_global_selection == GLBL_PARAM_MIDI_CH:
        if n == config.KEY_DOWN_PIN:
            lower_midi_chan()
            global_param_screen()
        if n == config.KEY_UP_PIN:
            raise_midi_chan()
            global_param_screen()
    if cur_global_selection == GLBL_PARAM_TRANSPOSE:
        if n == config.KEY_DOWN_PIN:
            lower_midi_transpose()
            global_param_screen()
        if n == config.KEY_UP_PIN:
            raise_midi_transpose()
            global_param_screen()

def handle_load_sf_screen(n):
    global selected_sf2_index
    nbr_files = get_nbr_sf2_files()
    if n == config.KEY_DOWN_PIN:
        if selected_sf2_index == nbr_files - 1:
            return # on the last file
        selected_sf2_index += 1
        load_sf_screen()
        load_sf2_file(selected_sf2_index)
    if n == config.KEY_UP_PIN:
        if selected_sf2_index == 0:
            return # on the first file
        selected_sf2_index -= 1
        load_sf_screen()
        load_sf2_file(selected_sf2_index)

def handle_btn(n):
    global cur_screen
    
    # Map pin numbers back to their device objects to check state
    pin_map = {
        config.KEY_UP_PIN: disp.GPIO_KEY_UP_PIN,
        config.KEY_DOWN_PIN: disp.GPIO_KEY_DOWN_PIN,
        config.KEY_LEFT_PIN: disp.GPIO_KEY_LEFT_PIN,
        config.KEY_RIGHT_PIN: disp.GPIO_KEY_RIGHT_PIN,
        config.KEY_PRESS_PIN: disp.GPIO_KEY_PRESS_PIN,
        config.KEY1_PIN: disp.GPIO_KEY1_PIN,
        config.KEY2_PIN: disp.GPIO_KEY2_PIN,
        config.KEY3_PIN: disp.GPIO_KEY3_PIN,
        config.KEY4_PIN: disp.GPIO_KEY4_PIN,
    }
    
    device = pin_map.get(n)
    # If the device is not active (i.e. it was a release event), ignore it!
    if device and not device.is_active:
        return

    if cur_screen == SCRN_HOME:
        handle_home_screen(n)
    if n == config.KEY2_PIN and cur_screen != SCRN_HOME:
        cur_screen = SCRN_HOME
        home_screen()
    if cur_screen == SCRN_MENU:
        handle_menu_screen(n)
    if cur_screen == SCRN_GLOBAL:
        handle_global_screen(n)
    if cur_screen == SCRN_LOAD_SF:
        handle_load_sf_screen(n)
    # key 3 is save global settings
    if n == config.KEY3_PIN:
        save_settings_to_file()



def init_buttons():
    # Hook into the existing DigitalInputDevice objects already created by config.py / ST7789
    disp.GPIO_KEY1_PIN.when_activated = lambda: handle_btn(config.KEY1_PIN)
    disp.GPIO_KEY2_PIN.when_activated = lambda: handle_btn(config.KEY2_PIN)
    disp.GPIO_KEY3_PIN.when_activated = lambda: handle_btn(config.KEY3_PIN)
    disp.GPIO_KEY4_PIN.when_activated = lambda: handle_btn(config.KEY4_PIN)

    disp.GPIO_KEY_UP_PIN.when_activated = lambda: handle_btn(config.KEY_UP_PIN)
    disp.GPIO_KEY_DOWN_PIN.when_activated = lambda: handle_btn(config.KEY_DOWN_PIN)
    disp.GPIO_KEY_LEFT_PIN.when_activated = lambda: handle_btn(config.KEY_LEFT_PIN)
    disp.GPIO_KEY_RIGHT_PIN.when_activated = lambda: handle_btn(config.KEY_RIGHT_PIN)
    disp.GPIO_KEY_PRESS_PIN.when_activated = lambda: handle_btn(config.KEY_PRESS_PIN)

def splash_screen():
    # blue background
    image1 = Image.new("RGB", (240, 240), (0, 0, 255))
    draw = ImageDraw.Draw(image1)
    # draw.text((5, 160), '1234567890', fill = "WHITE",font=Font1)
    # top 2 lines
    draw.text((HOME_BANK_X, HOME_BANK_Y), 'PI SF2 PLAYER' + str(home_bank), fill = "WHITE",font=Font1)
    draw.text((HOME_PROG_NAME_X, HOME_PROG_NAME_Y), 'REV 1.0', fill = "WHITE",font=Font1)
    im_r=image1.rotate(90)
    disp.ShowImage(im_r)

def home_screen():
    # blue background
    image1 = Image.new("RGB", (240, 240), (0, 0, 255))
    draw = ImageDraw.Draw(image1)
    # draw.text((5, 160), '1234567890', fill = "WHITE",font=Font1)
    # top 2 lines
    bank, prog, prog_name = get_current_prog_details()
    draw.text((HOME_BANK_X, HOME_BANK_Y), 'BANK: ' + str(bank), fill = "WHITE",font=Font1)
    draw.text((HOME_PROG_X, HOME_PROG_Y), 'PROG: ' + str(prog), fill = "WHITE",font=Font1)
    draw.text((HOME_PROG_NAME_X, HOME_PROG_NAME_Y), prog_name, fill = "WHITE",font=Font1)
    # bottom 2 lines global settings
    fVolume = get_gain() # 0.0 to 1.0
    nVolume = int(fVolume * 100) # 0 to 100
    ch = get_midi_chan_display()
    tr = get_transpose()
    fname = get_sf2_filenames()[selected_sf2_index]
    draw.text((HOME_PROG_NAME_X, HOME_INFO_1_Y), f'Vol:{nVolume} M:{ch} Tr:{tr}', fill = "WHITE",font=Font1)
    draw.text((HOME_PROG_NAME_X, HOME_INFO_2_Y), f'{fname}', fill = "WHITE",font=Font1)
    im_r=image1.rotate(90)
    disp.ShowImage(im_r)

def menu_screen():
    items = ['VOLUME', 'MIDI CH', 'TRANSPOSE', 'LOAD SOUNDFONT']
    image1 = Image.new("RGB", (240, 240), (0, 0, 255))
    draw1 = ImageDraw.Draw(image1)
    y = HOME_SEL1_Y + 20
    draw1.text((MENU_TITLE_X, HOME_TITLE_Y), 'SELECT:', fill = "WHITE",font=Font1)
    for index, item in enumerate(items):
        s = item
        if index == cur_menu_selection:
            s = '->' + item
        draw1.text((HOME_SELECTION_X, y), s, fill = "WHITE",font=Font1)
        y += HOME_SEL_Y_OFFSET
    im_r1=image1.rotate(90)
    disp.ShowImage(im_r1)

def global_param_screen():
    '''
       GLOBAL SETTING
    
       VOLUME: xxx
         or 
       MIDI CHAN: xxx
        or
       TRANSPOSE:  xxx
    '''
    #print(f'GLOBAL PARAM SCREEN, cur_global_selection {cur_global_selection}')
    image1 = Image.new("RGB", (240, 240), (0, 0, 255))
    draw1 = ImageDraw.Draw(image1)

    y = 2 * HOME_SEL1_Y
    draw1.text((5, HOME_TITLE_Y), 'GLOBAL SETTING', fill = "WHITE",font=Font1)
    if cur_global_selection == GLBL_PARAM_VOL:
        fVolume = get_gain() # 0.0 to 1.0
        nVolume = int(fVolume * 100) # 0 to 100
        #print(f'fVolume {fVolume} nVolume {nVolume}')
        draw1.text((HOME_SELECTION_X, y), 'VOLUME: ' + str(nVolume), fill = "WHITE",font=Font1)
    elif cur_global_selection == GLBL_PARAM_MIDI_CH:
        ch = get_midi_chan_display()
        draw1.text((HOME_SELECTION_X, y), 'MIDI CH: ' + ch, fill = "WHITE",font=Font1)
    elif cur_global_selection == GLBL_PARAM_TRANSPOSE:
        tr = get_transpose()
        draw1.text((HOME_SELECTION_X, y), 'TRANSPOSE: ' + str(tr), fill = "WHITE",font=Font1)
    im_r1=image1.rotate(90)
    disp.ShowImage(im_r1)

def load_sf_screen():
    '''
       LOAD SOUNDFONT
    
       ->file1.sf2
       file2.sf2
       file3.sf2
       file4.sf2
    '''
    global selected_sf2_index
    image1 = Image.new("RGB", (240, 240), (0, 0, 255))
    draw1 = ImageDraw.Draw(image1)

    y = HOME_SEL1_Y + 20
    draw1.text((5, HOME_TITLE_Y), 'LOAD SOUNDFONT', fill = "WHITE",font=Font1)
    files = get_sf2_filenames()
    if selected_sf2_index < 0:
        selected_sf2_index = get_sf_file_index()
    for index, f in enumerate(files):
        if index == selected_sf2_index:
            s = '->' + f 
        else:
            s = f
        draw1.text((HOME_SELECTION_X, y), s, fill = "WHITE",font=Font1)
        y += HOME_SEL_Y_OFFSET
    im_r1=image1.rotate(90)
    disp.ShowImage(im_r1)

