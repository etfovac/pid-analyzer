#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pyHMI.Colors import *
from pyHMI.DS_ModbusTCP import ModbusTCPDevice
from pyHMI.Tag import Tag
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib import style


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
    PID_KP = Tag(0.0, src=Devices.yun, ref={"type": "float", "addr": 6})
    PID_KI = Tag(0.0, src=Devices.yun, ref={"type": "float", "addr": 8})
    PID_KD = Tag(0.0, src=Devices.yun, ref={"type": "float", "addr": 10})
    # to Yun
    SET_AUTO_MODE = Tag(False, src=Devices.yun, ref={"type": "w_bit", "addr": 100})
    SET_MAN_MODE = Tag(False, src=Devices.yun, ref={"type": "w_bit", "addr": 101})
    SET_EEPROM_SAVE = Tag(False, src=Devices.yun, ref={"type": "w_bit", "addr": 110})
    SET_PID_SP = Tag(0.0, src=Devices.yun, ref={"type": "w_float", "addr": 100})
    SET_PID_OUT = Tag(0.0, src=Devices.yun, ref={"type": "w_float", "addr": 102})
    SET_PID_KP = Tag(0.0, src=Devices.yun, ref={"type": "w_float", "addr": 104})
    SET_PID_KI = Tag(0.0, src=Devices.yun, ref={"type": "w_float", "addr": 106})
    SET_PID_KD = Tag(0.0, src=Devices.yun, ref={"type": "w_float", "addr": 108})

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

    def do_every(self, do_cmd, every_ms=1000):
        do_cmd()
        self.after(every_ms, lambda: self.do_every(do_cmd, every_ms=every_ms))

    def _tab_update(self):
        if self.winfo_ismapped():
            self.tab_update()
        self.master.after(self.update_ms, self._tab_update)

    def tab_update(self):
        pass


