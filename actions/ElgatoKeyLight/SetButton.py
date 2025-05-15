from gi.repository import Adw
from .Core import Core

# Import gtk modules - used for the config rows
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")


class SetButton(Core):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_ready(self) -> None:
        local_settings = self.get_settings()

        self._custom_brightness = local_settings.get(
            "custom_brightness") or self.supported_lights["ElgatoKeyLight"]["min_brightness"]
        self._custom_temperature = local_settings.get(
            "custom_temperature") or self.supported_lights["ElgatoKeyLight"]["min_temperature"]
        self._live_update = local_settings.get("live_update") or False

        self.update_icon()

    @property
    def custom_brightness(self):
        return self._custom_brightness

    @custom_brightness.setter
    def custom_brightness(self, value):
        self._custom_brightness = value
        local_settings = self.get_settings()
        local_settings["custom_brightness"] = int(value)
        self.set_settings(local_settings)

    @property
    def custom_temperature(self):
        return self._custom_temperature

    @custom_temperature.setter
    def custom_temperature(self, value):
        self._custom_temperature = value
        local_settings = self.get_settings()
        local_settings["custom_temperature"] = int(value)
        self.set_settings(local_settings)

    @property
    def live_update_active(self):
        return self._live_update

    @live_update_active.setter
    def live_update_active(self, value):
        self._live_update = value
        local_settings = self.get_settings()
        local_settings["live_update"] = int(value)
        self.set_settings(local_settings)

    def get_config_rows(self) -> list:
        parent_entries = super().get_config_rows()

        self.live_update = Adw.SwitchRow.new()
        self.live_update.set_title(self.lm.get("actions.live_update.title"))
        self.live_update.set_active(self.live_update_active)
        self.live_update.connect("notify::active", self.on_live_update_changed)

        self.brightness_entry = Adw.SpinRow.new_with_range(
            self.supported_lights["ElgatoKeyLight"]["min_brightness"], self.supported_lights["ElgatoKeyLight"]["max_brightness"], 1)
        self.brightness_entry.set_title(
            self.plugin_base.locale_manager.get("actions.brightness_entry.title"))
        self.brightness_entry.set_value(self.custom_brightness)

        self.temperature_entry = Adw.SpinRow.new_with_range(
            self.supported_lights["ElgatoKeyLight"]["min_temperature"], self.supported_lights["ElgatoKeyLight"]["max_temperature"], 1)
        self.temperature_entry.set_title(
            self.plugin_base.locale_manager.get("actions.brightness_entry.title"))
        self.temperature_entry.set_value(self.custom_temperature)

        self.brightness_entry.connect(
            "notify::value", self.on_brightness_changed)
        self.temperature_entry.connect(
            "notify::value", self.on_temperature_changed)
        return parent_entries + [self.live_update, self.brightness_entry, self.temperature_entry]

    def on_live_update_changed(self, switch: Adw.SwitchRow, *args):
        self.live_update_active = switch.get_active()

        if self.live_update_active:
            self.push_light_properties()

    def on_brightness_changed(self, spinner: Adw.SpinRow, *args):
        self.custom_brightness = spinner.get_value()

        if self.live_update_active:
            self.current_brightness = self.custom_brightness

    def on_temperature_changed(self, spinner: Adw.SpinRow, *args):
        self.custom_temperature = spinner.get_value()
        if self.live_update_active:
            self.current_temperature = self.custom_temperature

    def on_key_down(self) -> None:
        self.push_light_properties()

    def push_light_properties(self):
        self.set_property("brightness",self.custom_brightness)
        self.set_property("temperature",self.custom_temperature)

        if self.current_status == 0:
            self.set_property("on",None)
            return
