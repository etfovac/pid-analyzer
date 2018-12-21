#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pyHMI.Colors import *
from pyHMI.DS_ModbusTCP import ModbusTCPDevice
from pyHMI.Tag import Tag
import time
import tkinter as tk
from tkinter import ttk


class Devices(object):
    # init datasource
    # PLC TBox
    yun = ModbusTCPDevice("192.168.0.90", port=502, timeout=2.0, refresh=1.0)
    # init modbus tables
    yun.add_bits_table(0, 2)
    yun.add_floats_table(0, 6)


class Tags(object):
    # tags list
    # from Yun
    PID_AUTO = Tag(False, src=Devices.yun, ref={"type": "bit", "addr": 0})
    PID_MAN = Tag(False, src=Devices.yun, ref={"type": "bit", "addr": 1})
    PID_PV = Tag(0.0, src=Devices.yun, ref={"type": "float", "addr": 0})
    PID_SP = Tag(0.0, src=Devices.yun, ref={"type": "float", "addr": 2})
    PID_OUT = Tag(0.0, src=Devices.yun, ref={"type": "float", "addr": 4})
    # to Yun
    SET_AUTO_MODE = Tag(False, src=Devices.yun, ref={"type": "w_bit", "addr": 100})
    SET_MAN_MODE = Tag(False, src=Devices.yun, ref={"type": "w_bit", "addr": 101})
    SET_PID_SP = Tag(0.0, src=Devices.yun, ref={"type": "w_float", "addr": 100})
    SET_PID_OUT = Tag(0.0, src=Devices.yun, ref={"type": "w_float", "addr": 102})

    @classmethod
    def update_tags(cls):
        # update tags
        pass


class HMITab(tk.Frame):
    def __init__(self, notebook, update_ms=500, *args, **kwargs):
        tk.Frame.__init__(self, notebook, *args, **kwargs)
        # global tk app shortcut
        self.notebook = notebook
        self.app = notebook.master
        # frame auto-refresh delay (in ms)
        self.update_ms = update_ms
        # setup auto-refresh of notebook tab (on-visibility and every update_ms)
        self.bind('<Visibility>', lambda evt: self.tab_update())
        self._tab_update()

    def _tab_update(self):
        if self.winfo_ismapped():
            self.tab_update()
        self.master.after(self.update_ms, self._tab_update)

    def tab_update(self):
        pass