class TabControl(HMITab):
    def __init__(self, notebook, update_ms=500, *args, **kwargs):
        HMITab.__init__(self, notebook, update_ms, *args, **kwargs)
        # Some vars
        self.set_sp_str = tk.StringVar(value="0.0")
        self.set_out_str = tk.StringVar(value="0.0")
        self.set_kp_str = tk.StringVar(value="0.0")
        self.set_ki_str = tk.StringVar(value="0.0")
        self.set_kd_str = tk.StringVar(value="0.0")
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
        self.cmd_list = HMIButtonList(self.frmChoice, dim=1, btn_args={'width': 14})
        self.cmd_list.add("Mode automatique", cmd=lambda: Tags.SET_AUTO_MODE.set(True), btn_args={"bg": "light salmon"})
        self.cmd_list.add("Mode manuel", cmd=lambda: Tags.SET_MAN_MODE.set(True), btn_args={"bg": "light salmon"})
        self.cmd_list.add("", btn_args={"state": "disabled"})
        self.cmd_list.add("Save to EEPROM", cmd=lambda: Tags.SET_EEPROM_SAVE.set(True), btn_args={"bg": "tomato3"})
        self.cmd_list.build()
        # Settings
        self.frmSetCns = tk.LabelFrame(self, text="Consignes", padx=10, pady=10)
        self.frmSetCns.grid(row=0, column=3, padx=5, pady=5, sticky=tk.NSEW)
        tk.Label(self.frmSetCns, text="Consigne").grid(row=0, column=0, padx=5, pady=5)
        self.ent_sp = tk.Entry(self.frmSetCns, width="6", justify=tk.RIGHT, textvariable=self.set_sp_str)
        self.ent_sp.grid(row=0, column=1, padx=5, pady=5)
        self.ent_sp.bind("<Return>", self.send_cons_value)
        tk.Label(self.frmSetCns, text="m3/h").grid(row=0, column=2, padx=5, pady=5)
        tk.Label(self.frmSetCns, text="Sortie").grid(row=1, column=0, padx=5, pady=5)
        self.ent_out = tk.Entry(self.frmSetCns, width="6", justify=tk.RIGHT, textvariable=self.set_out_str)
        self.ent_out.grid(row=1, column=1, padx=5, pady=5)
        self.ent_out.bind("<Return>", self.send_out_value)
        tk.Label(self.frmSetCns, text="%").grid(row=1, column=2, padx=5, pady=5)
        # Settings
        self.frmSetPID = tk.LabelFrame(self, text="Réglages PID", padx=10, pady=10)
        self.frmSetPID.grid(row=0, column=4, padx=5, pady=5, sticky=tk.NSEW)
        tk.Label(self.frmSetPID, text="Kp").grid(row=0, column=0, padx=5, pady=5)
        self.ent_kp = tk.Entry(self.frmSetPID, width="6", justify=tk.RIGHT, textvariable=self.set_kp_str)
        self.ent_kp.grid(row=0, column=1, padx=5, pady=5)
        self.ent_kp.bind("<Return>", self.send_kp_value)
        tk.Label(self.frmSetPID, text="Ki").grid(row=1, column=0, padx=5, pady=5)
        self.ent_ki = tk.Entry(self.frmSetPID, width="6", justify=tk.RIGHT, textvariable=self.set_ki_str)
        self.ent_ki.grid(row=1, column=1, padx=5, pady=5)
        self.ent_ki.bind("<Return>", self.send_ki_value)
        tk.Label(self.frmSetPID, text="Kd").grid(row=2, column=0, padx=5, pady=5)
        self.ent_kd = tk.Entry(self.frmSetPID, width="6", justify=tk.RIGHT, textvariable=self.set_kd_str)
        self.ent_kd.grid(row=2, column=1, padx=5, pady=5)
        self.ent_kd.bind("<Return>", self.send_kd_value)

    def tab_update(self):
        # update display list
        self.state_list.update()
        self.cons_r.update()
        # manage out entry: is disabled if not in manual mode
        self.ent_out.config(state="normal" if Tags.PID_MAN.val else "disabled")
        # manage kp, ki, kd update: update entry value if widget not currently edited
        if self.master.focus_displayof() != self.ent_sp:
            self.set_sp_str.set("%.2f" % Tags.PID_SP.val)
            self.ent_sp.config(bg="white")
        if self.master.focus_displayof() != self.ent_out:
            self.set_out_str.set("%.2f" % Tags.PID_OUT.val)
            self.ent_out.config(bg="white")
        if self.master.focus_displayof() != self.ent_kp:
            self.set_kp_str.set("%.2f" % Tags.PID_KP.val)
            self.ent_kp.config(bg="white")
        if self.master.focus_displayof() != self.ent_ki:
            self.set_ki_str.set("%.2f" % Tags.PID_KI.val)
            self.ent_ki.config(bg="white")
        if self.master.focus_displayof() != self.ent_kd:
            self.set_kd_str.set("%.2f" % Tags.PID_KD.val)
            self.ent_kd.config(bg="white")

    def send_cons_value(self, _):
        try:
            send_cons = round(float(self.set_sp_str.get()), 2)
            if not 25.0 >= send_cons >= 0.0:
                raise ValueError
            Tags.SET_PID_SP.set(send_cons)
            self.ent_sp.config(bg="green")
        except ValueError:
            self.ent_sp.config(bg="red")

    def send_out_value(self, _):
        try:
            send_out = round(float(self.set_out_str.get()), 2)
            if not 100.0 >= send_out >= 0.0:
                raise ValueError
            Tags.SET_PID_OUT.set(send_out)
            self.ent_out.config(bg="green")
        except ValueError:
            self.ent_out.config(bg="red")

    def send_kp_value(self, _):
        try:
            send_kp = float(self.set_kp_str.get())
            if not 1000.0 >= send_kp >= 0.0:
                raise ValueError
            Tags.SET_PID_KP.set(send_kp)
            self.ent_kp.config(bg="green")
        except ValueError:
            self.ent_kp.config(bg="red")

    def send_ki_value(self, _):
        try:
            send_ki = float(self.set_ki_str.get())
            if not 1000.0 >= send_ki >= 0.0:
                raise ValueError
            Tags.SET_PID_KI.set(send_ki)
            self.ent_ki.config(bg="green")
        except ValueError:
            self.ent_ki.config(bg="red")

    def send_kd_value(self, _):
        try:
            send_kd = float(self.set_kd_str.get())
            if not 1000.0 >= send_kd >= 0.0:
                raise ValueError
            Tags.SET_PID_KD.set(send_kd)
            self.ent_kd.config(bg="green")
        except ValueError:
            self.ent_kd.config(bg="red")


