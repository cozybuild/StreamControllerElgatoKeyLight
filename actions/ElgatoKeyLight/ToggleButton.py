from .Core import Core


class ToggleButton(Core):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_key_down(self) -> None:
        self.toggle_light()