class TabMisc(HMITab):
    def __init__(self, notebook, update_ms=500, *args, **kwargs):
        HMITab.__init__(self, notebook, update_ms, *args, **kwargs)
        # Some vars
        self.set_sp_str = tk.StringVar(value="0.0")
        self.set_out_str = tk.StringVar(value="0.0")
        # PID states
        self.frmState = tk.LabelFrame(self, text="Etat du PID", padx=10, pady=10)
        self.frmState.grid(row=0, column=0, padx=5, pady=5, sticky=tk.NSEW)
        self.state_list = HMIBoolList(self.frmState, lbl_args={"width": 15})
        self.state_list.add("AUTO", Tags.PID_AUTO, alarm=False)
        self.state_list.add("MAN", Tags.PID_MAN, alarm=False)
        self.state_list.build()
        # Measures
        self.frmMeasReg = tk.LabelFrame(self, text="Mesures régulateur", padx=10, pady=10)
        self.frmMeasReg.grid(row=0, column=1, padx=5, pady=5, sticky=tk.NSEW)
        self.cons_r = HMIAnalogList(self.frmMeasReg, lbl_args={'width': 10})
        self.cons_r.add("Consigne", Tags.PID_SP, unit="m3/h", fmt="%0.2f")
        self.cons_r.add("Mesure", Tags.PID_PV, unit="m3/h", fmt="%0.2f")
        self.cons_r.add("Sortie", Tags.PID_OUT, unit="%", fmt="%0.2f")
        self.cons_r.build()
        # Choices
        self.frmChoice = tk.LabelFrame(self, text="Choix du Mode", padx=10, pady=10)
        self.frmChoice.grid(row=0, column=2, padx=5, pady=5, sticky=tk.NSEW)
        self.cmd_list = HMIButtonList(self.frmChoice, dim=1, btn_args={'width': 10})
        self.cmd_list.add("Automatique", cmd=lambda: Tags.SET_AUTO_MODE.set(True), btn_args={"bg": "light salmon"})
        self.cmd_list.add("Manuel", cmd=lambda: Tags.SET_MAN_MODE.set(True), btn_args={"bg": "light salmon"})
        self.cmd_list.build()
        # Settings
        self.frmSetReg = tk.LabelFrame(self, text="Réglages", padx=10, pady=10)
        self.frmSetReg.grid(row=0, column=3, padx=5, pady=5, sticky=tk.NSEW)
        tk.Label(self.frmSetReg, text="Consigne").grid(row=0, column=0, padx=5, pady=5)
        self.ent_sp = tk.Entry(self.frmSetReg, width="6", justify=tk.RIGHT, textvariable=self.set_sp_str)
        self.ent_sp.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(self.frmSetReg, text="m3/h").grid(row=0, column=2, padx=5, pady=5)
        self.but_sp = tk.Button(self.frmSetReg, text="Set", command=self.send_cons_value)
        self.but_sp.grid(row=0, column=3, padx=5, pady=5)
        tk.Label(self.frmSetReg, text="Sortie").grid(row=1, column=0, padx=5, pady=5)
        self.ent_out = tk.Entry(self.frmSetReg, width="6", justify=tk.RIGHT, textvariable=self.set_out_str)
        self.ent_out.grid(row=1, column=1, padx=5, pady=5)
        tk.Label(self.frmSetReg, text="%").grid(row=1, column=2, padx=5, pady=5)
        self.but_out = tk.Button(self.frmSetReg, text="Set", command=self.send_out_value)
        self.but_out.grid(row=1, column=3, padx=5, pady=5)

    def tab_update(self):
        self.state_list.update()
        self.cons_r.update()

    def send_cons_value(self):
        try:
            send_cons = float(self.set_sp_str.get())
            if not 25.0 >= send_cons >= 0.0:
                raise ValueError
            Tags.SET_PID_SP.set(send_cons)
            self.ent_sp.config(bg="white")
        except ValueError:
            self.ent_sp.config(bg="red")

    def send_out_value(self):
        try:
            send_out = float(self.set_out_str.get())
            if not 100.0 >= send_out >= 0.0:
                raise ValueError
            Tags.SET_PID_OUT.set(send_out)
            self.ent_sp.config(bg="white")
        except ValueError:
            self.ent_sp.config(bg="red")


class HMIToolbar(tk.Frame):
    def __init__(self, tk_app, update_ms=500, *args, **kwargs):
        tk.Frame.__init__(self, tk_app, *args, **kwargs)
        self.tk_app = tk_app
        self.update_ms = update_ms
        # build toolbar
        self.butTbox = tk.Button(self, text='Yun', relief=tk.SUNKEN,
                                 state='disabled', disabledforeground='black')
        self.butTbox.pack(side=tk.LEFT)
        self.lblDate = tk.Label(self, text='', font=('TkDefaultFont', 12))
        self.lblDate.pack(side=tk.RIGHT)
        self.pack(side=tk.BOTTOM, fill=tk.X)
        # setup auto-refresh of notebook tab (on-visibility and every update_ms)
        self.bind('<Visibility>', lambda evt: self.tab_update())
        self._tab_update()

    def _tab_update(self):
        self.tab_update()
        self.master.after(self.update_ms, self._tab_update)

    def tab_update(self):
        self.butTbox.configure(background=GREEN if Devices.yun.connected else PINK)
        self.lblDate.configure(text=time.strftime('%H:%M:%S %d/%m/%Y'))


class HMIApp(tk.Tk):
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        # configure main window
        self.wm_title("Contrôle de la régulation du flux d'air")
        # self.attributes('-fullscreen', True)
        # self.geometry("800x600")
        # periodic tags update
        self.do_every(Tags.update_tags, every_ms=500)
        # build a notebook with tabs
        self.note = ttk.Notebook(self)
        self.tab_misc = TabMisc(self.note)
        self.note.add(self.tab_misc, text='PID (F1)')
        # defaut selected tab
        self.note.select(self.tab_misc)
        self.note.pack(fill=tk.BOTH, expand=True)
        # bind function keys to tabs
        self.bind('<F1>', lambda evt: self.note.select(self.tab_misc))
        # build toolbar
        self.toolbar = HMIToolbar(self, update_ms=500)

    def do_every(self, do_cmd, every_ms=1000):
        do_cmd()
        self.after(every_ms, lambda: self.do_every(do_cmd, every_ms=every_ms))


if __name__ == '__main__':
    # main Tk App
    app = HMIApp()
    app.mainloop()
