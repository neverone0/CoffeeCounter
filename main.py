#!/usr/bin/env python3
# Module Imports
import sys
import RPi.GPIO as GPIO
from lcd_screen import ST7920
from mfrc522 import SimpleMFRC522
from current_sensor import MCP3201
import time
import pandas as pd
import threading
import shutil
import os
import logging
import cowsay
from logging.handlers import RotatingFileHandler

class MonotonicFilter(logging.Filter):
    def filter(self, record):
        record.monotonic = f"{time.monotonic():.6f}"
        return True



COFFEE_PRICE_PER_SEC = 0.1
PRICE_PER_DOSE = 0.5
LOW_BALANCE_THRESHOLD = 2.0
MIN_BALANCE = -2.0

CS_PIN = 7
RELAY_PIN = 12

MSB_THRESHOLD = 100
ON_TIME = 45
SINGLE_DOSE_TIME = 7.5

GPIO.setmode(GPIO.BOARD)
GPIO.setup(CS_PIN, GPIO.OUT)
GPIO.output(CS_PIN, 1)

GPIO.setup(RELAY_PIN, GPIO.OUT)
GPIO.output(RELAY_PIN, 0)

def load_state():
    if not os.path.exists(STATE_FILE):
        raise FileNotFoundError(STATE_FILE)

    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

STATE_FILE = "./state.json"
STATE = load_state()

BALANCESHEET_PATH = "./balance_sheet.csv"
TEMP_BALANCESHEET_PATH = "./balance_sheet_temp.csv"
BACKUP_LOCATION = "."
BACKUP_TIMER = 7200 # Once two hours

def backup_csv():
    backup_path = f"{BACKUP_LOCATION}/Backup/balance_sheet_backup_{time.time()}.csv"
    try:
        shutil.copy(BALANCESHEET_PATH, backup_path)
    except Exception as e:
        logger.error(f"CSV backup failed: {e}")
        if STATE["last_backup"] is None:
            logger.error(f"No previous Backups")
        else:
            logger.error(f"Last successful backup time: {STATE["last_backup"]}")
    else:
        logger.info(f"Backup CSV saved to {backup_path}")
        STATE["last_backup"] = time.time()
        save_state(STATE)

def update_balances(path_to_csv):
    """ Update balancesheet using another csv file. By default unknown IDs will generate a new entry
    TODO: Maybe ask before creating new identiies
    """
    pass

def main():
    reader = SimpleMFRC522()
    lcd_screen = ST7920()
    cur_sensor = MCP3201()
    lastUser = ""

    logger.warn(cowsay.get_output_string('cow', "Starting Coffee Counter"))

    backup_csv()

    balanceDF  = pd.read_csv(BALANCESHEET_PATH, sep=",", header=0)

    while (1):
        if MAINTENANCE_MODE:
            # TODO: Add logic for balance top up
            pass

        if ((STATE["last_backup"] is None) or ((time.time() - STATE["last_backup"]) > BACKUP_TIMER)):
            backup_csv()
        try:
            print("Wait for tag...!")
            lcd_screen.text_string(f"Scan Tag! ({PRICE_PER_DOSE}CHF/Dose)  ", ST7920.LCD_LINE0)
            lcd_screen.text_string("                  ", ST7920.LCD_LINE1)
            lcd_screen.text_string("Blame: " + lastUser, ST7920.LCD_LINE1)
            rfid, text = reader.read()
            print(rfid)
            time.sleep(0.1)

            username = balanceDF.loc[rfid, "Name"]
            balance = balanceDF.loc[rfid, "Balance"]
            price =  PRICE_PER_DOSE if df.isnull()[rfid, "Price"] else balanceDF.loc[rfid, "Price"]
            lcd_screen.text_string(f"Hello {username}", ST7920.LCD_LINE0)
            time.sleep(1)

            if balance<MIN_BALANCE:
                lcd_screen.text_string("!! Balance too low, please top up before use !!", ST7920.LCD_LINE_1)
                raise Exception
            elif balance < LOW_BALANCE_THRESHOLD:
                lcd_screen.text_string("!! Low Balance, please top up soon !!", ST7920.LCD_LINE_0)

            lcd_screen.text_string(f"Balance: {balance:.2f}CHF", ST7920.LCD_LINE1)

            time.sleep(0.5)

            lcd_screen.text_string("Activating Relay", ST7920.LCD_LINE0)
            # display_thread = threading.Thread(target=lcd_screen.countdown, args=(time.time(), ON_TIME, ST7920.LCD_Line1))
            GPIO.output(RELAY_PIN, 1)

            start_time = time.time()
            end_time = start_time + ON_TIME

            nbr_coffees = 0

            cur_sensor_thread = threading.Thread(target=cur_sensor.continuous_uptime, args=(cur_sensor,MSB_THRESHOLD,start_time))
            cur_sensor_thread.start()

            while  time.time() < end_time:
                rem_time = end_time - time.time()
                lcd_screen.text_string(f"#Coffees: {nbr_coffees}, Time left: {rem_time:.0f}s", ST7920.LCD_LINE1)
                uptime = cur_sensor.continuous_uptime
                est_nbr_doses = (uptime%SINGLE_DOSE_TIME)+1
                status = cur_sensor.status
                lcd_screen.text_string(f"{status} , Est. # Doses: {est_nbr_doses}", ST7920.LCD_LINE0)

            lcd_screen.text_string("Deactivating Relay", ST7920.LCD_LINE0)
            lcd_screen.text_string("", ST7920.LCD_LINE0)
            cur_sensor.continuous_read = False
            cur_sensor_thread.join()
            GPIO.output(RELAY_PIN, 0)
            total_uptime = cur_sensor.continuous_uptime
            nbr_doses = (total_uptime%SINGLE_DOSE_TIME)+1
            price = nbr_doses * PRICE_PER_DOSE

            # update df and write to balance sheet
            new_balance = balance-price
            balanceDF.loc[rfid, "Balance"] = new_balance
            balanceDF.loc[rfid, "LastUse"] = time.time()
            balanceDF.loc[rfid, "Counter"] = balanceDF.loc[rfid, "Counter"] + 1
            shutil.copyfile(BALANCESHEET_PATH, TEMP_BALANCESHEET_PATH)
            try:
                balanceDF.to_csv(BALANCESHEET_PATH, sep=",", header=True, index=False)
            except:
                lcd_screen.text_string(f"!! Error occured during balance update !!", ST7920.LCD_LINE0)
                lcd_screen.text_string("!! Please note your consumption and contact admin !!", ST7920.LCD_LINE0)
                time.sleep(2)
            finally:
                if os.path.isfile(TEMP_BALANCESHEET_PATH):
                    os.remove(TEMP_BALANCESHEET_PATH)

            lcd_screen.text_string(f"Total: {nbr_doses} doses, {price:.2f}CHF", ST7920.LCD_LINE0)
            lcd_screen.text_string(f"New Balance: {new_balance:.2f} CHF", ST7920.LCD_LINE1)
            time.sleep(2)

            lcd_screen.text_string("Than you for choosing MSRL Coffee Counter!", ST7920.LCD_LINE0)
            lcd_screen.text_string("Enjoy your break!", ST7920.LCD_LINE1)

            time.sleep(2)

        except Exception as e:

            time.sleep(1)

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    file_handler = RotatingFileHandler(STATE["logfile"], maxBytes=1_000_000, backupCount=5)
    file_handler.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    formatter = logging.Formatter("%(asctime)s - %(monotonic)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    main()

