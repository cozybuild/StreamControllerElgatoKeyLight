# Import StreamController modules
from src.backend.PluginManager.ActionBase import ActionBase

import os
import gi
import threading
import time
import json

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

import requests
from gi.repository import Gtk, Adw


class Core(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lm = self.plugin_base.locale_manager

        self.plugin_base.backend.on_light_state_changed.subscribe(self.update_icon)

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

        _current_brightness = max(self.supported_lights["ElgatoKeyLight"]["min_brightness"], min(value, self.supported_lights["ElgatoKeyLight"]["max_brightness"]))

        settings["brightness"] = int(_current_brightness)

        self.plugin_base.set_settings(settings)
        self.plugin_base.backend.on_brightness_changed.emit()

        data = self.get_light_data()
        data["lights"][0]["brightness"] = value

        threading.Thread(target=self.update_light, args=[data], daemon=True, name="update_light").start()

    @property
    def current_temperature(self):
        settings = self.plugin_base.get_settings()
        return settings.get("temperature") or self.supported_lights["ElgatoKeyLight"]["min_temperature"]

    @current_temperature.setter
    def current_temperature(self, value):
        settings = self.plugin_base.get_settings()

        _current_temperature = max(self.supported_lights["ElgatoKeyLight"]["min_temperature"], min(value, self.supported_lights["ElgatoKeyLight"]["max_temperature"]))

        settings["temperature"] = int(_current_temperature)

        self.plugin_base.set_settings(settings)
        self.plugin_base.backend.on_temperature_changed.emit()

        data = self.get_light_data()
        data["lights"][0]["temperature"] = value

        threading.Thread(target=self.update_light, args=[data], daemon=True, name="update_light").start()

    def on_ready(self) -> None:
        self.update_icon()

    def get_config_rows(self) -> list:
        self.ip_entry = Adw.EntryRow(title=self.plugin_base.locale_manager.get("actions.ip_entry.title"), input_purpose=Gtk.InputPurpose.FREE_FORM)
        self.ip_entry.connect("notify::text", self.on_ip_address_changed)

        self.connection_banner = Adw.Banner()
        self.connection_banner.set_revealed(True)

        self.banner_is_visible = True
        self.load_default_config()

        return [self.ip_entry, self.connection_banner]

    def set_banner_connection_info(self) -> None:
        if not self.banner_is_visible:
            return

        if self.running_requests > 0:
            self.connection_banner.set_title(self.plugin_base.locale_manager.get("actions.connection_banner.loading"))
        elif self.is_connected:
            self.connection_banner.set_title(self.plugin_base.locale_manager.get("actions.connection_banner.connected"))
        else:
            self.connection_banner.set_title(self.plugin_base.locale_manager.get("actions.connection_banner.not_connected"))

    def modify_brightness(self, amount: int):
        settings = self.plugin_base.get_settings()
        data = self.get_light_data()
        new_brightness = data["lights"][0]["brightness"] + amount
        self.current_brightness = new_brightness

    def modify_temperature(self, amount: int):
        settings = self.plugin_base.get_settings()
        data = self.get_light_data()
        new_temperature = data["lights"][0]["temperature"] + amount
        self.current_temperature = new_temperature

    def toggle_light(self):
        settings = self.plugin_base.get_settings()
        data = self.get_light_data()

        data["lights"][0]["on"] ^= 1
        settings["light_active"] = data["lights"][0]["on"] 

        self.plugin_base.set_settings(settings)
        self.plugin_base.backend.on_light_state_changed.emit()
        self.update_light(data)

    def load_default_config(self):
        settings = self.plugin_base.get_settings()
        ip_address = settings.get("ip_address")

        if ip_address:
            self.ip_entry.set_text(ip_address)

    def on_ip_address_changed(self, entry: Adw.EntryRow, text):
        settings = self.plugin_base.get_settings()
        settings["ip_address"] = entry.get_text()
        self.plugin_base.set_settings(settings)

    def update_icon(self):
        settings = self.plugin_base.get_settings()
        if settings.get("light_active") == 1:
            icon_path = os.path.join(self.plugin_base.PATH, "assets", "ring_light_on.png")
        else:
            icon_path = os.path.join(self.plugin_base.PATH, "assets", "ring_light_off.png")
        self.set_media(media_path=icon_path, size=0.75)


    def get_light_data(self):
        settings = self.plugin_base.get_settings()
        ip_address = settings.get("ip_address")
        url = f"http://{ip_address}:9123/elgato/lights"
        try:
            r = requests.get(url)
            return json.loads(r.text)
        except:
            return "Failed to get lights"


    def update_light(self, data):
        settings = self.plugin_base.get_settings()
        ip_address = settings.get("ip_address")
        url = f"http://{ip_address}:9123/elgato/lights"

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
