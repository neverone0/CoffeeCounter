from mfrc522 import SimpleMFRC522
reader = SimpleMFRC522()

try:
    while True:
        id = reader.read_id()
        print("UID:", id)
finally:
    GPIO.cleanup()
