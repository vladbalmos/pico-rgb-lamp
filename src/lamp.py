class Lamp:

    def __init__(self, leds) -> None:
        self._leds = leds
        
    def change_state(self, feature_id, state) -> None:
        if feature_id == "change_global_color":
            return self.change_all_colors(state)
        
        if feature_id.startswith("change_led") and feature_id.endswith("_color"):
            try:
                led_idx = int(feature_id[10])
            except ValueError:
                return
            self.change_led_color(led_idx, state)
            
    def change_all_colors(self, color) -> None:
        for led in self._leds:
            led.set_color(color)
            
    def change_led_color(self, led_idx, color) -> None:
        try:
            self._leds[led_idx].set_color(color)
        except IndexError:
            return
        
    def restore_state(self, state) -> None:
        print("Restoring state")
        pass
            