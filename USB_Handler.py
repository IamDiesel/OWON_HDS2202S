import queue
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

    def __init__(self, dev):
        self.dev = dev
        self.running = True
        self.send_cmds_q = queue.LifoQueue()
        self.rcv_data_q = queue.LifoQueue()
        #self.rcv_ch1_q = queue.LifoQueue()
        #self.rcv_ch2_q


    def terminate(self):
        self.running = False

    def send(self):
        send_q_empty = True
        try:
            cmd = self.send_cmds_q.get_nowait()
            send_q_empty = False
        except queue.Empty:
            pass

        if(send_q_empty == False):
            # address taken from results of print(dev):   ENDPOINT 0x3: Bulk OUT
            self.dev.write(1, cmd)
            # address taken from results of print(dev):   ENDPOINT 0x81: Bulk IN
            result = (self.dev.read(0x81, 100000, 1000))
            try:
                self.rcv_data_q.put(result)
            except queue.Full:
                print("Send queue is fulll, cmd:", cmd," res: ",result)
                pass


    def run(self):
        while(True):
            self.send()