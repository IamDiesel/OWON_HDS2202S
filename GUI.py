import queue

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import threading
from matplotlib.widgets import Button
import OWON_Handler
import USB_Handler
from threading import Thread
import time
import numpy as np
import sys


class Controls:

    def __init__(self, owon_handle, scopescreen):
        self.owon_handle = owon_handle
        self.scopescreen = scopescreen
        self.x = np.arange(0, 1, 0.02)
        self.i = 1
    def ch1_hOffset(self, event):
        print("Button pressed in GUI")
        owon_handle.onThread(owon_handle.testcall)
        self.scopescreen.set_xdata(self.x**self.i)
        self.scopescreen.set_ydata(self.x)
        self.i +=1
        plt.draw()

    def ch2_hOffset(self, event):
        print("Button pressed in GUI")
        owon_handle.onThread(owon_handle.testcall)
        self.scopescreen.set_xdata(self.x**self.i)
        self.scopescreen.set_ydata(self.x)
        self.i +=1
        plt.draw()


class GUI(threading.Thread):

    def __init__(self, owon_handle, usb_handle):
        self.interval_ms = 100
        self.owon_handle = owon_handle
        self.usb_handle = usb_handle
        #receive oscilloscope data from OWON_Handler via qui
        self.gui_points_q = owon_handle.get_gui_points_q()
        self.fig_gui, self.gui_screen = plt.subplots()
        plt.subplots_adjust(left=0.1, bottom=0.3)
        #self.fig_scope, self.scopescreen = plt.subplots()
        self.fig_scope, = plt.plot([],[])
        self.gui_screen.set(xlabel='time (s)', ylabel='voltage (V)', title='HDS2202(S)-DATA-AQC')
        self.gui_screen.grid(linestyle=':')
        self._running = False
        self.ctrl_callback = Controls(self.owon_handle, self.fig_scope)
        ax_ch1_hOffset = self.fig_gui.add_axes([0.0, 0.0, 0.2, 0.05])
        ax_ch2_hOffset = self.fig_gui.add_axes([0.2, 0.0, 0.2, 0.05])
        self.btn_ch1_h_offset = Button(ax_ch1_hOffset, 'CH1 hOffset')
        self.btn_ch2_h_offset = Button(ax_ch2_hOffset, 'CH2 hOffset')
        self.btn_ch1_h_offset.on_clicked(self.ctrl_callback.ch1_hOffset)
        self.btn_ch1_h_offset.on_clicked(self.ctrl_callback.ch2_hOffset)
        self.fig_gui.canvas.mpl_connect('close_event', self.on_close)
        super(GUI, self).__init__()


    def update(self):
        try:
            ch_data_struct = self.gui_points_q.get_nowait()
            self.fig_scope.set_xdata(ch_data_struct.get_X())
            self.fig_scope.set_ydata(ch_data_struct.get_Y())
            yscale = ch_data_struct.get_yscale()
            xscale = ch_data_struct.get_xscale()
            #print(yscale)
            self.gui_screen.set_ylim(-4.0 * yscale, 4.0 * yscale)
            self.gui_screen.set_xlim(-7 * xscale, 7*xscale)
            #xpoints = np.linspace(-6 * xscale, 6 * xscale, 300)
            plt.draw()
        except queue.Empty:
            pass

        #print("UPD")
        #self.scopescreen.cla()
        #xpoints = np.array([1, 8])
        #ypoints = np.array([3, 10])
        #plt.set
        #plt.plot(xpoints, ypoints)
#        self.btn_ch1_h_offset.on_clicked(self.ctrl_callback.ch1_hOffset)
        #plt.draw()
        pass


    def run(self):
        self._running = True
        while(self._running):
            self.update()
            time.sleep(self.interval_ms/1000)

    def show(self):
        plt.show()

    def on_close(self, event):
        self.owon_handle.onThread(self.owon_handle.terminate)
        self.usb_handle.terminate()
        self._running = False
        #sys.exit()




if __name__ == "__main__":
    usb_handle = USB_Handler.OWON_USB_Handler()
    send_cmds_q, rec_data_q = usb_handle.get_send_rcv_q()
    owon_handle = OWON_Handler.OWON_Handler(send_cmds_q, rec_data_q)
    owon_gui= GUI(owon_handle, usb_handle)
    owon_handle_thread = Thread(target=owon_handle.run)
    owon_gui_thread = Thread(target=owon_gui.run)
    owon_usb_thread = Thread(target=usb_handle.run)

    owon_handle_thread.start()
    owon_gui_thread.start()

    owon_usb_thread.start()
    owon_gui.show()

    owon_gui_thread.join()
    owon_handle_thread.join()
    owon_usb_thread.join()

    #plt.show()





