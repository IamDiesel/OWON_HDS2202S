class OWON_Points:
    """
    class representation of channel 1 / 2 data of the OWON Oscilloscope
    """

    def __init__(self, y_vals=None, x_vals=None, channel=None, yscale=None, yoffset=None, xscale=None, is_on=False):
        self._channel = channel
        self._y_vals = y_vals
        self._yscale = yscale
        self._yoffset = yoffset
        self._xscale = xscale
        self._xvals = x_vals
        self._is_on = is_on

    def get_Y(self):
        return self._y_vals

    def get_X(self):
        return self._xvals

    def get_channel(self):
        return self._channel

    def get_yscale(self):
        return self._yscale

    def get_yoffset(self):
        return self._yoffset

    def get_xscale(self):
        return self._xscale

    def get_is_on(self):
        return self._is_on


