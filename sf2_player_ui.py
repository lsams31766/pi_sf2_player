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
    get_current_prog_details, save_settings_to_file, get_sf_file_index, \
    layer_sounds, lookup_prog_name_from_prog_number, fs_turn_off_layering, \
    split_keyboard, turn_off_split_keyboard
from sf2_player_effects import set_effect_configuration, set_effect_parameter
from sf2_player_controls import load_default_reverb_settings, \
   load_default_chorus_settings, reverb_controls, chorus_controls
from sf2_player_settings import load_settings

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
SCRN_EFFECTS = 5
SCRN_EFFECTS_SETTINGS = 6
SCREN_LAYER_SPLIT = 7
cur_screen = SCRN_HOME

cur_menu_selection = 0
nbr_menu_items = 6
MNU_VOLUME = 0
MNU_MIDI_CH = 1
MNU_TRANSPOSE = 2
MNU_LOAD_SF = 3
MNU_EFFECTS = 4
MNU_LAYER_SPLIT = 5

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
effects_configured = False
sReverbState = 'OFF'
sChorusState = 'OFF'
effects_item_selected = 0

effect_settings_type = 'reverb' #reverb or chorus
effect_settings_selected = 0 # which settings is being edited
current_reverb_settings = [] # list of current reverb settings
current_chorus_settings = [] # list of current chorus settings
nbr_settings_per_page = 4

selected_sf2_index = -1 # will get updated in sf screen

layer_split_choices = ['LAYER','SPLIT']
layer_split_index = 0
cur_layer_split_choice = 0 # 0 for layer 1 for split
split_point = 60
layer_1_prog_number = 0
layer_2_prog_number = 1
MAX_PROG_NUMBER = 127
MAX_MIDI_NOTE_NUMBER = 108
MIN_MIDI_NOTE_NUMBER = 21

def handle_home_screen(n):
    global cur_screen, home_bank, home_program, home_preset_name
    if n == config.KEY1_PIN:
        # goto to menu screen
        cur_screen = SCRN_MENU
        cur_menu_selection = 0
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
    global cur_menu_selection,  cur_global_selection, cur_screen, \
           effects_item_selected
    if n == config.KEY_DOWN_PIN:
        cur_menu_selection += 1
        if cur_menu_selection >= nbr_menu_items:
            cur_menu_selection = nbr_menu_items - 1
        menu_screen() # do not increment here

    if n == config.KEY_UP_PIN:
        cur_menu_selection -= 1
        if cur_menu_selection < 0:
            cur_menu_selection = 0
        menu_screen() # update it
    if n == config.KEY_PRESS_PIN:
        if cur_menu_selection in [MNU_VOLUME,MNU_MIDI_CH,MNU_TRANSPOSE]:
            cur_global_selection = cur_menu_selection
            cur_screen = SCRN_GLOBAL
            global_param_screen()
        if cur_menu_selection == MNU_LOAD_SF:
            cur_screen = SCRN_LOAD_SF
            load_sf_screen()
        if cur_menu_selection == MNU_EFFECTS:
            effects_item_selected = 0
            cur_screen = SCRN_EFFECTS
            effects_screen()
        if cur_menu_selection == MNU_LAYER_SPLIT:
            effects_item_selected = 0
            cur_screen = SCREN_LAYER_SPLIT
            layer_split_screen()


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

def update_effects_state():
    if sReverbState == 'OFF' and sChorusState == 'OFF':
        set_effect_configuration('none')
    if sReverbState == 'ON' and sChorusState == 'OFF':
        set_effect_configuration('reverb')
    if sReverbState == 'OFF' and sChorusState == 'ON':
        set_effect_configuration('chorus')
    if sReverbState == 'ON' and sChorusState == 'ON':
        set_effect_configuration('chorus_reverb')

