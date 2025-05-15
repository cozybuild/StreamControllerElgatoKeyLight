from .Core import Core


class ToggleButton(Core):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_key_down(self) -> None:
        self.set_property("on",None)

    def on_ready(self):
        self.update_icon()

    def get_config_rows(self) -> list:
        parent_entries = super().get_config_rows()
        return parent_entries
