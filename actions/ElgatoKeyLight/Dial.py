# Import StreamController modules
from src.backend.DeckManagement.InputIdentifier import Input, InputEvent
from enum import Enum

from .Core import Core

# Import gtk modules - used for the config rows
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

class DialProperty(Enum):
    Brightness = 0
    Temperature = 1

class Dial(Core):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selected_step_size = 1
        self.current_dial_selection = 0

    def on_ready(self) -> None:
        self.load_local_saved_config()
        self.update_icon()

    def get_config_rows(self) -> list:
        parent_entries = super().get_config_rows()

        self.property_selection = Gtk.StringList()

        for property in DialProperty:
            self.property_selection.append(property.name)

        self.step_size = Adw.SpinRow.new_with_range(1, 10, 1)
        self.step_size.set_title(self.plugin_base.locale_manager.get("actions.step_size.title"))
        self.step_size.set_value(self.selected_step_size)

        self.dial_selection = Adw.ComboRow(title=self.plugin_base.locale_manager.get("actions.dial_selection.title"), model=self.property_selection)
        self.dial_selection.set_selected(self.current_dial_selection)

        self.step_size.connect("notify::text", self.on_step_size_changed)
        self.dial_selection.connect("notify::selected", self.on_dial_selection_changed)

        return parent_entries + [self.dial_selection, self.step_size]

    def on_step_size_changed(self, spinner: Adw.SpinRow, *args):
        self.save_settings()

    def on_dial_selection_changed(self, spinner: Adw.ComboRow, *args):
        self.save_settings()

    def load_local_saved_config(self):
        local_settings = self.get_settings()

        self.selected_step_size = local_settings.get("step_size") or 1
        self.current_dial_selection = local_settings.get("current_dial_selection")


    def save_settings(self):
        local_settings = self.get_settings()

        self.selected_step_size = int(self.step_size.get_value())
        self.current_dial_selection = int(self.dial_selection.get_selected())

        local_settings["step_size"] = self.selected_step_size
        local_settings["current_dial_selection"] = self.current_dial_selection
        self.set_settings(local_settings)

    def event_callback(self, event: InputEvent, data: dict) -> None:
            if event == Input.Key.Events.DOWN or event == Input.Dial.Events.DOWN:
                self.toggle_light()
                return

            new_value = 0
            if str(event) == str(Input.Dial.Events.TURN_CW):
                new_value = +self.selected_step_size
            if str(event) == str(Input.Dial.Events.TURN_CCW):
                new_value = -self.selected_step_size

            is_brightness = self.current_dial_selection == DialProperty.Brightness.value
            if is_brightness:
                self.modify_brightness(new_value)
            else:
                self.modify_temperature(new_value)

    def on_key_down(self) -> None:
        self.toggle_light()
