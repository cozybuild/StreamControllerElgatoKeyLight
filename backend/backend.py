from streamcontroller_plugin_tools import BackendBase

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")


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


class Backend(BackendBase):
    def __init__(self):
        super().__init__()
        self.on_brightness_changed = Event()
        self.on_temperature_changed = Event()
        self.on_light_state_changed = Event()

backend = Backend()
