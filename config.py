import os
import sys
import time
import spidev
import logging
import numpy as np
from gpiozero import *

# GPIO define (Aligned directly with your hardware routing)
KEY_UP_PIN     = 6 
KEY_DOWN_PIN   = 26
KEY_LEFT_PIN   = 5
KEY_RIGHT_PIN  = 20
KEY_PRESS_PIN  = 13

KEY1_PIN       = 24
KEY2_PIN       = 12  
KEY3_PIN       = 22 
KEY4_PIN       = 23   


class RaspberryPi:
    def __init__(self,spi=spidev.SpiDev(0,0),spi_freq=40000000,rst = 0,dc = 25,bl = 1,bl_freq=1000,i2c=None,i2c_freq=100000):
        self.np=np
        self.INPUT = False
        self.OUTPUT = True

        self.SPEED  =spi_freq
        self.BL_freq=bl_freq

        self.GPIO_RST_PIN= self.gpio_mode(rst,self.OUTPUT)
        self.GPIO_DC_PIN = self.gpio_mode(dc,self.OUTPUT)
        self.GPIO_BL_PIN = self.gpio_pwm(bl)
        self.bl_DutyCycle(0)

        # Initialize inputs with automatic active state handling
        self.GPIO_KEY_UP_PIN     = self.gpio_mode(KEY_UP_PIN,self.INPUT,True)
        self.GPIO_KEY_DOWN_PIN   = self.gpio_mode(KEY_DOWN_PIN,self.INPUT,True)
        self.GPIO_KEY_LEFT_PIN   = self.gpio_mode(KEY_LEFT_PIN,self.INPUT,True)
        self.GPIO_KEY_RIGHT_PIN  = self.gpio_mode(KEY_RIGHT_PIN,self.INPUT,True)
        self.GPIO_KEY_PRESS_PIN  = self.gpio_mode(KEY_PRESS_PIN,self.INPUT,True)

        self.GPIO_KEY1_PIN       = self.gpio_mode(KEY1_PIN,self.INPUT,True)
        self.GPIO_KEY2_PIN       = self.gpio_mode(KEY2_PIN,self.INPUT,True)
        self.GPIO_KEY3_PIN       = self.gpio_mode(KEY3_PIN,self.INPUT,True)
        self.GPIO_KEY4_PIN       = self.gpio_mode(KEY4_PIN,self.INPUT,True) 

        self.SPI = spi
        if self.SPI!=None :
            self.SPI.max_speed_hz = spi_freq
            self.SPI.mode = 0b00

    def gpio_mode(self, Pin, Mode, pull_up = None, active_state = True, bounce_time = 0.08):
        if Mode:
            return DigitalOutputDevice(Pin, active_high = True, initial_value = False)
        else:
            if pull_up:
                # Pass bounce_time here to filter out mechanical chatter
                return DigitalInputDevice(Pin, pull_up=True, bounce_time=bounce_time)
            else:
                return DigitalInputDevice(Pin, pull_up=False, active_state=active_state, bounce_time=bounce_time)
   
    def digital_write(self, Pin, value):
        if value:
            Pin.on()
        else:
            Pin.off()

    def digital_read(self, Pin):
        return Pin.value

    def delay_ms(self, delaytime):
        time.sleep(delaytime / 1000.0)

    def gpio_pwm(self,Pin):
        return PWMOutputDevice(Pin,frequency = self.BL_freq)

    def spi_writebyte(self, data):
        if self.SPI!=None :
            self.SPI.writebytes(data)

    def bl_DutyCycle(self, duty):
        self.GPIO_BL_PIN.value = duty / 100
        
    def bl_Frequency(self,freq):
        self.GPIO_BL_PIN.frequency = freq
           
    def module_init(self):
        if self.SPI!=None :
            self.SPI.max_speed_hz = self.SPEED        
            self.SPI.mode = 0b00     
        return 0
 
    def module_exit(self):
        if self.SPI!=None :
            self.SPI.close()
        self.digital_write(self.GPIO_RST_PIN, 1)
        self.digital_write(self.GPIO_DC_PIN, 0)   
        self.GPIO_BL_PIN.close()
        time.sleep(0.001)
