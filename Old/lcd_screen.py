#!/usr/bin/env python3
import spidev
import png
import RPi.GPIO as GPIO
from copy import deepcopy
import time



class ST7920:
    CS_PIN = 7
    
    LCD_CLS         = 0x01
    LCD_HOME        = 0x02
    LCD_ADDRINC     = 0x06
    LCD_DISPLAYON   = 0x0C
    LCD_DISPLAYOFF  = 0x08
    LCD_CURSORON    = 0x0E
    LCD_CURSORBLINK = 0x0F
    LCD_BASIC       = 0x30
    LCD_EXTEND      = 0x34
    LCD_GFXMODE     = 0x36
    LCD_TXTMODE     = 0x34
    LCD_STANDBY     = 0x01
    LCD_SCROLL      = 0x03
    LCD_SCROLLADDR  = 0x40
    LCD_ADDR        = 0x80
    LCD_LINE0       = 0x80
    LCD_LINE1       = 0x90
    
    SPI_SPEED       = 1000000
    
    ALIGN_LEFT  =  0
    ALIGN_RIGHT = -1
    ALIGN_RIGHT = -2
    
    def __init__(self):
        print("LCD_INIT...")
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.CS_PIN, GPIO.OUT)
        GPIO.output(self.CS_PIN, 0)
        self.spi = spidev.SpiDev()
        self.spi.open(1,1)
        self.spi.cshigh = True # use inverted CS
        self.spi.max_speed_hz = self.SPI_SPEED # set SPI clock to 1.8MHz, up from 125kHz
        
        GPIO.output(self.CS_PIN, 1)
        self.send(self.LCD_BASIC) # basic instruction set
        self.send(self.LCD_BASIC) # repeated
        self.send(self.LCD_DISPLAYON) # display on
        
        self.send(self.LCD_CLS)
        time.sleep(2)
        self.send(self.LCD_ADDRINC) #enable graphics display
        self.send(self.LCD_HOME) #enable RE mode
        
        #self.setGfxMode(False)
        GPIO.output(self.CS_PIN, 0)
        
                
    # true = graphics mode
    # flase = text mode
    def setGfxMode(self, mode):
        if mode:
            print("set gfx mode")
            self.send(self.LCD_EXTEND)
            self.send(self.LCD_GFXMODE)
        else:
            print("set txt mode")
            self.send(self.LCD_EXTEND)
            self.send(self.LCD_TXTMODE)
             
    def send(self, cmds):
        if type(cmds) is int: # if a single arg, convert to a list
            cmds = [cmds]
        b1 = 0XF8
        bytes = []
        for cmd in cmds:
            bytes.append(cmd & 0xF0)
            bytes.append((cmd & 0x0F)<<4)
        
        output = self.spi.xfer2([b1] + bytes)
        return output
    
    def data(self, cmds):
        if type(cmds) is int: # if a single arg, convert to a list
            cmds = [cmds]
        b1 = 0xFA
        bytes = []
        for cmd in cmds:
            bytes.append(cmd & 0xF0)
            bytes.append((cmd & 0x0F)<<4)
        output = self.spi.xfer2([b1] + bytes)
        return output
    
    def text_string(self, text, pos):
        GPIO.output(self.CS_PIN, 1)
        self.send(self.LCD_BASIC)
        self.send(pos)
        print("Print: " + text)
        for element in range(0,18):
            if element < len(text):
                self.data(ord(text[element])) #0x41
            else:
                self.data(ord(" "))
        GPIO.output(self.CS_PIN, 0)
        #self.send(self.LCD_STANDBY)
        
