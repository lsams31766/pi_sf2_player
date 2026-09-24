#sf2_player_controls.py

#reverb controls
reverb_controls = [
    {"name":"delay", "min":0.02, "max":0.1, "default": 0.06, "inc": .01},
    {"name":"xover", "min":50, "max":1000, "default": 223, "inc": 10},
    {"name":"rt_low", "min":1, "max":8, "default": 2.75, "inc": .25},
    {"name":"rt_mid", "min":1, "max":8, "default": 2.75, "inc": .25},
    {"name":"damping", "min":1500, "max":24000, "default": 6000, "inc": 1000},
    {"name":"f1_freq", "min":40, "max":10000, "default": 159, "inc": .100},
    {"name":"f1_gain", "min":-20, "max":20, "default": 0, "inc": 5},
    {"name":"f2_freq", "min":40, "max":10000, "default": 2514.87, "inc": 100},
    {"name":"f2_gain", "min":-20, "max":20, "default": 0, "inc": 5},
    {"name":"out_mix", "min":0.00, "max":1.0, "default": 0.5, "inc": .1}
]

#chorus controls
chorus_controls = [
    {"name":"delay", "min":0.0, "max":30, "default": 1, "inc": 1},
    {"name":"mod_freq_1", "min":0.003, "max":10.0, "default": 0.25, "inc": .1},
    {"name":"mod_amp_1", "min":0.0, "max":10.0, "default": 1.0, "inc": .5},
    {"name":"mod_freq_2", "min":0.01, "max":30.0, "default": 0.125, "inc": .1},
    {"name":"mod_amp_2", "min":0.0, "max":3.0, "default": 0.5, "inc": .1}
]

def load_default_reverb_settings():
    l = []
    for control in  reverb_controls:
        l.append((control["name"],control['default']))
    return l

def load_default_chorus_settings():
    l = []
    for control in  chorus_controls:
        l.append((control["name"],control['default']))
    return l

#l = load_default_reverb_settings()
#m = l
#print(m)
