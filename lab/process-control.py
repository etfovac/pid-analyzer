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
    AUTO = False
    MAN = False
    PV = 0.0
    OUT = 0.0
    SP = 0.0
    KP = 0.0
    KI = 0.0
    KD = 0.0


# some functions
def modbus_thread():
    # init modbus client for local server
    c = FloatModbusClient(host="localhost", auto_open=True)
    # update loop
    while True:
        # read commands (auto, manu...)
        # auto
        if c.read_coils(100)[0]:
            c.write_single_coil(100, False)
            Tags.cmd_q.put("auto")
        # manu
        if c.read_coils(101)[0]:
            c.write_single_coil(101, False)
            Tags.cmd_q.put("man")
        # save
        if c.read_coils(110)[0]:
            c.write_single_coil(110, False)
            Tags.cmd_q.put("save")
        # set-point update
        sp_value = c.read_float(100)[0]
        if sp_value:
            c.write_float(100, [0.0])
            Tags.cmd_q.put("sp %.2f" % sp_value)
        # output update for manual mode
        out_value = c.read_float(102)[0]
        if out_value:
            c.write_float(102, [0.0])
            Tags.cmd_q.put("out %.2f" % out_value)
        # set kp params
        kp_value = c.read_float(104)[0]
        if kp_value:
            c.write_float(104, [0.0])
            Tags.cmd_q.put("kp %.2f" % kp_value)
        # set ki params
        ki_value = c.read_float(106)[0]
        if ki_value:
            c.write_float(106, [0.0])
            Tags.cmd_q.put("ki %.2f" % ki_value)
        # set kd params
        kd_value = c.read_float(108)[0]
        if kd_value:
            c.write_float(108, [0.0])
            Tags.cmd_q.put("kd %.2f" % kd_value)
        # refresh PID status
        with Tags.lock:
            coils_l = [Tags.AUTO, Tags.MAN]
        c.write_multiple_coils(0, coils_l)
        # refresh PID values
        with Tags.lock:
            write_l = [Tags.PV, Tags.SP, Tags.OUT, Tags.KP, Tags.KI, Tags.KD]
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
    s = ArduinoCommandSerial("/dev/ttyATH0", baudrate=9600, timeout=2.0)

    # init PID board
    s.send_cmd("auto", echo=True)

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
                Tags.AUTO = float(d["auto"])
                Tags.MAN = float(d["man"])
                Tags.PV = float(d["pv"])
                Tags.OUT = float(d["out"])
                Tags.SP = float(d["sp"])
                Tags.KP = float(d["kp"])
                Tags.KI = float(d["ki"])
                Tags.KD = float(d["kd"])
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
        # wait next loop
        time.sleep(0.5)
