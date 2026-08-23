import array, time
from machine import Pin
import rp2

@rp2.asm_pio(
    sideset_init=rp2.PIO.OUT_LOW,
    out_shiftdir=rp2.PIO.SHIFT_LEFT,
    autopull=True,
    pull_thresh=24
)
def ws2812():
    T1 = 2
    T2 = 5
    T3 = 3
    wrap_target()
    label("bitloop")
    out(x, 1)               .side(0)    [T3 - 1]
    jmp(not_x, "do_zero")   .side(1)    [T1 - 1]
    jmp("bitloop")          .side(1)    [T2 - 1]
    label("do_zero")
    nop()                   .side(0)    [T2 - 1]
    wrap()

class PicoWS2812:
    def __init__(self, pin, num_leds, brightness=1.0, sm_id=0):
        self.num_leds = num_leds
        self.brightness = brightness
        self.ar = array.array("I", [0 for _ in range(num_leds)])
        self.sm = rp2.StateMachine(
            sm_id,
            ws2812,
            freq=8_000_000,
            sideset_base=Pin(pin)
        )
        self.sm.active(1)

    def pixel_set(self, i, color):
        # color = (r,g,b)
        r, g, b = color
        self.ar[i] = (g<<16) | (r<<8) | b

    def pixels_set(self, colors):
        # colors = [(r,g,b), ...]
        n = min(len(colors), self.num_leds)
        for i in range(n):
            r, g, b = colors[i]
            self.ar[i] = (g<<16) | (r<<8) | b

    def pixels_fill(self, color):
        for i in range(self.num_leds):
            self.pixel_set(i, color)

    def clear(self):
        self.pixels_fill((0,0,0))

    def show(self):
        dim = array.array("I", [0]*self.num_leds)
        for i, c in enumerate(self.ar):
            r = int(((c >> 8) & 0xFF) * self.brightness)
            g = int(((c >>16) & 0xFF) * self.brightness)
            b = int(( c      & 0xFF) * self.brightness)
            dim[i] = (g<<16) | (r<<8) | b
        self.sm.put(dim, 8)
        time.sleep_ms(1)

    def close(self):
        self.clear()
        self.show()
        self.sm.active(0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

def sample():
  leds = PicoWS2812(pin=10, num_leds=8, brightness=0.1)
  try:
      colors = [(0,0,0),(0,0,255),(0,255,0),(0,255,255),(255,0,0),(255,0,255),(255,255,0),(255,255,255)]
      leds.pixels_set(colors)
      leds.show()
      time.sleep(1)
  finally:
      leds.close()

if __name__ == "__main__":
    sample()