def handle_effects_settings_screen(n):
    global effects_item_selected, sReverbState, sChorusState, \
        effect_settings_type, effect_settings_selected, \
        cur_screen
    if n == config.KEY_DOWN_PIN:
        effects_item_selected += 1
        if effects_item_selected > 1:
            effects_item_selected = 1
        effects_screen()
    if n == config.KEY_UP_PIN:
        effects_item_selected -= 1
        if effects_item_selected < 0:
            effects_item_selected = 0
        effects_screen()
    if n == config.KEY_RIGHT_PIN:
        if effects_item_selected == 0 and sReverbState == 'OFF': # TURN ON REVERB
            sReverbState = 'ON'
        if effects_item_selected == 1 and sChorusState == 'OFF': # TURN ON CHORUS
            sChorusState = 'ON'
        update_effects_state()
        effects_screen()
    if n == config.KEY_LEFT_PIN:
        if effects_item_selected == 0 and sReverbState == 'ON': # TURN OFF REVERB
            sReverbState = 'OFF'
        if effects_item_selected == 1 and sChorusState == 'ON': # TURN OFF CHORUS
            sChorusState = 'OFF'
        update_effects_state()
        effects_screen()
    if n == config.KEY_PRESS_PIN: # edit the effect
        if effects_item_selected == 0 and sReverbState == 'ON':
            effect_settings_type = 'reverb'
            cur_screen = SCRN_EFFECTS_SETTINGS
            effect_settings_selected = 0
            effects_settings_screen()
        if effects_item_selected == 1 and sChorusState == 'ON':
            effect_settings_type = 'chorus'
            cur_screen = SCRN_EFFECTS_SETTINGS
            effect_settings_selected = 0
            effects_settings_screen()

def handle_reverb_chorus_settings_screen(n):
    global effect_settings_selected
    #print(f'handle_reverb_chorus_settings_screen n {n}')
    if n == config.KEY_DOWN_PIN:
        effect_settings_selected += 1
        effects_settings_screen()
    if n == config.KEY_UP_PIN:
        effect_settings_selected -= 1
        if effect_settings_selected < 0:
            effect_settings_selected = 0
        effects_settings_screen()
    if n == config.KEY_RIGHT_PIN:
        update_effects_value(True) # increment
        effects_settings_screen()
    if n == config.KEY_LEFT_PIN:
        update_effects_value(False) # decrement
        effects_settings_screen()

def handle_layer_split_screen(n):
    global cur_layer_split_choice, split_point, layer_split_index, \
        layer_1_prog_number, layer_2_prog_number
    #print(f'handle_layer_split_screen n {n} choice {cur_layer_split_choice} \
    # split {split_point} index {layer_split_index}')
    if cur_layer_split_choice == 0:
        last_index = 1
    else:
        last_index = 2
        layer_split_screen()
    if n == config.KEY_DOWN_PIN:
        #print('key_down')
        layer_split_index += 1
        if layer_split_index > last_index:
            layer_split_index = last_index
        layer_split_screen()
    if n == config.KEY_UP_PIN:
        #print('key_up')
        layer_split_index -= 1
        if layer_split_index < 0:
            layer_split_index = 0
        layer_split_screen()

    if n == config.KEY_PRESS_PIN: # toggle layer/split
        #print('key_press')
        if cur_layer_split_choice == 0:
            cur_layer_split_choice = 1
            split_keyboard(split_point)
        else:
            cur_layer_split_choice = 0
            turn_off_split_keyboard()
        layer_split_screen()
    if n == config.KEY_RIGHT_PIN: # increment element
        #print('key_right')
        if (cur_layer_split_choice == 0 and layer_split_index == 0) or \
           (cur_layer_split_choice == 1 and layer_split_index == 1):
            layer_1_prog_number += 1
            if layer_1_prog_number > MAX_PROG_NUMBER:
                layer_1_prog_number = MAX_PROG_NUMBER
            else:
                update_layer_sound()
        elif (cur_layer_split_choice == 0 and layer_split_index == 1) or \
             (cur_layer_split_choice == 1 and layer_split_index == 2):
            layer_2_prog_number += 1
            if layer_2_prog_number > MAX_PROG_NUMBER:
                layer_2_prog_number = MAX_PROG_NUMBER
            else:
                update_layer_sound()
        elif (cur_layer_split_choice == 1 and layer_split_index == 0): 
            split_point += 1
            if split_point > MAX_MIDI_NOTE_NUMBER:
                split_point = MAX_MIDI_NOTE_NUMBER
            else:
                split_keyboard(split_point)
        layer_split_screen()
    if n == config.KEY_LEFT_PIN: # decrement element
        #print('key_left')
        if (cur_layer_split_choice == 0 and layer_split_index == 0) or \
           (cur_layer_split_choice == 1 and layer_split_index == 1):
            layer_1_prog_number -= 1
            if layer_1_prog_number < 0:
                layer_1_prog_number = 0
        elif (cur_layer_split_choice == 0 and layer_split_index == 1) or \
             (cur_layer_split_choice == 1 and layer_split_index == 2):
            layer_2_prog_number -= 1
            if layer_2_prog_number < 0:
                layer_2_prog_number = 0
        elif (cur_layer_split_choice == 1 and layer_split_index == 0): 
            split_point -= 1
            if split_point < MIN_MIDI_NOTE_NUMBER:
                split_point = MIN_MIDI_NOTE_NUMBER
            else:
                split_keyboard(split_point)
        layer_split_screen()

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

    #print(f'handle_btn n{n} screen {cur_screen}')
    if cur_screen == SCRN_HOME:
        handle_home_screen(n)
    elif n == config.KEY2_PIN and cur_screen != SCRN_HOME:
        cur_screen = SCRN_HOME
        home_screen()
    elif cur_screen == SCRN_MENU:
        handle_menu_screen(n)
    elif cur_screen == SCRN_GLOBAL:
        handle_global_screen(n)
    elif cur_screen == SCRN_LOAD_SF:
        handle_load_sf_screen(n)
    elif cur_screen == SCRN_EFFECTS:
        handle_effects_settings_screen(n)
    elif cur_screen == SCRN_EFFECTS_SETTINGS:
        handle_reverb_chorus_settings_screen(n)
    elif cur_screen == SCREN_LAYER_SPLIT:
        handle_layer_split_screen(n)
    # key 3 is save global settings
    if n == config.KEY3_PIN:
        reverb_enabled = True if sReverbState == 'ON' else False
        chorus_enabled = True if sChorusState == 'ON' else False
        save_settings_to_file(current_reverb_settings, current_chorus_settings,
           reverb_enabled, chorus_enabled)
    # key 4 turns off layering
    if n == config.KEY4_PIN:
        turn_off_layering()

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

