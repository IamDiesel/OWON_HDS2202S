import array
import queue
import usb.core
import usb.util
import time
"""lib usb win32 needs to bee installed
https://github.com/mcuee/libusb-win32/releases
"""
#from threading import Thread
#from queue import Queue
#PyYaml
#matplotlib
#pyusb
#scipy


class OWON_USB_Handler:
    """
    Send and receive USB data to and from OWON Oscilloscope
    """

    def __init__(self):
        self.dev = usb.core.find(idVendor=0x5345, idProduct=0x1234)
        # dev.reset()
        # time.sleep()
        if self.dev is None:
            print("Dev not found")
            #raise ValueError('Owon HDS200X scope not found; please set to HID mode and reconnect via USB.')

        self._running = True
        self.send_cmds_q = queue.LifoQueue()
        print(self.send_cmds_q)
        self.rcv_data_q = queue.LifoQueue()
        #self.rcv_ch1_q = queue.LifoQueue()
        #self.rcv_ch2_q

    def get_send_rcv_q(self):
        return self.send_cmds_q, self.rcv_data_q

    def terminate(self):
        self._running = False

    def send_receive(self):
        send_q_empty = True
        try:
            cmd = self.send_cmds_q.get_nowait()
            send_q_empty = False
        except queue.Empty:
            pass

        if(send_q_empty == False):
            print("USB Handler received cmd")
            try:
                # address taken from results of print(dev):   ENDPOINT 0x3: Bulk OUT
                self.dev.write(1, cmd)
                # address taken from results of print(dev):   ENDPOINT 0x81: Bulk IN
                result = (self.dev.read(0x81, 100000, 1000))
            except AttributeError:
                result = array.array('i',[40])
                pass
            try:
                self.rcv_data_q.put(result.tobytes().decode('utf-8'))
            except queue.Full:
                print("Send queue is fulll, cmd:", cmd," res: ",result)
                pass

    def run(self):
        while(self._running):
            self.send_receive()
            time.sleep(10 / 1000)