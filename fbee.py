import socket
import threading
from datetime import datetime

GET_ALL_DEVICES="81"
SET_SWITCH_STATE="82"
GET_SWITCH_STATE="85"

ALL_DEVICES_RESP=0x01
SWITCH_STATUS=0x07
ACK=0x29

STATE_NO_CHANGE=0
STATE_NEW_DEV=1
STATE_NEW_STATE=2

def fmt(v, l):
    v = hex(v)
    if len(v) > 2 and v[0:2] == "0x":
        v = v[2:]
    v = v.zfill(l)
    return v[:l]

class FBee():
    def __init__(self, host, port, sn, device_callbacks = []):
        self.host = host
        self.port = port
        self.sn = bytes.fromhex(sn[6:8] + sn[4:6] + sn[2:4] + sn[0:2])
        self.devices = {}
        self.device_callbacks = device_callbacks
        self.m = threading.Lock()
        self.poll_interval = 60
        self.s = None
        self.async_thread = None

    def add_callback(self, callback):
        self.device_callbacks += callback

    def connect(self):
        if self.s == None:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            self.s.settimeout(1)
            self.s.connect((self.host, self.port))

    def send_data(self, data):
        data = bytes.fromhex(data)
        b = self.sn + b"\xFE" + data
        l = (len(b) + 2).to_bytes(2, byteorder='little')
        self.m.acquire()
        if self.s != None:
            try:
                self.s.send(l + b)
            except OSError:
                s.m.release()
                raise NotConnected
        else:
           self.m.release()
           raise NotConnected
        self.m.release()

    def recv(self):
        if self.s == None:
            raise NotConnected
        b = self.s.recv(2)
        if len(b) == 2:
            resp = b[0]
            b = self.s.recv(b[1])
            if resp == ALL_DEVICES_RESP:
                short=int.from_bytes(b[0:2], byteorder='little')
                ep=b[2]
                state = b[7]
                name=b[9:9+b[8]].decode()
                if name == "":
                    name = "[" + b[19:19+b[18]].decode() + "]"

                key = hex(short) + hex(ep)
                if key in self.devices:
                    device = self.devices[key]
                    oldstate = device.get_state()
                    oldname = device.get_name()
                    device.set_state(state)
                    device.set_name(name)
                    if oldstate == state and oldname == name:
                        state = STATE_NO_CHANGE
                    else:
                        state = STATE_NEW_STATE
                else:
                    device = self.devices[hex(short) + hex(ep)] = FBeeSwitch(self, name, short, ep, state)
                    state = STATE_NEW_DEV

                for callback in self.device_callbacks:
                    callback(device, state)
            elif resp == SWITCH_STATUS:
                short=int.from_bytes(b[0:2], byteorder='little')
                ep=b[2]
                state = b[3]
                key = hex(short) + hex(ep)
                if key in self.devices:
                    device = self.devices[key]
                    oldstate = device.get_state()
                    self.devices[key].set_state(state)
                    if oldstate == state:
                        state = STATE_NO_CHANGE
                    else:
                        state = STATE_NEW_STATE
                else:
                    device = self.devices[key] = FBeeSwitch(self, "[Unknown] " + hex(short) + " " + hex(ep), short, ep, state)
                    state = STATE_NEW_DEV

                for callback in self.device_callbacks:
                    callback(device, state)

    def async_read(self, poll_interval, disconnect_callback):
        poll_interval = int(poll_interval)
        self.s.settimeout(poll_interval)
        next_refresh = 0
        while True:
            now = datetime.now()
            now = (now-datetime(1970,1,1)).total_seconds()
            if next_refresh <= now:
                try:
                    self.refresh_devices()
                except NotConnected as e:
                    break
                next_refresh = now + poll_interval

            self.s.settimeout(next_refresh - now)
            try:
                self.recv()
            except socket.timeout as e:
                pass
            except OSError as e:
                break
        self.async_thread = None
        if disconnect_callback != None:
            disconnect_callback(self)

    def safe_recv(self):
        if self.async_thread != None:
            return
        while True:
            try:
                self.recv()
            except socket.timeout as e:
                break

    def refresh_devices(self):
        self.send_data(GET_ALL_DEVICES)
        self.safe_recv()
        return self.devices

    def get_devices(self):
        return self.devices

    def poll_state(self, short, ep):
        short = fmt(short, 4)
        ep = fmt(ep, 2)
        self.send_data(GET_SWITCH_STATE + "0002" + short[2:4] + short[0:2] + ("0" * 12) + ep + "0000")
        self.safe_recv()

    def get_device(self, short, ep):
        if type(short) != "int":
            short = int(short, 16)
        if type(ep) != "int":
            ep = int(ep, 16)
        key = hex(short) + hex(ep)
        if key not in self.devices:
            self.poll_state(short, ep)

        return self.devices[key]

    def start_async_read(self, poll_interval = None, disconnect_callback = None):
        if self.s == None:
            raise NotConnected
        if poll_interval != None:
            self.poll_interval = poll_interval
        if self.async_thread == None:
            self.async_thread = threading.Thread(target=self.async_read, args=(self.poll_interval,disconnect_callback))
            self.async_thread.start()
        return self.async_thread

    def close(self):
        if self.s != None:
            self.m.acquire()
            try:
                self.s.close()
            except:
                self.m.release()
                raise
            self.s = None
            self.m.release()


class FBeeSwitch():
    def __init__(self, fbee, name, short, ep, state):
        self.fbee = fbee
        self.name = name
        self.short = short
        self.ep = ep
        self.state = state

    def set_state(self, state):
        self.state = state

    def set_name(self, name):
        self.name = name

    def get_state(self):
        return self.state

    def get_name(self):
        return self.name

    def get_key(self):
        return hex(self.short) + hex(self.ep)

    def poll_state(self):
        self.fbee.poll_state(self.short, self.ep)

    def push_state(self, state):
        short = fmt(self.short, 4)
        ep = fmt(self.ep, 2)
        if type(state) != int:
            state = int(state, 16)
        self.fbee.send_data(SET_SWITCH_STATE + "0D02" + short[2:4] + short[0:2] + ("0" * 12) + ep + "0000" + fmt(state, 2))
        self.fbee.safe_recv()

class NotConnected(Exception):
    pass
