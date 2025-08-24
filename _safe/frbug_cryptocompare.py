import os
import time
import csv
import calendar
from datetime import datetime
from debug_cryptocompare import fetch_prices, print_and_save

def loop_fetch(interval=240): # interval = 每 240 秒 (4 分鐘)
    while True:
        try:
            data = fetch_prices()
            print_and_save(data)
        except Exception as e:
            print("Error:", e)
        time.sleep(interval)

if __name__== "__main__":
    loop_fetch()
