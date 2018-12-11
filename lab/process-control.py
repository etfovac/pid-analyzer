#!/usr/bin/python

import json
from Queue import Queue
import sys
import time
import traceback
from threading import Thread, Lock
from pyModbusTCP.client import ModbusClient
from pyModbusTCP import utils
import serial


# some class
class ArduinoCommandSerial(serial.Serial):
    def send_cmd(self, cmd, echo=False):
        # flush rx buffer
        self.read(self.inWaiting())
        # send command
        self.write(cmd + "\r\n")
        if echo:
            print("> %s" % cmd)
        # receive command return
        ret = self.readline().strip()
        if echo:
            print("< %s" % ret)
        return ret


class FloatModbusClient(ModbusClient):
    def read_float(self, address, number=1):
        reg_l = self.read_holding_registers(address, number * 2)
        if reg_l:
            return [utils.decode_ieee(f) for f in utils.word_list_to_long(reg_l)]
        else:
            return None

    def write_float(self, address, floats_list):
        b32_l = [utils.encode_ieee(f) for f in floats_list]
        b16_l = utils.long_list_to_word(b32_l)
        return self.write_multiple_registers(address, b16_l)


class Tags:
    lock = Lock()
    cmd_q = Queue()
    PV = 0.0
    OUT = 0.0
    SP = 0.0


# some functions
def modbus_thread():
    # init modbus client for local server
    c = FloatModbusClient(host="localhost", auto_open=True)
    # update loop
    while True:
        # read commands (auto, manu...)
        # auto
        if c.read_coils(0)[0]:
            c.write_single_coil(0, False)
            Tags.cmd_q.put("auto")
        # manu
        if c.read_coils(1)[0]:
            c.write_single_coil(1, False)
            Tags.cmd_q.put("man")
        # set output
        out_value = c.read_float(10)[0]
        if out_value:
            c.write_float(10, [0.0])
            Tags.cmd_q.put("out %.2f" % out_value)
        # write process monitoring value
        with Tags.lock:
            write_l = [Tags.PV, Tags.OUT, Tags.SP]
        c.write_float(0, write_l)
        # wait next loop
        time.sleep(0.5)


# main program
if __name__ == "__main__":
    # start polling thread
    tp = Thread(target=modbus_thread)
    # set daemon: polling thread will exit if main thread exit
    tp.daemon = True
    tp.start()

    # init serial port
    s = ArduinoCommandSerial("/dev/ttyACM0", baudrate=9600, timeout=2.0)
    #s = ArduinoCommandSerial("/dev/ttyATH0", baudrate=9600, timeout=2.0)

    # init PID board
    s.send_cmd("auto", echo=True)
    s.send_cmd("sp 12.0", echo=True)
    s.send_cmd("kp 4.1", echo=True)
    s.send_cmd("ki 2.5", echo=True)
    s.send_cmd("kd 0.0", echo=True)

    # main loop
    while True:
        # process pending command
        while not Tags.cmd_q.empty():
            cmd = Tags.cmd_q.get()
            s.send_cmd(cmd, echo=True)
        # read process values
        try:
            json_msg = s.send_cmd("json")
            d = json.loads(json_msg)
            with Tags.lock:
                Tags.PV = float(d["pv"])
                Tags.OUT = float(d["out"])
                Tags.SP = float(d["sp"])
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
        # wait next loop
        time.sleep(0.5)
