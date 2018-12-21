#!/usr/bin/python

import json
from Queue import Queue
import sys
import time
import traceback
from threading import Thread, Lock
from pyModbusTCP.server import ModbusServer, DataBank
from pyModbusTCP import utils
import serial


# some function
def is_nan(x):
    return x != x


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


class DB(DataBank):
    @classmethod
    def get_floats(cls, address, number=1):
        reg_l = cls.get_words(address, number * 2)
        if reg_l:
            return [utils.decode_ieee(f) for f in utils.word_list_to_long(reg_l)]
        else:
            return None

    @classmethod
    def set_floats(cls, address, floats_list):
        b32_l = [utils.encode_ieee(f) for f in floats_list]
        b16_l = utils.long_list_to_word(b32_l)
        return cls.set_words(address, b16_l)


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
def mbus_data_thread():
    # init some value at startup
    DB.set_bits(100, [False] * 20)
    DB.set_floats(100, [float("nan")] * 20)
    # update loop
    while True:
        # read commands (auto, manu...)
        # auto
        if DB.get_bits(100)[0]:
            DB.set_bits(100, [False])
            Tags.cmd_q.put("auto")
        # manu
        if DB.get_bits(101)[0]:
            DB.set_bits(101, [False])
            Tags.cmd_q.put("man")
        # save
        if DB.get_bits(110)[0]:
            DB.set_bits(110, [False])
            Tags.cmd_q.put("save")
        # set-point update
        sp_value = DB.get_floats(100)[0]
        if not is_nan(sp_value):
            DB.set_floats(100, [float('nan')])
            Tags.cmd_q.put("sp %.2f" % sp_value)
        # output update for manual mode
        out_value = DB.get_floats(102)[0]
        if not is_nan(out_value):
            DB.set_floats(102, [float('nan')])
            Tags.cmd_q.put("out %.2f" % out_value)
        # set kp params
        kp_value = DB.get_floats(104)[0]
        if not is_nan(kp_value):
            DB.set_floats(104, [float('nan')])
            Tags.cmd_q.put("kp %.2f" % kp_value)
        # set ki params
        ki_value = DB.get_floats(106)[0]
        if not is_nan(ki_value):
            DB.set_floats(106, [float('nan')])
            Tags.cmd_q.put("ki %.2f" % ki_value)
        # set kd params
        kd_value = DB.get_floats(108)[0]
        if not is_nan(kd_value):
            DB.set_floats(108, [float('nan')])
            Tags.cmd_q.put("kd %.2f" % kd_value)
        # refresh PID status
        with Tags.lock:
            coils_l = [Tags.AUTO, Tags.MAN]
        DB.set_bits(0, coils_l)
        # refresh PID values
        with Tags.lock:
            write_l = [Tags.PV, Tags.SP, Tags.OUT, Tags.KP, Tags.KI, Tags.KD]
        DB.set_floats(0, write_l)
        # wait next loop
        time.sleep(0.5)


# main program
if __name__ == "__main__":
    # init and start modbus data manager
    tp = Thread(target=mbus_data_thread)
    # set daemon: polling thread will exit if main thread exit
    tp.daemon = True
    tp.start()

    # init and start modbus server(remain this after modbus data manager init)
    server = ModbusServer(host="0.0.0.0", port=502, no_block=True)
    server.start()

    # init serial port
    s = ArduinoCommandSerial("/dev/ttyATH0", baudrate=9600, timeout=2.0)

    # init PID board
    # s.send_cmd("auto", echo=True)

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
