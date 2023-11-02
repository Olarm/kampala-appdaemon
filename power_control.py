import datetime
import requests
import time
import numpy as np
from scipy.stats import percentileofscore

import hassapi as hass


class PowerControl(hass.Hass):
    def initialize(self):
        self.get_prices()
        runtime = datetime.time(0,0,0) # every hour
        self.check_price()
        self.hourly = self.run_hourly(self.check_price, runtime)


    def check_price(self, *args, **kwargs):
        percentiles = [percentileofscore(self.prices, hour, kind='strict') for hour in self.prices]
        avg = np.mean(self.prices)
        now = datetime.datetime.now().hour
        if percentiles[now] >= 90 and self.prices[now] >= avg + 0.2:
            self.turn_off_stuff()
        else:
            self.turn_on_stuff()


    def turn_off_stuff(self):
        self.log("power expensive")
        self.call_service("input_boolean/turn_on", entity_id="input_boolean.power_expensive")
        self.call_service("switch/turn_off", entity_id="switch.shellyplug_water_heater")
        self.call_service("climate/turn_off", entity_id="climate.termostat_bad")


    def turn_on_stuff(self):
        self.log("power cheap")
        self.call_service("input_boolean/turn_off", entity_id="input_boolean.power_expensive")
        self.call_service("climate/turn_on", entity_id="climate.termostat_bad")


    def get_prices(self):
        now = datetime.datetime.now()
        year = now.year
        month = now.month
        day = now.day
        r = requests.get(
            f"https://www.hvakosterstrommen.no/api/v1/prices/{year}/{str(month).zfill(2)}-{str(day).zfill(2)}_NO5.json"
        )
        if not r.ok:
            self.log(f"Error getting power prices: {r.status_code} {r.reason}")
            self.log("Turning stuff on")
            self.turn_on_stuff()
            time.sleep(10)
            self.restart_app("power_control")

        data = r.json()
        arr = [hour["NOK_per_kWh"] for hour in data]
        arr = np.array(arr)
        # moms
        arr *= 1.25
        # energiledd
        if month in range(1,4):
            arr[0:6] += 0.3209
            arr[6:22] += 0.4209
            arr[22:24] += 0.3209
        if month in range(4,13):
            arr[0:6] += 0.4044
            arr[6:22] += 0.5044
            arr[22:24] += 0.4044

        self.prices = arr

