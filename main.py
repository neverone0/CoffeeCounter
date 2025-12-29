#!/usr/bin/env python3
# Module Imports
import sys
import RPi.GPIO as GPIO
from rpi_lcd import LCD
from pirc522 import RFID
from current_sensor import MCP3201
import time
import pandas as pd
import threading
import shutil
import os
import logging
import cowsay
import json
from logging.handlers import RotatingFileHandler
from random import randrange

class MonotonicFilter(logging.Filter):
    def filter(self, record):
        record.monotonic = f"{time.monotonic():.6f}"
        return True

LOGGER = logging.getLogger(__name__)

def setup_logging():
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False
    file_handler = RotatingFileHandler(STATE["logfile"], maxBytes=1_000_000, backupCount=5)
    file_handler.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    formatter = logging.Formatter("%(asctime)s - %(monotonic)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)
    LOGGER.addHandler(file_handler)
    LOGGER.addHandler(console_handler)

COFFEE_PRICE_PER_SEC = 0.1
PRICE_PER_DOSE = 0.5
LOW_BALANCE_THRESHOLD = 2.0
MIN_BALANCE = -2.0

CS_CURRENT_PIN = 7
RELAY_PIN = 12

MSB_THRESHOLD = 100
ON_TIME = 45
SINGLE_DOSE_TIME = 7.5

GPIO.setmode(GPIO.BOARD)
GPIO.setup(CS_CURRENT_PIN, GPIO.OUT)
GPIO.output(CS_CURRENT_PIN, GPIO.HIGH)

GPIO.setup(RELAY_PIN, GPIO.OUT)
GPIO.output(RELAY_PIN, GPIO.LOW)

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

BALANCESHEET_PATH = "./Data/Balances.csv"
TEMP_BALANCESHEET_PATH = "./Data/Balances_temp.csv"
BACKUP_LOCATION = "./Data"
BACKUP_TIMER = 7200 # Once two hours

def backup_csv():
    LOGGER.warning("Backing up balance sheet...")
    backup_path = f"{BACKUP_LOCATION}/Backup/Balances_backup_{time.time()}.csv"
    try:
        shutil.copy(BALANCESHEET_PATH, backup_path)
    except Exception as e:
        LOGGER.error(f"CSV backup failed: {e}")
        if STATE["last_backup"] is None:
            LOGGER.error(f"No previous Backups")
        else:
            LOGGER.error(f"Last successful backup time: {STATE['last_backup']}")
    else:
        LOGGER.info(f"Backup CSV saved to {backup_path}")
        STATE["last_backup"] = time.time()
        save_state(STATE)

def update_balances(path_to_csv):
    """ Update balancesheet using another csv file. By default unknown IDs will generate a new entry
    TODO: Maybe ask before creating new identiies
    """
    LOGGER.info("Updating balance sheet...")
    balanceDF = pd.read_csv(BALANCESHEET_PATH)
    balance_changes_df = pd.read_csv(path_to_csv)
    unknown_entries = []

    for index, row in balance_changes_df.iterrows():
        tag_id = row["TagId"]
        if tag_id in balanceDF.loc[:,"TagId"]:
            # update balances
            curr_balance =  balanceDF.loc[row["TagId"], "Balance"]
            new_balance = curr_balance + row["BalanceChange"]
            balanceDF.loc[row["TagId"], "Balance"] = new_balance
            LOGGER.warning(f"Update {tag_id} Balance: {curr_balance} -> {new_balance} ({row['BalanceChange']})")
            # Set Name if exists in update file
            if not pd.isnull(row["Name"]):
                current_name = balanceDF.loc[row["TagId"], "Name"]
                balanceDF.loc[row["TagId"], "Name"] = row["Name"]
                LOGGER.warning(f"Update {tag_id} Name: {current_name} -> {row['Name']}")
            # Set special price if exists in update file
            if not pd.isnull(row["Price"]):
                current_price = balanceDF.loc[row["TagId"], "Price"]
                balanceDF.loc[row["TagId"], "Price"] = row["Price"]
                LOGGER.warning(f"Update {tag_id} Price: {current_price} -> {row['Price']}")
        else:
            unknown_entries.append(row.todict)
            LOGGER.error(f"Tag id {tag_id} not found (Name: {row['Name']}, BalanceChange: {row['BalanceChange']}), Price {row['Price']}")

    shutil.copyfile(BALANCESHEET_PATH, TEMP_BALANCESHEET_PATH)
    try:
        balanceDF.to_csv(BALANCESHEET_PATH, sep=",", header=True, index=False)
    except Exception as e:
        LOGGER.error(f"Error occured during balance update. Please try again. \n {e}")
    finally:
        LOGGER.info("Delete temporary balancesheet")
        if os.path.isfile(TEMP_BALANCESHEET_PATH):
            os.remove(TEMP_BALANCESHEET_PATH)

    LOGGER.info("Finished updating balance sheet.")

def get_new_user_dict(tag_uid):
    return {"TagId": tag_uid, "Name": f"NewUser{randrange(99)}", "Balance": 0.0, "LastUse": None, "Price": None, "Counter": 0}

def main():
    setup_logging()

    reader = RFID(pin_irq = None)
    # Board Pins: SDA-24 , SCK-23, MOSI-19, MISO-21, IRQ-None, GND-6/9/20/25, RST-22, 3.3V-1/17
    lcd = LCD()
    cur_sensor = MCP3201()
    lastUser = ""

    LOGGER.warning(cowsay.get_output_string('cow', "Starting Coffee Counter"))

    backup_csv()

    LOGGER.info("loading balancesheet to memory")
    balanceDF  = pd.read_csv(BALANCESHEET_PATH, sep=",", header=0)

    while (1):
        STATE = load_state()
        if STATE["mode"] == "maintenance":
            STATE["mode_ack"]= STATE["mode"]
            save_state(STATE)
            lcd.text("Maintenance mode active", 1)
            lcd.text("Coffee currently unavailabe", 2)
            # Suspend while in maintenance mode
            while STATE["mode"] == "maintenance":
                STATE = load_state()
                pass
            balanceDF = pd.read_csv(BALANCESHEET_PATH, sep=",", header=0)
            STATE["mode_ack"]= STATE["mode"]

        if ((STATE["last_backup"] is None) or ((time.time() - STATE["last_backup"]) > BACKUP_TIMER)):
            backup_csv()

        try:
            lcd.text(f"Scan Tag! ({price}CHF/Dose)  ", 1)
            lcd.text("                  ", 2)
            lcd.text("Blame: " + lastUser, 2)
            uid = reader.get_uid()
            if uid is None:
                raise Exception("No tag detected")

            time.sleep(0.1)

            if uid not in balanceDF.loc[:,"TagId"]:
                balanceDF.append(get_new_user_dict(uid), ignore_index=True)

            username = balanceDF.loc[uid, "Name"]
            balance = balanceDF.loc[uid, "Balance"]
            price =  PRICE_PER_DOSE if pd.isnull(balanceDF.loc[uid, "Price"]) else balanceDF.loc[uid, "Price"]
            lcd.text(f"Hello {username}", 1)
            LOGGER.info(f"Tag detected: {uid}, Balance: {balance}, Price: {price}")

            time.sleep(1)

            if balance<MIN_BALANCE:
                lcd.text("!! Balance too low, please top up before use !!", 2)
                LOGGER.error(f"Balance too low: {balance}")
                raise Exception("Balance too low")
            elif balance < LOW_BALANCE_THRESHOLD:
                lcd.text("!! Low Balance, please top up soon !!", 1)
                LOGGER.warning(f"Low Balance warning: {balance}")

            lcd.text(f"Balance: {balance:.2f}CHF", 2)
            time.sleep(0.5)


            lcd.text("Activating Relay", 1)
            LOGGER.info(f"Activating Relay")

            GPIO.output(RELAY_PIN, 1)

            start_time = time.time()
            end_time = start_time + ON_TIME

            nbr_coffees = 0

            LOGGER.info(f"Starting current sensor thread")

            cur_sensor_thread = threading.Thread(target=cur_sensor.continuous_uptime, args=(cur_sensor,MSB_THRESHOLD,start_time))
            cur_sensor_thread.start()

            while  time.time() < end_time:
                rem_time = end_time - time.time()
                lcd.text(f"#Coffees: {nbr_coffees}, Time left: {rem_time:.0f}s", 2)
                uptime = cur_sensor.continuous_uptime
                est_nbr_doses = (uptime%SINGLE_DOSE_TIME)+1
                status = cur_sensor.status
                lcd.text(f"{status} , Est. # Doses: {est_nbr_doses}", 1)

            lcd.text("Deactivating Relay", 1)
            lcd.text("", 1)

            LOGGER.info(f"Deactivating Relay, waiting for current sensor to join")

            cur_sensor.continuous_read = False
            cur_sensor_thread.join()
            GPIO.output(RELAY_PIN, 0)

            LOGGER.info(f"Current sensor thread joined, Relay deactivated")

            total_uptime = cur_sensor.continuous_uptime
            nbr_doses = (total_uptime%SINGLE_DOSE_TIME)+1
            total_cost = nbr_doses * price


            # update df and write to balance sheet
            new_balance = round(balance-total_cost , 2)
            balanceDF.loc[uid, "Balance"] = new_balance
            balanceDF.loc[uid, "LastUse"] = time.time()
            balanceDF.loc[uid, "Counter"] = balanceDF.loc[uid, "Counter"] + 1

            LOGGER.info(f"Summary: Total uptime: {total_uptime:.0f}, Nbr. of Doses: {nbr_doses}, Total cost: {total_cost:.2f}CHF, New Balance: {new_balance:.2f}CHF")
            LOGGER.info(f"Trying to update balance sheet, creating temporary balancesheet at {TEMP_BALANCESHEET_PATH}")

            shutil.copyfile(BALANCESHEET_PATH, TEMP_BALANCESHEET_PATH)
            try:
                balanceDF.to_csv(BALANCESHEET_PATH, sep=",", header=True, index=False)
            except Exception as e:
                lcd.text(f"!! Error occured during balance update !!", 1)
                lcd.text("!! Please note your consumption and contact admin !!", 1)
                LOGGER.error(f"Error occured during balance update. Manual adjustment needed for {username}({uid}) (see above): \n{e}")
                time.sleep(2)
            finally:
                LOGGER.info("Delete temporary balancesheet")
                if os.path.isfile(TEMP_BALANCESHEET_PATH):
                    os.remove(TEMP_BALANCESHEET_PATH)

            lcd.text(f"Total: {nbr_doses} doses, {total_cost:.2f}CHF", 1)
            lcd.text(f"New Balance: {new_balance:.2f} CHF", 2)
            time.sleep(2)

            lcd.text("Than you for choosing MSRL Coffee Counter!", 1)
            lcd.text("Enjoy your break!", 2)

            LOGGER.info(f"Process finished for {username}({uid})")

            time.sleep(2)

        except KeyboardInterrupt:
            break
        except Exception as e:
            time.sleep(1)


    LOGGER.warning(cowsay.get_output_string('cow', 'Exiting Program, calling GPIO cleanup'))
    GPIO.cleanup()

if __name__ == "__main__":
    main()

