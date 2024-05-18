import queue
import threading


class OWON_Handler(threading.Thread):
    """
    SCPI Layer on top of USB Handler.
    Responsible for parsing data from the OWON oscilloscope
    and wrapper for OWON Oscilloscope SCPI Commands
    """
    def __init__(self, q, send_cmds_q, rcv_data_q):
        self.q = q
        self.send_cmds_q = send_cmds_q
        self.rcv_data_q = rcv_data_q
        super(OWON_Handler, self).__init__()

    def onThread(self, function, *args, **kwargs):
        self.q.put((function,args,kwargs))


    def run(self):
        while True:
            try:
                function, args, kwargs = self.q.get_nowait()
                function(*args, **kwargs)
            except queue.Empty:
                self.idle()

    def idle(self):
        print("process send and rcv queues")
        #TODO implement sending and receiving via USB_Handler





