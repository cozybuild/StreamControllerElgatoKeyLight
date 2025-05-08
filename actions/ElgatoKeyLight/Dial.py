# Import StreamController modules
from gi.repository import Gtk, Adw
from src.backend.DeckManagement.InputIdentifier import Input, InputEvent
from enum import Enum

from .Core import Core

# Import gtk modules - used for the config rows
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")


class DialProperty(Enum):
    Brightness = 0
    Temperature = 1


class ToggleProperty(Enum):
    ToggleLightOnOff = 0
    ChangeBrightnessTemperature = 1


class Dial(Core):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.selected_step_size = 1
        self.current_dial_selection = 0
        self.current_toggle_selection = 0

    def on_ready(self) -> None:
        self.load_local_saved_config()
        self.update_icon()
        self.update_labels()

        self.plugin_base.backend.on_brightness_changed.subscribe(
            self.update_labels)
        self.plugin_base.backend.on_temperature_changed.subscribe(
            self.update_labels)

    def get_config_rows(self) -> list:
        parent_entries = super().get_config_rows()
    
        self.toggle_property_selection = Gtk.StringList()
        self.toggle_property_selection.append(
            self.plugin_base.locale_manager.get("actions.toggle_selection.light_on_off"))
        self.toggle_property_selection.append(self.plugin_base.locale_manager.get(
            "actions.toggle_selection.brightness_temperature"))

        self.property_selection = Gtk.StringList()

        for property in DialProperty:
            self.property_selection.append(property.name)

        self.step_size = Adw.SpinRow.new_with_range(1, 10, 1)
        self.step_size.set_title(
            self.plugin_base.locale_manager.get("actions.step_size.title"))
        self.step_size.set_value(self.selected_step_size)

        self.dial_selection = Adw.ComboRow(title=self.plugin_base.locale_manager.get(
            "actions.dial_selection.title"), model=self.property_selection)
        self.dial_selection.set_selected(self.current_dial_selection)

        self.toggle_selection = Adw.ComboRow(title=self.plugin_base.locale_manager.get(
            "actions.toggle_selection.title"), model=self.toggle_property_selection)
        self.toggle_selection.set_selected(self.current_toggle_selection)

        self.step_size.connect("notify::text", self.on_step_size_changed)
        self.dial_selection.connect(
            "notify::selected", self.on_dial_selection_changed)
        self.toggle_selection.connect(
            "notify::selected", self.on_toggle_selection_changed)

        return parent_entries + [self.dial_selection, self.toggle_selection, self.step_size]

    def on_step_size_changed(self, spinner: Adw.SpinRow, *args):
        self.selected_step_size = int(self.step_size.get_value())
        self.save_settings()

    def on_dial_selection_changed(self, spinner: Adw.ComboRow, *args):
        self.current_dial_selection = int(self.dial_selection.get_selected())
        self.save_settings()

    def on_toggle_selection_changed(self, spinner: Adw.ComboRow, *args):
        self.current_toggle_selection = int(
            self.toggle_selection.get_selected())
        self.save_settings()

    def load_local_saved_config(self):
        local_settings = self.get_settings()

        self.selected_step_size = local_settings.get("step_size") or 1
        self.current_dial_selection = local_settings.get(
            "current_dial_selection") or 0
        self.current_toggle_selection = local_settings.get(
            "current_toggle_selection") or 0

    def save_settings(self):
        local_settings = self.get_settings()

        local_settings["step_size"] = self.selected_step_size
        local_settings["current_dial_selection"] = self.current_dial_selection
        local_settings["current_toggle_selection"] = self.current_toggle_selection
        self.set_settings(local_settings)

    def event_callback(self, event: InputEvent, data: dict) -> None:
        if event == Input.Key.Events.DOWN or event == Input.Dial.Events.DOWN:
            self.on_key_down()
            return

        new_value = 0
        if str(event) == str(Input.Dial.Events.TURN_CW):
            new_value = +self.selected_step_size
        if str(event) == str(Input.Dial.Events.TURN_CCW):
            new_value = -self.selected_step_size

        is_brightness = self.current_dial_selection == DialProperty.Brightness.value
        if is_brightness:
            self.set_property("brightness",new_value)
        else:
            self.set_property("temperature",new_value)
        
        self.update_labels()

    def toggle_brightness_temperature(self):
        if self.current_dial_selection == DialProperty.Brightness.value:
            self.current_dial_selection = DialProperty.Temperature.value
        else:
            self.current_dial_selection = DialProperty.Brightness.value

        self.save_settings()

    def update_labels(self):
        if self.current_dial_selection == DialProperty.Brightness.value:
            self.set_top_label(text=self.plugin_base.locale_manager.get(
                "actions.current_brightness.title"))
            self.set_bottom_label(text=self.plugin_base.locale_manager.get(
                "actions.current_brightness.value") % self.current_brightness)
        else:
            self.set_top_label(text=self.plugin_base.locale_manager.get(
                "actions.current_temperature.title"))
            self.set_bottom_label(text=self.plugin_base.locale_manager.get(
                "actions.current_temperature.value") % int(self.current_k_temperature))

    def on_key_down(self) -> None:
        if self.current_toggle_selection == ToggleProperty.ToggleLightOnOff.value:
            self.set_property("on",None)
        else:
            self.toggle_brightness_temperature()
