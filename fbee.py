import socket
import threading
from datetime import datetime

GET_ALL_DEVICES="81"
SET_SWITCH_STATE="82"
GET_SWITCH_STATE="85"

ALL_DEVICES_RESP=0x01
SWITCH_STATUS=0x07
ACK=0x29

def fmt(v, l):
    v = hex(v)
    if len(v) > 2 and v[0:2] == "0x":
        v = v[2:]
    v = v.zfill(l)
    return v[:l]

class FBee():
    def __init__(self, host, port, sn, device_callback = None):
        self.connected = False
        self.host = host
        self.port = port
        self.sn = bytes.fromhex(sn[6:8] + sn[4:6] + sn[2:4] + sn[0:2])
        self.devices = {}
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.s.settimeout(1)
        self.device_callback = device_callback
        self.async_thread = None

    def connect(self):
        if not self.connected:
            self.connected = True
            self.s.connect((self.host, self.port))

    def send_data(self, data):
        data = bytes.fromhex(data)
        b = self.sn + b"\xFE" + data
        l = (len(b) + 2).to_bytes(2, byteorder='little')
        self.s.send(l + b)

    def recv(self):
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
                    device.set_state(state)
                    device.set_name(name)
                    newdev = False
                else:
                    device = self.devices[hex(short) + hex(ep)] = FBeeSwitch(self, name, short, ep, state)
                    newdev = True

                if self.device_callback != None:
                    self.device_callback(device, newdev)
            elif resp == SWITCH_STATUS:
                short=int.from_bytes(b[0:2], byteorder='little')
                ep=b[2]
                state = b[3]
                key = hex(short) + hex(ep)
                if key in self.devices:
                    device = self.devices[key]
                    self.devices[key].set_state(state)
                    newdev = False
                else:
                    device = self.devices[key] = FBeeSwitch(self, "[Unknown] " + hex(short) + " " + hex(ep), short, ep, state)
                    newdev = True

                if self.device_callback != None:
                    self.device_callback(device, newdev)

    def async_read(self, poll_interval):
        poll_interval = int(poll_interval)
        self.s.settimeout(poll_interval)
        next_refresh = 0
        while True:
            now = datetime.now()
            now = (now-datetime(1970,1,1)).total_seconds()
            if next_refresh <= now:
                self.refresh_devices()
                next_refresh = now + poll_interval
            self.s.settimeout(next_refresh - now)
            try:
                self.recv()
            except socket.timeout as e:
                pass

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

    def start_async_read(self, poll_interval):
        self.async_thread = threading.Thread(target=self.async_read, args=(poll_interval,))
        self.async_thread.start()
        return self.async_thread

    def close(self):
        self.s.close()

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

    def poll_state(self):
        self.fbee.poll_state(self.short, self.ep)

    def push_state(self, state):
        short = fmt(self.short, 4)
        ep = fmt(self.ep, 2)
        if type(state) != int:
            state = int(state, 16)
        self.fbee.send_data(SET_SWITCH_STATE + "0D02" + short[2:4] + short[0:2] + ("0" * 12) + ep + "0000" + fmt(state, 2))
        self.fbee.safe_recv()