def update_all_effects_settings(effects_type):
    global current_reverb_settings, current_chorus_settings
    #print(f'->update_all_effects_settings {effects_type}')
    ls = load_settings()
    if effects_type == 'reverb':
        current_reverb_settings = convert_json_to_tuples_list(ls,'reverb')
        # push them to the effect
        for item in current_reverb_settings:
            cur_name = item[0]
            cur_value = item[1]
            set_effect_parameter(effects_type, cur_name, cur_value)
    if effects_type == 'chorus':
        current_chorus_settings = convert_json_to_tuples_list(ls,'chorus')
        # push them to the effect
        for item in current_chorus_settings:
            cur_name = item[0]
            cur_value = item[1]
            set_effect_parameter(effects_type, cur_name, cur_value)
 
def load_initial_effects():
    global sReverbState, sChorusState
    #print('-->load_initial_effects')
    # if we just loaded the program, set reverb/chorus on if necessary
    ls = load_settings() # see if reverb/chorus enabled
    r_en = ls.get('reverb_enabled',None)
    c_en = ls.get('chorus_enabled',None)
    if r_en != None and r_en == True:
        sReverbState = 'ON'
        update_all_effects_settings('reverb')
    if c_en != None and c_en == True:
        sChorusState = 'ON'
        update_all_effects_settings('chorus')
    update_effects_state()
    effects_configured = True    

def home_screen():
    global effects_configured
    if effects_configured == False:
        load_initial_effects()
        effects_configured = True
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
    # handle paging - only 4 items per screen
    items_page_0 = ['VOLUME', 'MIDI CH', 'TRANSPOSE', 'LOAD SOUNDFONT']
    items_page_1 = ['EFFECTS','LAYER/SPLIT']
    image1 = Image.new("RGB", (240, 240), (0, 0, 255))
    draw1 = ImageDraw.Draw(image1)
    # paging
    page = cur_menu_selection // nbr_settings_per_page
    if page == 0:
        list_items = items_page_0
    if page == 1:
        list_items = items_page_1
    first_index = page * nbr_settings_per_page
    last_index = min(first_index + nbr_settings_per_page, first_index + len(list_items))
    # done paging
    y = HOME_SEL1_Y + 20
    draw1.text((MENU_TITLE_X, HOME_TITLE_Y), 'SELECT:', fill = "WHITE",font=Font1)
    print(f'page {page} first {first_index}, last {last_index}, list_items {list_items}')
    i = first_index
    index = 0
    while i < last_index:
        s = list_items[index]
        if i == cur_menu_selection:
            s = '->' + s
        draw1.text((HOME_SELECTION_X, y), s, fill = "WHITE",font=Font1)
        y += HOME_SEL_Y_OFFSET
        i += 1
        index += 1
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

