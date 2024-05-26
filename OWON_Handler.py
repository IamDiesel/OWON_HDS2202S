import queue
import threading
import sys


class OWON_Handler(threading.Thread):
    """
    SCPI Layer on top of USB Handler.
    Responsible for parsing data from the OWON oscilloscope
    and wrapper for OWON Oscilloscope SCPI Commands
    """
    def __init__(self, send_cmds_q, rcv_data_q):
        self.q = queue.LifoQueue()
        self.send_cmds_q = send_cmds_q
        self.rcv_data_q = rcv_data_q
        self._running = False
        super(OWON_Handler, self).__init__()

    def onThread(self, function, *args, **kwargs):
        self.q.put((function,args,kwargs))


    def run(self):
        self._running = True
        while(self._running):
            try:
                function, args, kwargs = self.q.get_nowait()
                function(*args, **kwargs)
            except queue.Empty:
                self.idle()

    def idle(self):
        #print("implement additional rec events if they are sent from osci")
        #TODO implement additional rec data from osci
        try:
            result = self.rcv_data_q.get_nowait()
            print(result)
        except queue.Empty:
            pass


    def testcall(self):
        #print("Test OWON_Handler")
        self.send_cmds_q.put('*IDN?')

    def terminate(self):
        self._running = False
        sys.exit()









