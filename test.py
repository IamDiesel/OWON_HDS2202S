import usb.core
import usb.util
import yaml
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

""""""
#    [Port 8] usb device
# SOURCE 2.255.1
dev = None
def send(cmd):
    global dev
    # address taken from results of print(dev):   ENDPOINT 0x3: Bulk OUT
    dev.write(1, cmd)
    # address taken from results of print(dev):   ENDPOINT 0x81: Bulk IN
    result = (dev.read(0x81,100000,1000))
    #print(result)
    #result=0
    return result

def get_header():
    global dev
    # first 4 bytes indicate the number of data bytes following
    header = send(':DATA:WAVE:SCREen:HEAD?')
    header = header[4:].tobytes().decode('utf-8')
    return header

def get_data(ch, yscale, yoffset):
    # first 4 bytes indicate the number of data bytes following
    try:
        rawdata = send(':DATA:WAVE:SCREen:CH{}?'.format(ch))
        length = int().from_bytes(rawdata[0:2],'little',signed=False)
        data = [[],[]] # array of datapoints, [0] is value, [1] is errorbar if available (when 600 points are returned)
        if (length == 300):
            for idx in range(4,len(rawdata),1):
                # take 1 bytes and convert these to signed integer
                point = int().from_bytes([rawdata[idx]],'little',signed=True);
                #data[0].append(yscale*(point-yoffset)/25)  # vertical scale is 25/div
                data[0].append(yscale * (point - yoffset/ 25))   # vertical scale is 25/div
                data[1].append(0)  # no errorbar
        else:
            for idx in range(4,len(rawdata),2):
                # take 2 bytes and convert these to signed integer for upper and lower value
                lower = int().from_bytes([rawdata[idx]],'little',signed=True)
                upper = int().from_bytes([rawdata[idx+1]],'little',signed=True)
                #lower = yscale*(upper+lower-2*yoffset)/2
                #lower = yscale * (upper + lower) / 2
                #data[0].append( (lower / 25))  # vertical scale is 25/div
                data[0].append(yscale * (lower + upper - 2*yoffset) / 50)  # average of the two datapoints
                #data[0].append(yscale*(lower+upper-2*yoffset)/50)  # average of the two datapoints
                data[1].append(yscale*(upper-lower)/50)  # errorbar is delta between upper and lower
                print("yscale:",yscale," Offset",yoffset,"lower:",lower)
                #value in volts: lower*yscale*/(25*2)
                #data[1].append(0)
    except usb.core.USBTimeoutError:
            pass


    return data


def readYScaleAndOffsetFromHeader():
    global dev
    #global yscale, yoffset
    header = yaml.safe_load(get_header())
    yscale = float(header["CHANNEL"][0]["PROBE"][0:-1]) * \
             float(header["CHANNEL"][0]["SCALE"][0:-2]) / \
             divfactor.get(header["CHANNEL"][0]["SCALE"][-2], 1)
    yoffset = int(header["CHANNEL"][0]["OFFSET"])
    print("offset",yoffset)
    return yscale, yoffset, header

def initialize():
    global dev

    dev = usb.core.find(idVendor=0x5345, idProduct=0x1234)
    #dev.reset()
    #time.sleep()
    if dev is None:
        raise ValueError('Owon HDS200X scope not found; please set to HID mode and reconnect via USB.')
    else:
        return True

if __name__ == "__main__":
    yscale = 1.0
    yoffset = 0.0
    divfactor = {
        "m": 1000,  # milli
        "u": 1000000,  # micro
        "n": 1000000000,  # nano
    }
    #dev = usb.core.find(idVendor=0x5345, idProduct=0x1234)
    if initialize():
        # print(dev)
        dev.set_configuration()
        print(send('*IDN?').tobytes().decode('utf-8'))

        yscale, yoffset, header = readYScaleAndOffsetFromHeader()
        print(header)
        print(header["TIMEBASE"])
        print(header["SAMPLE"])
        print(header["CHANNEL"][0])
        xscale = float(header["TIMEBASE"]["SCALE"][0:-2]) / \
                 divfactor.get(header["TIMEBASE"]["SCALE"][-2], 1)
        print("XSCALE")
        print(xscale)
        xpoints = np.linspace(-6 * xscale, 6 * xscale, 300)
        print(header["CHANNEL"][1])
        print(header["DATATYPE"])
        print(header["RUNSTATUS"])
        print(header["IDN"])
        print(header["MODEL"])
        print(header["Trig"])
        #fig, ax = plt.subplots()
        fig, scopescreen = plt.subplots()
        plt.ylim(yscale,-1.0*yscale)




        i=0
        def update(frame):
            scopescreen.cla()
            global i, yscale, yoffset

            if(frame%10 == 0):
                yscale, yoffset, _ = readYScaleAndOffsetFromHeader()
                #print("new offset")
                #plt.ylim(yscale, -1.0 * yscale)

            i+=1
            data = get_data(1, yscale, yoffset)

            scopescreen.set(xlabel='time (s)', ylabel='voltage (V)', title='HDS2202(S)-DATA-AQC')
            scopescreen.grid(linestyle=':')
            plt.ylim(-4.0 * yscale, 4.0* yscale)
           #dev.reset()
            for i in range(0, len(data[1])):
                data[1][i] = abs(data[1][i])
            # Put data in a figure
            #fig, scopescreen = plt.subplots()
            scopescreen.plot(xpoints, data[0])#, xerr=0, yerr=data[1])



        ani = animation.FuncAnimation(fig=fig, func=update, frames=20, interval=500) #20 fps
        #ani = animation.FuncAnimation(fig=fig, func=update, fargs=(dev, ), frames=20, interval=500)  # 20 fps

        plt.show()