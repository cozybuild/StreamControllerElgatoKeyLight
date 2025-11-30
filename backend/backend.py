from streamcontroller_plugin_tools import BackendBase


class Event:
    def __init__(self):
        self.listeners = []

    def subscribe(self, listener):
        self.listeners.append(listener)

    def unsubscribe(self, listener):
        self.listeners.remove(listener)

    def emit(self, *args):
        for listener in self.listeners:
            listener(*args)


class Device:
    def __init__(self, ip_address: str, name: str):
        self.ip_address = ip_address
        self.name = name


class Backend(BackendBase):
    def __init__(self):
        super().__init__()
        self.on_brightness_changed = Event()
        self.on_temperature_changed = Event()
        self.on_light_state_changed = Event()
        self.on_device_added = Event()

        self.devices: dict[str, Device] = {}

    def register_new_device(self, device_ip: str, device_name: str):
        print("Registering new device: ", device_ip)

        if device_ip in self.devices:
            return

        self.devices[device_ip] = Device(device_ip, device_name)
        self.on_device_added.emit()

    def remove_device(self, device_ip: str):
        del self.devices[device_ip]
        self.on_device_removed.emit(device_ip)

    def get_devices(self) -> dict[str, Device]:
        return self.devices

    def is_device_in_list(self, device_ip: str) -> bool:
        return device_ip in self.devices


backend = Backend()