class TabGraph(HMITab):
    DATA_LEN = 900

    def __init__(self, notebook, update_ms=1000, *args, **kwargs):
        HMITab.__init__(self, notebook, update_ms, *args, **kwargs)
        # init data
        self.t = []
        self.pv_l = []
        self.sp_l = []
        self.out_l = []
        # init matplotlib graph
        style.use("ggplot")
        self.fig = Figure(figsize=(8, 5), dpi=112)
        self.ax1 = self.fig.add_subplot(211)
        self.ax2 = self.fig.add_subplot(212, sharex=self.ax1)
        self.ax1.set_ylim(0, 25, auto=True)
        self.ax2.set_ylim(0, 100, auto=False)
        self.ax1.set_ylabel("m3/h", color="black")
        self.ax2.set_ylabel("%", color="black")
        self.fig.set_tight_layout(True)
        # add graph widget to tk app
        graph = FigureCanvasTkAgg(self.fig, master=self)
        canvas = graph.get_tk_widget()
        canvas.pack(expand=True)
        # periodic data update
        self.do_every(self.data_update, every_ms=1000)

    def tab_update(self):
        self.ax1.clear()
        self.ax2.clear()
        self.ax1.set_ylim(0, 25, auto=True)
        self.ax2.set_ylim(0, 100, auto=False)
        self.ax1.set_ylabel("m3/h", color="black")
        self.ax2.set_ylabel("%", color="black")
        self.ax1.plot(self.t, self.pv_l, "b", label="pv")
        self.ax1.plot(self.t, self.sp_l, "g", label="sp")
        self.ax1.legend()
        self.ax2.plot(self.t, self.out_l, "r", label="out")
        self.ax2.legend()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def data_update(self):
        self.t.append(datetime.now())
        while len(self.t) > TabGraph.DATA_LEN:
            self.t.pop(0)
        self.pv_l.append(Tags.PID_PV.val)
        while len(self.pv_l) > TabGraph.DATA_LEN:
            self.pv_l.pop(0)
        self.sp_l.append(Tags.PID_SP.val)
        while len(self.sp_l) > TabGraph.DATA_LEN:
            self.sp_l.pop(0)
        self.out_l.append(Tags.PID_OUT.val)
        while len(self.out_l) > TabGraph.DATA_LEN:
            self.out_l.pop(0)


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
        self.tab_ctrl = TabControl(self.note)
        self.tab_graph = TabGraph(self.note)
        self.note.add(self.tab_ctrl, text='Contrôle (F1)')
        self.note.add(self.tab_graph, text='Graphique (F2)')
        # default selected tab
        self.note.select(self.tab_ctrl)
        self.note.pack(fill=tk.BOTH, expand=True)
        # bind function keys to tabs
        self.bind("<F1>", lambda evt: self.note.select(self.tab_ctrl))
        self.bind("<F2>", lambda evt: self.note.select(self.tab_graph))
        # build toolbar
        self.toolbar = HMIToolbar(self, update_ms=500)

    def do_every(self, do_cmd, every_ms=1000):
        do_cmd()
        self.after(every_ms, lambda: self.do_every(do_cmd, every_ms=every_ms))


class HMIToolbar(tk.Frame):
    def __init__(self, tk_app, update_ms=500, *args, **kwargs):
        tk.Frame.__init__(self, tk_app, *args, **kwargs)
        self.tk_app = tk_app
        self.update_ms = update_ms
        # build toolbar
        self.butTbox = tk.Button(self, text="Yun", relief=tk.SUNKEN, width=8,
                                 state="disabled", disabledforeground="black")
        self.butTbox.pack(side=tk.LEFT)
        self.lblDate = tk.Label(self, text="", font=("TkDefaultFont", 12))
        self.lblDate.pack(side=tk.RIGHT)
        self.pack(side=tk.BOTTOM, fill=tk.X)
        # setup auto-refresh of notebook tab (on-visibility and every update_ms)
        self.bind("<Visibility>", lambda evt: self.tab_update())
        self._tab_update()

    def _tab_update(self):
        self.tab_update()
        self.master.after(self.update_ms, self._tab_update)

    def tab_update(self):
        self.butTbox.configure(background=GREEN if Devices.yun.connected else PINK)
        self.lblDate.configure(text=time.strftime('%H:%M:%S %d/%m/%Y'))


if __name__ == '__main__':
    # main Tk App
    app = HMIApp()
    app.mainloop()
