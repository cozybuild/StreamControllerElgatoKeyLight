# Import StreamController modules
from src.backend.PluginManager.ActionBase import ActionBase

import os
import gi
import threading

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

import requests
from gi.repository import Gtk, Adw


class Core(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.supported_lights = {
            "ElgatoKeyLight": {
                "name": "Elgato Key Light",
                "min_brightness": 1,
                "max_brightness": 100,
                "min_temperature": 143,
                "max_temperature": 344,
            }
        }

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
        threading.Thread(target=self.update_light, daemon=True, name="update_light").start()

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
        threading.Thread(target=self.update_light, daemon=True, name="update_light").start()

    def on_ready(self) -> None:
        self.update_icon()

    def get_config_rows(self) -> list:
        self.ip_entry = Adw.EntryRow(title=self.plugin_base.locale_manager.get("actions.ip_entry.title"), input_purpose=Gtk.InputPurpose.FREE_FORM)

        self.load_default_config()

        return [self.ip_entry]

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
        self.update_light()
        self.update_icon()

    def load_default_config(self):
        settings = self.plugin_base.get_settings()
        ip_address = settings.get("ip_address")

        if ip_address:
            self.ip_entry.set_text(ip_address)

    def on_ip_address_changed(self, entry: Adw.EntryRow, text):
        settings = self.plugin_base.get_settings()
        settings["ip_address"] = entry.get_text()
        self.plugin_base.set_settings(settings)
        threading.Thread(target=self.update_light, daemon=True, name="update_light").start()

    def update_icon(self):
        settings = self.plugin_base.get_settings()
        if settings.get("light_active") == 1:
            icon_path = os.path.join(self.plugin_base.PATH, "assets", "ring_light_on.png")
        else:
            icon_path = os.path.join(self.plugin_base.PATH, "assets", "ring_light_off.png")
        self.set_media(media_path=icon_path, size=0.75)


    # TODO: Fetch data from light (singleton)
    def get_light_data(self):
        url = ""
        try:
            r = requests.get(url)
            return r.text
        except:
            return "Failed to get lights"


    def update_light(self):
        settings = self.plugin_base.get_settings()
        ip_address = settings.get("ip_address")
        url = f"http://{ip_address}:9123/elgato/lights"

        data = {
        "numberOfLights": 1,
        "lights": [
                {
                    "on": settings.get("light_active"),
                    "brightness": self.current_brightness,
                    "temperature": self.current_temperature
                }
            ]
        }

        try:
            r = requests.put(url, json=data, timeout=10)
            print(r.text)
            self.update_icon()
        except ValueError:
            print("Failed to set lights ", ValueError)
