import os
import time
import csv
import calendar
from datetime import datetime
from debug_cryptocompare import fetch_prices, print_and_save

def loop_fetch(interval=240): # interval = æ¯ 240 ç§’ (4 åˆ†é˜)
    while True:
        try:
            data = fetch_prices()
            print_and_save(data)
        except Exception as e:
            print("Error:", e)
        time.sleep(interval)

if __name__== "__main__":
    loop_fetch()

