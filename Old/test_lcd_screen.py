from lcd_screen import ST7920
import RPi.GPIO as GPIO

GPIO.setwarnings(False)
GPIO.cleanup()

CS_PIN = 7
RELAY_PIN = 12
MSB_THRESHOLD = 100
MSB_THRESHOLD_2GRINDER = 200
ON_TIME = 10
ON_TIME_2 = 5
SMALL_COFFEE_TIME = 7.5

GPIO.setmode(GPIO.BOARD)
GPIO.setup(CS_PIN, GPIO.OUT)
GPIO.output(CS_PIN, 1)

GPIO.setup(RELAY_PIN, GPIO.OUT)
GPIO.output(RELAY_PIN, 0)
lcd_screen = ST7920()

print("Starting")
lcd_screen.text_string("Wait for tag...!  ",ST7920.LCD_LINE0)


    