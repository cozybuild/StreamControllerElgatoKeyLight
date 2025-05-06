# Import StreamController modules
from gi.repository import Gtk, Adw
import requests
from ipaddress import ip_address
from src.backend.PluginManager.ActionBase import ActionBase

import os
import gi
import threading
import time
import json

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")


class Core(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lm = self.plugin_base.locale_manager

        self.plugin_base.backend.on_light_state_changed.subscribe(
            self.update_icon)
        self.plugin_base.backend.on_device_added.subscribe(
            self.update_device_list)

        self.supported_lights = {
            "ElgatoKeyLight": {
                "name": "Elgato Key Light",
                "min_brightness": 1,
                "max_brightness": 100,
                "min_temperature": 143,
                "max_temperature": 344,
            }
        }

        self.banner_is_visible = False

        self._is_connected = False
        self._connection_error = ""
        self._last_request_number = 0
        self._running_requests = 0

    @property
    def running_requests(self):
        return self._running_requests

    @running_requests.setter
    def running_requests(self, value):
        self._running_requests = value
        self.set_banner_connection_info()

    @property
    def is_connected(self):
        return self._is_connected

    @is_connected.setter
    def is_connected(self, value):
        self._is_connected = value
        self.set_banner_connection_info()

    @property
    def current_brightness(self):
        settings = self.plugin_base.get_settings()
            
        return settings.get("brightness") or self.supported_lights["ElgatoKeyLight"]["min_brightness"]

    @current_brightness.setter
    def current_brightness(self, value):
        settings = self.plugin_base.get_settings()

        _current_brightness = max(self.supported_lights["ElgatoKeyLight"]["min_brightness"], min(
            value, self.supported_lights["ElgatoKeyLight"]["max_brightness"]))

        settings["brightness"] = int(_current_brightness)

        self.plugin_base.set_settings(settings)
        self.plugin_base.backend.on_brightness_changed.emit()
        threading.Thread(target=self.update_light, daemon=True,
                         name="update_light").start()

    @property
    def current_temperature(self):
        settings = self.plugin_base.get_settings()
        return settings.get("temperature") or self.supported_lights["ElgatoKeyLight"]["min_temperature"]

    @current_temperature.setter
    def current_temperature(self, value):
        settings = self.plugin_base.get_settings()

        _current_temperature = max(self.supported_lights["ElgatoKeyLight"]["min_temperature"], min(
            value, self.supported_lights["ElgatoKeyLight"]["max_temperature"]))

        settings["temperature"] = int(_current_temperature)

        self.plugin_base.set_settings(settings)
        self.plugin_base.backend.on_temperature_changed.emit()
        threading.Thread(target=self.update_light, daemon=True,
                         name="update_light").start()

    def on_ready(self) -> None:
        self.load_default_config()
        self.update_icon()

    def update_device_list(self):
        if not hasattr(self, "registered_devices"):
            return

        print(self.registered_devices)
        self.registered_devices.splice(
            0, self.registered_devices.get_n_items())
        for device in self.plugin_base.backend.get_devices():
            self.registered_devices.append(str(device))

    def get_config_rows(self) -> list:
        self.add_new_ip_entry = Adw.EntryRow(title=self.plugin_base.locale_manager.get(
            "actions.add_ip_entry.title"), input_purpose=Gtk.InputPurpose.FREE_FORM)
        self.add_light_button = Adw.ButtonRow(
            title=self.plugin_base.locale_manager.get("actions.add_light_button.title"))

        # Disable button until we have a working connection
        self.add_light_button

        self.add_light_button.connect("activated", self.on_ip_address_added)

        self.registered_devices = Gtk.StringList()
        for device in self.plugin_base.backend.get_devices():
            self.registered_devices.append(str(device))

        self.device_list = Adw.ComboRow(title=self.plugin_base.locale_manager.get(
            "actions.device_list.title"), model=self.registered_devices)
        self.device_list.connect("notify::selected", self.set_ip_address)

        self.connection_banner = Adw.Banner()
        self.connection_banner.set_revealed(True)

        self.banner_is_visible = True

        self.load_default_config()

        return [self.add_new_ip_entry, self.add_light_button, self.device_list, self.connection_banner]

    def set_banner_connection_info(self) -> None:
        if not self.banner_is_visible:
            return

        if self.running_requests > 0:
            self.connection_banner.set_title(
                self.plugin_base.locale_manager.get("actions.connection_banner.loading"))
        elif self.is_connected:
            self.connection_banner.set_title(
                self.plugin_base.locale_manager.get("actions.connection_banner.connected"))
        else:
            self.connection_banner.set_title(self.plugin_base.locale_manager.get(
                "actions.connection_banner.not_connected"))

    def modify_brightness(self, amount: int):
        settings = self.plugin_base.get_settings()
        new_brightness = int(settings.get("brightness") or 0) + amount
        self.current_brightness = new_brightness

    def modify_temperature(self, amount: int):
        settings = self.plugin_base.get_settings()
        new_temperature = int(settings.get("temperature") or 0) + amount
        self.current_temperature = new_temperature

    def toggle_light(self):
        settings = self.plugin_base.get_settings()

        if settings.get("light_active") == 0:
            settings["light_active"] = 1
        else:
            settings["light_active"] = 0

        self.plugin_base.set_settings(settings)
        self.plugin_base.backend.on_light_state_changed.emit()
        self.update_light()

    def load_default_config(self):
        # Fallback for old global settings
        global_settings = self.plugin_base.get_settings()
        migrate_global_address_to_local_address = global_settings.get(
            "ip_address")

        settings = self.get_settings()

        if migrate_global_address_to_local_address:
            settings["ip_address"] = migrate_global_address_to_local_address
            del global_settings["ip_address"]
            self.plugin_base.set_settings(global_settings)
            print("Migrating global settings")
            self.set_settings(settings)

        saved_ip_address = settings.get("ip_address")

        if saved_ip_address:
            print("Saved ip address in config ", saved_ip_address)

            self.plugin_base.backend.register_new_device(
                saved_ip_address, saved_ip_address)
            self.preselect_device_by_ip()
            self.ip_address = saved_ip_address

    def preselect_device_by_ip(self):
        base_devices = self.plugin_base.backend.get_devices()
        for index, key in enumerate(base_devices):
            if base_devices[key].ip_address == ip_address:
                self.device_list.set_selected(index)
                break

    def on_ip_address_added(self, entry):
        new_ip_address = self.add_new_ip_entry.get_text()

        self.plugin_base.backend.register_new_device(
            new_ip_address, new_ip_address)
        self.device_list.set_selected(
            self.registered_devices.get_n_items() - 1)
        self.set_ip_address(self.device_list)

    def set_ip_address(self, entry: Adw.EntryRow, *args):
        settings = self.get_settings()

        ip_by_index = list(self.plugin_base.backend.get_devices().values())[
            entry.get_selected()].ip_address

        settings["ip_address"] = ip_by_index

        self.ip_address = ip_by_index

        self.set_settings(settings)
        threading.Thread(target=self.update_light, daemon=True,
                         name="update_light").start()

    def update_icon(self):
        settings = self.plugin_base.get_settings()
        if settings.get("light_active") == 1:
            icon_path = os.path.join(
                self.plugin_base.PATH, "assets", "ring_light_on.png")
        else:
            icon_path = os.path.join(
                self.plugin_base.PATH, "assets", "ring_light_off.png")
        self.set_media(media_path=icon_path, size=0.75)

    # TODO: Fetch data from light (singleton)

    def get_light_data(self):
        ip_address = settings.get("ip_address")
        url = f"http://{ip_address}:9123/elgato/lights"
        try:
            r = requests.get(url)
            return json.loads(r.text()[0]) 
        except:
            return "Failed to get lights"

    def update_light(self):
        settings = self.get_settings()
        global_settings = self.plugin_base.get_settings()
        ip_address = settings.get("ip_address")
        url = f"http://{ip_address}:9123/elgato/lights"

        data = {
            "numberOfLights": 1,
            "lights": [
                {
                    "on": global_settings.get("light_active"),
                    "brightness": self.current_brightness,
                    "temperature": self.current_temperature
                }
            ]
        }

        request_number = self._last_request_number + 1
        self.running_requests += 1
        self._last_request_number = request_number

        try:
            requests.put(url, json=data, timeout=10)

            self.running_requests -= 1
            if request_number != self._last_request_number:
                return

            self.update_icon()
            self.is_connected = True
            self._last_request_number = time.time()
        except BaseException as e:
            self.running_requests -= 1

            if request_number != self._last_request_number:
                return

            self._connection_error = str(e)
            self.is_connected = False
