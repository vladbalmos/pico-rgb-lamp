class Lamp:

    def __init__(self, leds) -> None:
        self._leds = leds
        
    def change_state(self, feature_id, value):
        if feature_id == "change_global_color":
            self.change_all_colors(value)
            result = [(feature_id, value)]
            for i in range(len(self._leds)):
                result.append(('change_led' + str(i) + '_color', value))
            return result
        
        if feature_id.startswith("change_led") and feature_id.endswith("_color"):
            try:
                led_idx = int(feature_id[10])
            except ValueError:
                return
            self.change_led_color(led_idx, value)
            return [(feature_id, value)]
            
    def change_all_colors(self, color):
        for led in self._leds:
            led.set_color(color)
            
    def change_led_color(self, led_idx, color):
        try:
            self._leds[led_idx].set_color(color)
        except IndexError:
            return 
        
    def restore_state(self, state) -> None:
        for feature in state:
            value = feature["schema"]["default"]
            try:
                value = feature["value"]
            except:
                pass

            if feature["id"] == "change_global_color":
                self.change_all_colors(value)
                continue
            
            if feature["id"].startswith("change_led") and feature["id"].endswith("_color"):
                try:
                    led_idx = int(feature["id"][10])
                except ValueError:
                    return
                self.change_led_color(led_idx, value)