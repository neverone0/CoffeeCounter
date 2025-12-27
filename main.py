#!/usr/bin/env python3
# Module Imports
import sys
import RPi.GPIO as GPIO
from lcd_screen import ST7920
from mfrc522 import SimpleMFRC522
from current_sensor import MCP3201
import time

print("HERE!")
COFFEE_PRICE_PER_SEC = 0.1

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

reader = SimpleMFRC522()
lcd_screen = ST7920()
cur_sensor = MCP3201()
print("Start system")
lastUser = ""
while (1):
    try:
        print("Wait for tag...!")
        lcd_screen.text_string("Wait for tag...!  ", ST7920.LCD_LINE0)
        lcd_screen.text_string("                  ", ST7920.LCD_LINE1)
        lcd_screen.text_string("Blame: " + lastUser, ST7920.LCD_LINE1)
        rfid, text = reader.read();
        print(rfid)
        time.sleep(0.1)


        for id, name, balance, comment in cur:
            print(f"Name: {name}")
            lcd_screen.text_string("Hello " + name, ST7920.LCD_LINE0)
            balance_msg = "Balance: %.2fCHF" % balance
            lcd_screen.text_string(balance_msg, ST7920.LCD_LINE1)
            print(balance_msg)
            time.sleep(1.5)
            lcd_screen.text_string(balance_msg, ST7920.LCD_LINE1)
            if balance < -2.0:
                time.sleep(2)
                lcd_screen.text_string("Low balance!      ", ST7920.LCD_LINE0)
                lcd_screen.text_string("                  ", ST7920.LCD_LINE1)
                time.sleep(1)
                break
            start_time = time.time()
            end_time = start_time + ON_TIME
            remaining_time = end_time - time.time()
            display_time = -1
            GPIO.output(RELAY_PIN, 1)
            high_current_duration = 0
            double_grinding = 1
            while remaining_time > 0:
                if (int(remaining_time) != display_time):
                    display_time = int(remaining_time)
                    display_time_msg = "Time left: %us" % display_time
                    lcd_screen.text_string(display_time_msg, ST7920.LCD_LINE1)

                    I_MSB = cur_sensor.readADC_MSB()
                    time_before_usage = time.time()
                    tmp_high_current_duration = 0
                    current_msg = "Current: %.2fA" % I_MSB
                    # print(current_msg)
                    if I_MSB >= MSB_THRESHOLD:
                        lcd_screen.text_string("Grinding 1x...       ", ST7920.LCD_LINE1)
                        lastUser = name

                    while (I_MSB >= MSB_THRESHOLD):
                        tmp_high_current_duration = time.time() - time_before_usage
                        I_MSB = cur_sensor.readADC_MSB()
                        if I_MSB >= MSB_THRESHOLD_2GRINDER and double_grinding <= 2:
                            double_grinding = 2
                            lcd_screen.text_string("Grinding 2x...       ", ST7920.LCD_LINE1)

                        current_msg = "Current: %.2fA" % I_MSB
                        # print(current_msg)
                        end_time = time.time() + ON_TIME_2

                    high_current_duration = high_current_duration + tmp_high_current_duration
                # time.sleep(0.01)
                remaining_time = end_time - time.time()
            GPIO.output(RELAY_PIN, 0)
            lcd_screen.text_string("Grinding time: " + str(int(high_current_duration)), ST7920.LCD_LINE0)
            coffee_price = 0

            if high_current_duration > 0:
                if high_current_duration < SMALL_COFFEE_TIME:
                    coffee_price = 0.5 * double_grinding
                if high_current_duration >= SMALL_COFFEE_TIME:
                    coffee_price = 1.0 * double_grinding
            # coffee_price = int(high_current_duration)*COFFEE_PRICE_PER_SEC
            coffee_price_msg = "Price: %0.2fCHF" % coffee_price
            lcd_screen.text_string(coffee_price_msg, ST7920.LCD_LINE1)
            time.sleep(2)
            balance = balance - coffee_price
            coffee_price_msg = "Balance: %0.2fCHF" % balance
            lcd_screen.text_string(coffee_price_msg, ST7920.LCD_LINE0)
            lcd_screen.text_string("Enjoy!", ST7920.LCD_LINE1)
            time.sleep(2)
            conn.close()
            conn = mariadb.connect(
                user="u518823022_cehmke",  # "cehmke",
                password="CCMicrorobot2021!",  # "CCMicrorobot2024",
                host="sql703.main-hosting.eu",  # "mysql1.ethz.ch",
                database="u518823022_cehmke")  # cehmke")
            print("Connected!")
            cur = conn.cursor()

            if coffee_price > 0:
                print("Update db...")
                update_text = "UPDATE overview SET balance = %.2f WHERE rfid=?" % balance
                cur.execute(update_text, (rfid,))

            cur.execute("SELECT id,name,balance,comment FROM overview WHERE rfid=?", (rfid,))

            for id, name, balance, comment in cur:
                time.sleep(2)
                coffee_price_msg = "Balance2: %0.2fCHF" % balance
                lcd_screen.text_string(coffee_price_msg, ST7920.LCD_LINE0)
                print(coffee_price_msg)
                break
            conn.close()

            break

        time.sleep(2)
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Platform: {e}")
        lcd_screen.text_string("ERRORDB!", ST7920.LCD_LINE0)
        lcd_screen.text_string("ERRORDB!", ST7920.LCD_LINE1)
        time.sleep(2)
    #    sys.exit(1)

