import matplotlib.pyplot as plt
import matplotlib.animation as animation
import threading
from matplotlib.widgets import Button
import OWON_Handler
from threading import Thread
import time
import sys


class Controls:

    def __init__(self, owon_handle, ):
        self.owon_handle = owon_handle
    def ch1_hOffset(self, event):
        print("Button pressed in GUI")
        owon_handle.onThread(owon_handle.testcall)
        plt.draw()


class GUI(threading.Thread):

    def __init__(self, owon_handle):
        self.interval_ms = 100
        self.owon_handle = owon_handle
        self.fig, self.scopescreen = plt.subplots()
        self._running = False
        #self.ani = None
        self.ctrl_callback = Controls(self.owon_handle)
        ax_ch1_hOffset = self.fig.add_axes([0.0, 0.0, 0.2, 0.05])
        self.btn_ch1_h_offset = Button(ax_ch1_hOffset, 'CH1 hOffset')
        self.btn_ch1_h_offset.on_clicked(self.ctrl_callback.ch1_hOffset)
        self.fig.canvas.mpl_connect('close_event', self.on_close)
        super(GUI, self).__init__()


    def update(self):
        print("UPD")
        self.scopescreen.cla()
#        self.btn_ch1_h_offset.on_clicked(self.ctrl_callback.ch1_hOffset)


    def run(self):
        self._running = True
        while(self._running):
            self.update()
            time.sleep(self.interval_ms/1000)


    #def startAnimation(self):
        #self.show()
        #self.ani = animation.FuncAnimation(fig=self.fig, func=self.update, frames=100, interval=2000)  # 20 fps
        #self.show()

    def show(self):
        plt.show()

    def on_close(self, event):
        self.owon_handle.onThread(self.owon_handle.terminate)
        self._running = False
        #sys.exit()




if __name__ == "__main__":
    owon_handle = OWON_Handler.OWON_Handler(0,0)
    owon_gui= GUI(owon_handle)
    owon_handle_thread = Thread(target=owon_handle.run)
    owon_gui_thread = Thread(target=owon_gui.run)

    owon_handle_thread.start()
    owon_gui_thread.start()
    owon_gui.show()
    owon_gui_thread.join()
    owon_handle_thread.join()

    #plt.show()





