# CoffeeCounter

Pi Broadcasts it's own wifi from where vnc and a webgui are avialable: \
ssid: CoffeeCounterWiFi \
pw: CoffeeCounter_msrl

The Wifi was setup according to [this](https://www.raspberrypi.com/tutorials/host-a-hotel-wifi-hotspot/) official tutorial (also as pdf in folder). \
Use TigerVNC or something to connect to the rpi (10.42.0.1) when connected to the pi's wifi.\
The RFID reader uses the [pi-rf522](https://github.com/ondryaso/pi-rc522) package (Github link). You can just run the requirements.txt
and the requirements-pi.txt to download the required libraries. The "-pi.txt" file are all dependencies which only are installable on the RPi.\

The balances themselves are stored in a simple csv file in the Data folder. Adittionally, there is backup logic, were you can specify where the
backups should be stored. It will backup each hour (?) and keep the 5 newest backups. The fields stored are TagId, Name, Balance
LastUse, Price and Counter \

The webgui is reachable on (.............) and shows the log. Adittionally, you can use the upload to upload a csv file with the formatting of
Templates/BalanceChange.csv to adjust balances, associate a Name to a Tag id and set a custom price for a specifc TagId. The column names are: TagId, Name, Balance, Change , Price\
The webgui communicates to the main script through the state.json file.\

A new user can just scan their Legi and a new entry in the Balance.csv file is created. The name is then associated/set/updated once the admin pushes
the next balance update.\

The Pi only has read access to this repo through a deploy key. Additionally, .csv files are ignored by git, hence the .csv.template ending for files in the Template folder.

Logging should be relatively complete and logs both to console and CoffeeCounter.log\

For completeness sake, the old code is still accessible in the Old folder.\

TODO: ADD final RPI pin connections.