#!/usr/bin/env python3
# Module Imports
import mariadb
import time
print("try to connect to php database...")
conn = mariadb.connect(
          user="u518823022_cehmke", #"cehmke",
          password="CCMicrorobot2024!",#"CCMicrorobot2021", 
          host="sql703.main-hosting.eu",#"mysql1.ethz.ch",
          database="u518823022_cehmke")#cehmke")
print("Connected!")

    