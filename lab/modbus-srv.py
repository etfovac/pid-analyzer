#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Modbus/TCP server

from pyModbusTCP.server import ModbusServer

if __name__ == '__main__':
    # start modbus server
    server = ModbusServer(host="0.0.0.0", port=502)
    server.start()
