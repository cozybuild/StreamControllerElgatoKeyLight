# Import StreamController modules
from gi.repository import Gtk, Adw
from ipaddress import ip_address
from src.backend.PluginManager.ActionBase import ActionBase

import os
import gi
import threading
import time
import json
import requests

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")


class Core(ActionBase):

    data = {}

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
                "min_k_temperature": 2900,
                "max_k_temperature": 7000,
            }
        }

        self.json_data = {
            "numberOfLights": 1,
            "lights": [
                {
                    "on": 0,
                    "brightness": 1,
                    "temperature": 143
                }
            ]
        }

        self.banner_is_visible = False

        self._is_connected = False
        self._connection_error = ""
        self._last_request_number = 0
        self._running_requests = 0
        
    def set_property(self, key, value):
        match key:
            case "brightness":
                self.plugin_base.backend.on_brightness_changed.emit()
                #self.json_data["lights"][0][key] = max(1, min(self.current_brightness + value, 100))
                Core.data[self.get_settings().get("ip_address")]["lights"][0][key] = value

            case "temperature":
                self.plugin_base.backend.on_temperature_changed.emit()
                #self.json_data["lights"][0][key] = max(143, min(self.current_temperature + value, 344))
                Core.data[self.get_settings().get("ip_address")]["lights"][0][key] = value
            case "on":
                Core.data[self.get_settings().get("ip_address")]["lights"][0][key] = 1 - Core.data[self.get_settings().get("ip_address")]["lights"][0][key]
            case _:
                print("No actions passed")

        self._async_send()
    
    def _async_send(self):
        threading.Thread(target=self._send_to_api,
                         daemon=True,
                         name="_send_to_api").start()

    def _send_to_api(self):
        ip_address = self.get_settings().get("ip_address")
        payload = Core.data[ip_address].copy()
        url = f"http://{ip_address}:9123/elgato/lights"
        try:
            r = requests.put(url, json=payload, timeout=10)
            #self.update_icon()
            self.plugin_base.backend.on_light_state_changed.emit()

        except:
            print(f"[Error]: Couldnt Sent update, request_body={payload}")

    def _get_from_api(self,ip):
        url = f"http://{ip}:9123/elgato/lights"
        try:
            r = requests.get(url,timeout=10)
            return r.json()
        except:
            print("[Error]: Couldnt Sent update")
            return None

    def _add_data_dictonary(self, ip):
        if ip in Core.data:
            return 0
        Core.data[ip] = self._get_from_api(ip)
        return None
    
    def _get_data_dictonary(self, ip):
        if ip not in Core.data:
            return {}
        return data[ip]

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
    def current_status(self):
        ip = self.get_settings().get("ip_address")
        if ip not in Core.data:
            self._add_data_dictonary(ip)
        cur_status = Core.data[ip]["lights"][0]["on"]
        return cur_status or 0

    @property
    def current_brightness(self):
        ip = self.get_settings().get("ip_address")
        if ip not in Core.data :
            self._add_data_dictonary(ip)

        cur_status = Core.data[ip]["lights"][0]["brightness"]
        return cur_status or 1

    @property
    def current_temperature(self):
        ip = self.get_settings().get("ip_address")
        if ip not in Core.data:
            self._add_data_dictonary(ip)
        cur_status = Core.data[ip]["lights"][0]["temperature"]
        return cur_status or 143

    @property
    def current_k_temperature(self):
        real_min, real_max = self.supported_lights["ElgatoKeyLight"]["min_temperature"],self.supported_lights["ElgatoKeyLight"]["max_temperature"]
        shown_min, shown_max =  self.supported_lights["ElgatoKeyLight"]["max_k_temperature"],self.supported_lights["ElgatoKeyLight"]["min_k_temperature"]
        real_value = self.current_temperature
        return ((real_value - real_min) / (real_max - real_min)) * (shown_max - shown_min) + shown_min

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
        new_brightness = int(self.get_light_data()["brightness"] or 0) + amount
        self.current_brightness = new_brightness

    def modify_temperature(self, amount: int):
        new_temperature = int(self.get_light_data()["temperature"] or 0) + amount
        self.current_temperature = new_temperature

    def toggle_light(self):
        status = self.get_light_data()["on"]
        status = 1 - status
        self.current_status = status

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
            self.preselect_device_by_ip(saved_ip_address)
            self.ip_address = saved_ip_address

    def preselect_device_by_ip(self,ip):
        base_devices = self.plugin_base.backend.get_devices()
        for index, key in enumerate(base_devices):
            if base_devices[key].ip_address == ip:
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

        self._add_data_dictonary(ip_by_index)

        #threading.Thread(target=self.update_light, daemon=True,
        #                 name="update_light").start()

    def update_icon(self):
        if self.current_status == 1:
            icon_path = os.path.join(
                self.plugin_base.PATH, "assets", "ring_light_on.png")
        else:
            icon_path = os.path.join(
                self.plugin_base.PATH, "assets", "ring_light_off.png")
        self.set_media(media_path=icon_path, size=0.75)


    # TODO: Fetch data from light (singleton)

    def get_light_data(self):
        ip_address = self.get_settings().get("ip_address")
        url = f"http://{ip_address}:9123/elgato/lights"
        try:
            r = requests.get(url)
            return json.loads(r.text)["lights"][0] 
        except:
            return "Failed to get lights"

    def update_light(self,_is_light_active,_brightness,_temperature):

        ip_address = self.get_settings().get("ip_address")
        url = f"http://{ip_address}:9123/elgato/lights"

        if _is_light_active is None:
            _is_light_active = self.current_status

        data = {
            "numberOfLights": 1,
            "lights": [
                {
                    "on": _is_light_active, 
                    "brightness": _brightness or self.current_brightness,
                    "temperature": _temperature or self.current_temperature
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
