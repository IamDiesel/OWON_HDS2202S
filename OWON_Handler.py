import queue
import threading
import sys
import time
import yaml
import numpy as np
import OWON_Points


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
        self.gui_points_q = queue.LifoQueue()
        self._running = False
        self.divfactor = {
            "m": 1000,  # milli
            "u": 1000000,  # micro
            "n": 1000000000,  # nano
        }
        self.horizontal_scale_steps = [0.0000020, 0.0000050, 0.0000100, 0.0000200, 0.0000500, 0.000100, 0.000200, 0.000500, 0.0010, 0.002,
                 0.005,0.010, 0.020, 0.050, 0.100, 0.200, 0.500, 1.0, 2.0, 5.0, 10, 20, 50, 100, 200, 500, 1000.0, 2000.0,
                 5000.0,10000, 20000, 50000, 100000, 200000, 500000, 1000000]
        self.horizontal_scale_steps_str = ["2.0ns", "5.0ns", "10.0ns", "20.0ns", "50.0ns", "100ns", "200ns", "500ns", "1.0us", "2.0us",
                     "5.0us","10us", "20us", "50us", "100us", "200us", "500us", "1.0ms", "2.0ms", "5.0ms", "10ms", "20ms",
                     "50ms","100ms", "200ms", "500ms", "1.0s", "2.0s", "5.0s", "10s", "20s", "50s", "100s", "200s", "500s",
                     "1000s"]
        super(OWON_Handler, self).__init__()

    def get_gui_points_q(self):
        return self.gui_points_q

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
                time.sleep(100 / 1000)

    def idle(self):
        #print("implement additional rec events if they are sent from osci")
        #periodically ask for ch1 / ch2 header and point data. Parse the data and send it to the gui
        try:
            self.send_cmds_q.put(':DATA:WAVE:SCREen:HEAD?')
            header = self.rcv_data_q.get()
            print("Header: [", header, "]")
            if header is not None:
                print("Header2: [", header, "]")
                header = header[4:].tobytes().decode('utf-8')
                ch1_raw_data = None
                ch2_raw_data = None
                print(header)
                ch1_on = False
                ch2_on = False
                header = yaml.safe_load(header)
                display_ch1 = header["CHANNEL"][0]["DISPLAY"]
                display_ch2 = header["CHANNEL"][1]["DISPLAY"]
                if(display_ch1 == "ON"):
                    ch1_on = True
                    self.send_cmds_q.put(':DATA:WAVE:SCREen:CH1?')
                    ch1_raw_data = self.rcv_data_q.get()
                if(display_ch2 == "ON"):
                    ch2_on = True
                    self.send_cmds_q.put(':DATA:WAVE:SCREen:CH2?')
                    ch2_raw_data = self.rcv_data_q.get()

                self.parse_header_and_pts(header, ch1_on, ch2_on, ch1_raw_data, ch2_raw_data)
        except queue.Empty:
            pass


    def testcall(self):
        #print("Test OWON_Handler")
        self.send_cmds_q.put('*IDN?')
        try:
            owon_idn = self.rcv_data_q.get()
            print("OWON IDN: ", owon_idn)
        except queue.Empty:
            pass

    def terminate(self):
        self._running = False
        sys.exit()

    def parse_pts_helper(self, raw_data, yscale, yoffset, xscale, ch_on, xpoints, channel):
        length = int().from_bytes(raw_data[0:2], 'little', signed=False)
        data = [[],[]]  # array of datapoints, [0] is value, [1] is errorbar if available (when 600 points are returned)
        if (length == 300):
            for idx in range(4, len(raw_data), 1):
                # take 1 bytes and convert these to signed integer
                point = int().from_bytes([raw_data[idx]], 'little', signed=True);
                # data[0].append(yscale*(point-yoffset)/25)  # vertical scale is 25/div
                data[0].append(yscale * (point - yoffset / 25))  # vertical scale is 25/div
                data[1].append(0)  # no errorbar
        else:
            for idx in range(4, len(raw_data), 2):
                # take 2 bytes and convert these to signed integer for upper and lower value
                lower = int().from_bytes([raw_data[idx]], 'little', signed=True)
                upper = int().from_bytes([raw_data[idx + 1]], 'little', signed=True)
                # lower = yscale*(upper+lower-2*yoffset)/2
                # lower = yscale * (upper + lower) / 2
                # data[0].append( (lower / 25))  # vertical scale is 25/div
                data[0].append(yscale * (lower + upper - 2 * yoffset) / 50)  # average of the two datapoints
                # data[0].append(yscale*(lower+upper-2*yoffset)/50)  # average of the two datapoints
                data[1].append(yscale * (upper - lower) / 50)  # errorbar is delta between upper and lower
                #print("yscale:", yscale, " Offset", yoffset, "lower:", lower)

        for i in range(0, len(data[1])):
            data[1][i] = abs(data[1][i])

        ch_pts_struct = OWON_Points.OWON_Points(data[0], xpoints, channel, yscale, yoffset, xscale, ch_on)
        return ch_pts_struct

    def parse_header_and_pts(self,header, ch1_on, ch2_on, ch1_raw_data, ch2_raw_data):
        #header = yaml.safe_load(header)
        xscale = float(header["TIMEBASE"]["SCALE"][0:-2]) / \
                 self.divfactor.get(header["TIMEBASE"]["SCALE"][-2], 1)
        #display_ch1 = header["CHANNEL"][0]["DISPLAY"]
        #display_ch2 = header["CHANNEL"][1]["DISPLAY"]
        xpoints = np.linspace(-6 * xscale, 6 * xscale, 300)
        ch1_pts_struct = None
        ch2_pts_struct = None

        #parse channel 1 and 2 header if turned on
        if(ch1_on):
            yscale_ch1 = float(header["CHANNEL"][0]["PROBE"][0:-1]) * \
                     float(header["CHANNEL"][0]["SCALE"][0:-2]) / \
                     self.divfactor.get(header["CHANNEL"][0]["SCALE"][-2], 1)
            yoffset_ch1 = int(header["CHANNEL"][0]["OFFSET"])


        if(ch2_on):
            yscale_ch2 = float(header["CHANNEL"][1]["PROBE"][0:-1]) * \
                     float(header["CHANNEL"][1]["SCALE"][0:-2]) / \
                     self.divfactor.get(header["CHANNEL"][1]["SCALE"][-2], 1)
            yoffset_ch2 = int(header["CHANNEL"][1]["OFFSET"])

        if(ch1_on):
            ch1_pts_struct = self.parse_pts_helper(ch1_raw_data, yscale_ch1, yoffset_ch1, xscale, ch1_on, xpoints, 1)
            try:
                self.gui_points_q.put(ch1_pts_struct)
            except queue.Full:
                print("OWON Handler: GUI queue is full")
                pass
        if(ch2_on):
            ch2_pts_struct = self.parse_pts_helper(ch2_raw_data, yscale_ch2, yoffset_ch2, xscale, ch2_on, xpoints, 2)
            try:
                self.gui_points_q.put(ch2_pts_struct)
            except queue.Full:
                print("OWON Handler: GUI queue is full")
                pass


    def get_idn(self):
        #returns <Manufacturer>,<model>,<serial number>,X.XX.XX
        #XXXX,XXXXXXX,2128009,V2.1.1.5
        owon_idn = None
        self.send_cmds_q.put('*IDN?')
        try:
            owon_idn = self.rcv_data_q.get()
            #print("OWON IDN: ", owon_idn)
        except queue.Empty:
            pass
        return owon_idn


    def set_horizontal_scale(self,hor_scale_ms):
        """This functions sets the scale of the main time base"""
        #first, get closest floor value from the allowed steps list --> 1.5 will return 1.0ms
        step_res = None
        index_res = None
        for index, step in enumerate(self.horizontal_scale_steps):
            if index < (len(self.horizontal_scale_steps) - 1) and step_res == None:
                if hor_scale_ms >= step and hor_scale_ms < self.horizontal_scale_steps[index + 1]:
                    step_res = step
                    index_res = index
                    break
            else:
                step_res = step
                index_res = index
        step_res_str = self.horizontal_scale_steps_str[index_res]
        #send value to oscilloscope
        try:
            self.send_cmds_q.put(":HORIzontal:SCALe {}".format(step_res_str))
        except queue.Full:
            pass
        #return step_res_str

    def get_horizontal_scale(self):
        hor_scale = None
        try:
            self.send_cmds_q.put(":HORIzontal:SCALe?")
        except queue.Full:
            pass

        try:
            hor_scale = self.rcv_data_q.get()
        except queue.Empty:
            pass
        return hor_scale

    def set_horizontal_offset(self,div_offset):
        """sets the horizontal offset as factor of the main time base
        e.g. main time base = 500ms/div and div_offset = 3 div --> horizontal time offset = 1500ms"""
        try:
            self.send_cmds_q.put(":HORizontal:OFFset {}".format(int(div_offset)))
        except queue.Full:
            pass

    def get_horizontal_offset_in_div(self):
        time_offset_div = None
        try:
            self.send_cmds_q.put(":HORizontal:OFFset?")
        except queue.Full:
            pass

        try:
            time_offset_div = self.rcv_data_q.get()
        except queue.Empty:
            pass

        return time_offset_div



