def effects_screen():
    '''
       EFFECTS SETTING
    
       REVERB: OFF
       CHORUS: OFF
    '''
    #print(f'EFFECTS SETTING SCREEN')
    image1 = Image.new("RGB", (240, 240), (0, 0, 255))
    draw1 = ImageDraw.Draw(image1)

    y = 2 * HOME_SEL1_Y
    # handle text and selection arrow
    sReverb = 'REVERB: ' + sReverbState
    sChorus = 'CHORUS: ' + sChorusState
    if effects_item_selected == 0:
        sReverb = '->' + sReverb
    if effects_item_selected == 1:
        sChorus = '->' + sChorus
    
    draw1.text((5, HOME_TITLE_Y), 'EFFECTS SETTING', fill = "WHITE",font=Font1)
    draw1.text((HOME_SELECTION_X, y), sReverb, fill = "WHITE",font=Font1)
    y += HOME_SEL1_Y
    draw1.text((HOME_SELECTION_X, y), sChorus, fill = "WHITE",font=Font1)
    im_r1=image1.rotate(90)
    disp.ShowImage(im_r1)

def convert_json_to_tuples_list(loaded_settings, effect_type):
    # get the params for effect_type given
    p = loaded_settings[effect_type]
    # put in list, in form ('delay', 1), etc
    l = []
    for item in p:
        #['delay', 0.06],  to ('delay', 1)
        l.append((item[0],item[1]))
    return l 

def effects_settings_screen():
    '''
       REVERB SETTINGS  -> can be CHORUS SETTINGS
    
       REVERB: OFF
       CHORUS: OFF
    '''
    # nbr_settings_per_page = 4
    global current_reverb_settings, current_chorus_settings, effect_settings_selected
    #print(f'REVERB/CHORUS SETTING SCREEN')
    image1 = Image.new("RGB", (240, 240), (0, 0, 255))
    draw1 = ImageDraw.Draw(image1)
    y = 2 * HOME_SEL1_Y - 20
    # if current settings is blank, load defaults
    temp_settings = []
    if effect_settings_type == 'reverb':
        title_text = "REVERB SETTINGS"
        # if we don't have current settings
        #  1) try to read saved settings
        #  2) if no saved settings, then use default settings
        if current_reverb_settings == []:
            # try to get saved settings
            print('-->Reverb settings not found')
            ls = load_settings()
            print(f'-->ls {ls}')
            if ls.get('reverb_enabled','None') != None:
                current_reverb_settings = convert_json_to_tuples_list(ls,'reverb')
                print(f'-->current_reverb_settings {current_reverb_settings}')
            else:
                current_reverb_settings = load_default_reverb_settings()
            temp_settings = current_reverb_settings
        else:
            temp_settings = current_reverb_settings
    if effect_settings_type == 'chorus':
        title_text = "CHORUS SETTINGS"
        # if we don't have current settings
        #  1) try to read saved settings
        #  2) if no saved settings, then use default settings
        if current_chorus_settings == []:
            # try to get saved settings
            ls = load_settings()
            if ls.get('chorus_enabled','None') != None:
                current_chorus_settings = convert_json_to_tuples_list(ls,'chorus')
            else:
                current_chorus_settings = load_default_chorus_settings()
            temp_settings = current_chorus_settings
        else:
            temp_settings = current_chorus_settings
    draw1.text((5, HOME_TITLE_Y), title_text, fill = "WHITE",font=Font1)
    # paging
    if effect_settings_selected >= len(temp_settings):
        effect_settings_selected = len(temp_settings) -1
    page = effect_settings_selected // nbr_settings_per_page
    first_index = page * nbr_settings_per_page
    last_index = min(first_index + nbr_settings_per_page, len(temp_settings))
    print(f'temp_settings {temp_settings}')
    print(f'range {first_index} to {last_index}')
    print(f'effect_settings_selected {effect_settings_selected}')
    i = first_index
    while i < last_index:
        s = f"{temp_settings[i][0]}: {temp_settings[i][1]}"
        if i == effect_settings_selected:
            s = '->' + s
        draw1.text((HOME_SELECTION_X, y), s, fill = "WHITE",font=Font1)
        y += HOME_SEL_Y_OFFSET
        i += 1
    im_r1=image1.rotate(90)
    disp.ShowImage(im_r1)

