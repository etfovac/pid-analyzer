#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import numpy as np
import matplotlib.pyplot as plt
from scipy import fftpack
from influxdb import InfluxDBClient


# connect to influxdb DB
client = InfluxDBClient(host="localhost", port=8086)
client.switch_database("mydb")

# request for select last 3 records of "field1" in "test" measurement (mean value by 10s steps)
req = "SELECT mean(\"field1\") AS f1 FROM \"test\" GROUP BY time(10s) fill(null) ORDER BY time DESC LIMIT 400"

# format data and check all data is available
l_points = []
for point in client.query(req).get_points():
    if point['f1'] is None:
        print("data unavailable, skip fft", file=sys.stderr)
        exit(1)
    l_points.append(point['f1'])

# number of samples
Ns = len(l_points)

# second between 2 samples
Ts = 10  # 10 s

# N samples, every sample is time value (in s)
# 0 -> t_max with Ns items
t_max = Ts * Ns
t_samples = np.linspace(0.0, t_max, Ns)

# convert list to numpy array
y_samples = np.asarray(l_points)

# build signal
nb = len(y_samples)
x = np.linspace(0.0, (nb - 1) * Ts, nb)

# compute fft
yf = fftpack.fft(y_samples)
xf = np.linspace(0.0, 1.0 / (2.0 * Ts), nb // 2)
ya = 2.0 / nb * np.abs(yf[:nb // 2])

# normalize ya to % of signal
ya = ya * 100.0 / ya.sum()

# plot 1 data
plt.subplot(211)
plt.plot(x, y_samples)
plt.ylabel("sig. value vs time (s)")
plt.grid()

# plot 2 spectrum
plt.subplot(212)
plt.plot(xf, ya)
plt.ylabel("sig. level (%) vs freq. (Hz)")
plt.show()
