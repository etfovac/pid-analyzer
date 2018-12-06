#!/usr/bin/python

import json
import sys
import time
import traceback
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


# main program
if __name__ == "__main__":
    # init modbus client for local server
    c = FloatModbusClient(auto_open=True)

    # init serial port
    s = ArduinoCommandSerial("/dev/ttyATH0", baudrate=9600, timeout=2.0)

    # init PID board
    s.send_cmd("auto", echo=True)
    s.send_cmd("sp 12.0", echo=True)
    s.send_cmd("kp 4.1", echo=True)
    s.send_cmd("ki 2.5", echo=True)
    s.send_cmd("kd 0.0", echo=True)

    while True:
        try:
            json_msg = s.send_cmd("json", echo=True)
            d = json.loads(json_msg)
            pv = float(d["pv"])
            out = float(d["out"])
            sp = float(d["sp"])
            print("pv: %s m3/h, out: %s %%, sp: %s m3/h" % (pv, out, sp))
            c.write_float(0, [pv, out, sp])
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
        time.sleep(0.5)

    s.close()