def get_range(cur_params, effect_type):
    val_name = cur_params[0]
    if effect_type == 'reverb':
        controls = reverb_controls
    if effect_type == 'chorus':
        controls = chorus_controls
    for item in controls:
        if item["name"] == val_name:
            return item 

def format_number(val):
    if isinstance(val, int):
        return val
    elif isinstance(val, float):
        return round(val, 2)
    return val

def update_effects_value(increment=True):
    global current_reverb_settings, current_chorus_settings
    # cur is name of param and current value
    if effect_settings_type == 'reverb':
        cur = current_reverb_settings[effect_settings_selected]
    if effect_settings_type == 'chorus':
        cur = current_chorus_settings[effect_settings_selected]
    cur_name = cur[0]
    cur_value = cur[1]
    # val_range is possible range of values and increment
    val_range = get_range(cur, effect_settings_type)
    if increment == True:
        new_value = min(cur[1] + val_range['inc'], val_range['max'])
    else: #decrement
        new_value = max(cur[1] - val_range['inc'], val_range['min'])
    new_value = format_number(new_value) # limit to 2 decimal places
    if effect_settings_type == 'reverb':
        current_reverb_settings[effect_settings_selected] = (cur_name, new_value)
    if effect_settings_type == 'chorus':
        current_chorus_settings[effect_settings_selected] = (cur_name, new_value)
    # change on the jalv instance
    set_effect_parameter(effect_settings_type, cur_name, new_value)
    
def layer_split_screen():
    #TODO ability to turn off layer/split
    image1 = Image.new("RGB", (240, 240), (0, 0, 255))
    draw1 = ImageDraw.Draw(image1)
    # layer or split title
    if cur_layer_split_choice == 0:
        s = 'LAYER'
    else:
        s = 'SPLIT'
    draw1.text((5, HOME_TITLE_Y), s, fill = "WHITE",font=Font1)
    y = HOME_TITLE_Y + HOME_SEL_Y_OFFSET
    # only show this if in split mode
    if cur_layer_split_choice == 1: # split
        s = f'SPLIT AT {split_point}'
        if layer_split_index == 0:
            s = '->' + s
        draw1.text((HOME_SELECTION_X, y), s, fill = "WHITE",font=Font1)
    y = 2 * HOME_SEL1_Y
    # prog 1 selection
    s = f'PROG1: {layer_1_prog_number}'
    if (cur_layer_split_choice == 0 and layer_split_index == 0) or \
    (cur_layer_split_choice == 1 and layer_split_index == 1):
        s = '->' + s
    draw1.text((HOME_SELECTION_X, y), s, fill = "WHITE",font=Font1)
    y += HOME_SEL_Y_OFFSET
    s = lookup_prog_name_from_prog_number(layer_1_prog_number)
    draw1.text((HOME_SELECTION_X, y), s, fill = "WHITE",font=Font1)
    # prog 2 selection
    y += HOME_SEL_Y_OFFSET
    s = f'PROG2: {layer_2_prog_number}'
    if (cur_layer_split_choice == 0 and layer_split_index == 1) or \
    (cur_layer_split_choice == 1 and layer_split_index == 2):
        s = '->' + s
    draw1.text((HOME_SELECTION_X, y), s, fill = "WHITE",font=Font1)
    y += HOME_SEL_Y_OFFSET - 5
    s = lookup_prog_name_from_prog_number(layer_2_prog_number)
    draw1.text((HOME_SELECTION_X, y), s, fill = "WHITE",font=Font1)
    im_r1=image1.rotate(90)
    disp.ShowImage(im_r1)

def update_layer_sound():
    layer_sounds(midi_chan1=1, bank1=0, prog1=layer_1_prog_number, midi_chan2=2, bank2=0, prog2=layer_2_prog_number)

def turn_off_layering():
    print("LAYERING turned off")
    fs_turn_off_layering() 
    home_screen()

