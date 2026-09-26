# pi_sf2_player

1.0 Version

**Current Features:**
- Select a program from a soundfonts sf2 file and play it
- Adjust Global Volume, Midi Channel, Note Transpose
- Load alternate soundfont
- Add reverb and/or chorus effect
- Split or Layer 2 sounds
- Saves Global and Effects settings for later recall

**Future Features:**
- Save the Split/Layer as a Patch to recall later
- Play MIDI file
- Show Split/Layer patch vs single program on MAIN screen

**Future Version:**
- Touchscreen for easier Naviation
- Encoder for quicker program and parameter selection

**Hardware and Controls:**<br>
(Seengreat LCD + joystick + 4 buttons)<br>
(PCM 5102 DAC)<br>
LCD is 128 x 128 pixels (about 16 x 6 charachters)<br>
KEY_1: MENU<br>
KEY_2: HOME SCREEN<br>
KEY_3: SAVE Globl and Current Program value to File sf2_settings.json<br>
KEY_4: TURN OFF Layer/Split<br>
JOY_DOWN: Next MENU item<br>
JOY_UP: Previous MENU item<br>
JOY_RIGHT: Increase Value<br>
JOY_LEFT: Decrease Value<br>
JOY_SW: Go into Menu / Swith between layer/split mode

**How To Install program:**
  Raspberry PI 3 install (should work on Raspberry Pi 4/5)
  - Install Bookworm no GUI to SD CARD
  - sudo raspi-config
      ENABLE SPI
      SETUP WIFI Network/Passowrd/Enable SSH
      reboot
  - sudo apt install python3-pil
  - sudo apt install python3-numpy
  - sudo apt install python3-pip
  - pip install pyfluidsynth --break-system-packages
  - sudo apt install python3-mido python3-rtmidi
  - pip install python-osc --break-system-packages
  - Copy all sf2_player*.py programs, ST7789.py, config.py, FONT to dir on RPI3

**TO RUN:**
  cd to the directory the .py files were loaded to
  python3 sf2_player_main.py

## WIRING CONNECTIONS to Raspberry Pi 3:

| Pin | Pi Signal | Connection / Target |
| :--- | :--- | :--- |
| **1** | 3V3 | TO XMST OF DAC |
| **2** | 5V | TO VIN OF DAC |
| **6** | GND | TO GND OF DAC |
| **7** | GPIO4 | — |
| **12** | GPIO18 | TO BCK OF DAC |
| **14** | GND | TO SCK OF DAC |
| **15** | GPIO22 | TO KEY3 OF SEENGREAT |
| **16** | GPIO23 | TO KEY4 OF SEENGREAT |
| **17** | 3V3 | TO VSYS of SEENGREAT |
| **18** | GPIO24 | TO KEY1 of SEENGREAT |
| **19** | GPIO10/MOSI | TO SDA of SEENGREAT |
| **20** | GND | — |
| **21** | GPIO9/MISO | — |
| **22** | GPIO25 | TO DC of SEENGREAT |
| **23** | GPIO11/SCLK | TO SCK of SEENGREAT |
| **24** | GPIO8 | TO CS of SEENGREAT |
| **25** | GND | TO GND OF SEENGREAT |
| **26** | GPIO7 | — |
| **27** | GPIO0 | TO RST of SEENGREAT |
| **28** | GPIO1 | TO BLK of SEENGREAT |
| **29** | GPIO5 | TO LEFT OF SEENGREAT |
| **30** | GND | — |
| **31** | GPIO6 | TO UP OF SEENGREAT |
| **32** | GPIO12 | TO KEY2 OF SEENGREAT |
| **33** | GPIO13 | TO JS SW OF SEENGREAT |
| **34** | GND | — |
| **35** | GPIO19 | TO LCK of DAC |
| **36** | GPIO27 | TO KEY1 OF SEENGREAT |
| **37** | GPIO26 | TO DOWN OF SEENGREAT |
| **38** | GPIO20 | TO RIGHT OF SEENGREAT |
| **39** | GND | — |
| **40** | GPIO21 | TO DIN OF DAC |

---

You can use a Raspberry Pi PICO breakout board to plug Seengreat module into, and the Terminal block output:

### PICO BREAKOUT BOARD to SEENGREAT PINS

| SEENGREAT | DESC | WHITTEN |  TO PI ZERO W |
| :--- | :--- | :--- | :--- |
| **(Left Side)** | - | - | - |
| - | | | |
| **VSYS** | 3.3V | GPI1 | 3V3 |
| - | | | |
| - | | | |
| - | | | |
| - | | | |
| - | | | |
| - | | | |
| - | | | |
| - | | | |
| - | | | |
| - | | | |
| - | | | |
| - | | | |
| **DOWN** | DN | GP11 | 37-GPIO26 |
| **RIGHT** | RT | GP12 | 38-GPIO20 |
| **UP** | UP | GPI13 | 31-GPIO6
| - |  |  |  |
| **CENT** | CENT | GP14 | 33-GPIO13
| **LEFT** | LEFT | GP15 | 29-GPIO5
| **(Right Side)** | - | - | - |
| **GND** | GND | GND | - |
| **K4** | K4 | 3EN | 16-GPIO23 |
| **K3** | K3 | 3OUT | 15-GPIO22 |
| **K2** | K2 | AVREF | 32-GPIO12 |
| **CS** | CS | GP28 | 24-GPIO8 |
| **GND** | GND | GND | 25-GND |
| **SCK** | SCK | GP27 | 23-GPIO11 |
| **SDA** | SDA | GP26 | 19-GPIO10 |
| **K1** | K1 | RUN | 18-GPIO24 |
| - | | | | 
| **D/C** | D/C | GP20 | 22-GPIO25 |
| **RST** | RST | GP19 | 27-GPIO0 |
| **BL** | BL | GP18 | 28-GPIO1 |
| **GND** | GND | GND | *(Note: GNDs are all connected on the SEENGREAT display)* |
| - | | | |
| - | | | |
