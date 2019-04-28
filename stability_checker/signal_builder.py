#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import sys
import time
import traceback
from influxdb import InfluxDBClient

# connect to influxdb DB
client = InfluxDBClient(host="localhost", port=8086)
client.switch_database("mydb")

while True:
    try:
        # update metrics
        sin_values = 400
        sin_values += math.sin(2 * math.pi * 1/100 * time.time()) * 100
        sin_values += math.sin(2 * math.pi * 1/300 * time.time()) * 100
        sin_values = round(sin_values)
        # write to influx db
        l_metrics = [
            {
                "measurement": "test",
                "fields": {
                    "field1": sin_values,
                },
            },
        ]
        client.write_points(points=l_metrics)
        # wait for next update
        time.sleep(1.0)
    except KeyboardInterrupt:
        break
    except:
        # log except to stderr
        traceback.print_exc(file=sys.stderr)
        # wait before next try
        time.sleep(2.0)
