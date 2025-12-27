#!/usr/bin/env python3
import spidev
import RPi.GPIO as GPIO
import time

class MCP3201:
    CS_PIN = 11
     
    SPI_SPEED       = 100000

    continuous_read = False
    continous_uptime=0
    device_status = ""
    
    def __init__(self):
        print("CURRENT_INIT...")
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.CS_PIN, GPIO.OUT)
        GPIO.output(self.CS_PIN, 1)
        self.spi = spidev.SpiDev()
        self.spi.open(0,1)
        self.spi.cshigh = True # use inverted CS
        self.spi.max_speed_hz = self.SPI_SPEED # set SPI clock to 1.8MHz, up from 125kHz
               
                            
    def readADC_MSB(self):
        GPIO.output(self.CS_PIN, 0)
        bytes_received = self.spi.xfer2([0x00, 0x00])
        GPIO.output(self.CS_PIN, 1)
        
        MSB_1 = bytes_received[1]
        MSB_1 = MSB_1 >> 1
        
        MSB_0 = bytes_received[0] & 0b00011111
        MSB_0 = MSB_0 << 7
        
        return MSB_0 + MSB_1
    
                 
    def readADC_LSB(self):
        GPIO.output(self.CS_PIN, 0)
        bytes_received = self.spi.xfer2([0x00, 0x00, 0x00, 0x00])
        GPIO.output(self.CS_PIN, 1)
        
        LSB_0 = bytes_received[1] & 0b00000011
        LSB_0 = bin(LSB_0)[2:].zfill(2)
        
        LSB_1 = bytes_received[2] 
        LSB_1 = bin(LSB_1)[2:].zfill(8)
        
        LSB_2 = bytes_received[3] 
        LSB_2 = bin(LSB_2)[2:].zfill(8)
        LSB_2 = LSB_2[0:2]
        
        LSB = LSB_0 + LSB_1 + LSB_2
        LSB = LSB[::-1]
        return int(LSB, base=2)

    def continuous_uptime(self, threshold, start_time, keep_previous = False):
        self.continuous_read = True
        if not keep_previous:
            self.continuous_uptime = 0
        # start_time = time.time()
        while self.continuous_read:
            I_MSB = self.readADC_MSB()
            if I_MSB >= threshold:
                self.continuous_uptime += (time.time() - start_time)
                self.status = "Running"
            else:
                self.status = "Standby"

        self.continuous_read = False
