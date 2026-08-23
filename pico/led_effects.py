import time
import random
import math


BLACK = (0, 0, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
CYAN = (0, 255, 255)
BLUE = (0, 0, 255)
MAGENTA = (255, 0, 255)
WHITE = (255, 255, 255)


class LEDEffects:
    def __init__(self, np, num_led):
        self.np = np
        self.num_led = num_led

        self.effect_start_time = time.ticks_ms()

        self.random_effect_func = None
        self.random_effect_args = ()

        self.random_rainbow_effect_func = None
        self.random_rainbow_effect_args = ()

        self.fall_direction = 1
        self.fall_step_seconds = 1
        self.fall_landed_count = 0
        self.fall_landed_colors = []
        self.fall_active_color = WHITE
        self.fall_active_start_time = time.ticks_ms()

    def hsv_to_rgb(self, hue):
        hue = int(hue) % 360

        if hue < 60:
            return (
                255,
                min(255, hue * 4),
                0
            )

        if hue < 120:
            return (
                min(255, (120 - hue) * 4),
                255,
                0
            )

        if hue < 180:
            return (
                0,
                255,
                min(255, (hue - 120) * 4)
            )

        if hue < 240:
            return (
                0,
                min(255, (240 - hue) * 4),
                255
            )

        if hue < 300:
            return (
                min(255, (hue - 240) * 4),
                0,
                255
            )

        return (
            255,
            0,
            min(255, (360 - hue) * 4)
        )

    def random_color(self):
        while True:
            color = (
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255)
            )

            if color != BLACK:
                return color

    def get_effect_elapsed_seconds(self):
        elapsed_ms = time.ticks_diff(
            time.ticks_ms(),
            self.effect_start_time
        )

        return elapsed_ms / 1000.0

    def reset_effect_time(self):
        self.effect_start_time = time.ticks_ms()

    def led_blank(self):
        self.np.clear()

    def led_comet(
        self,
        direction=1,
        cycle_seconds=2
    ):
        if cycle_seconds <= 0:
            cycle_seconds = 2

        if direction >= 0:
            direction = 1
        else:
            direction = -1

        elapsed = self.get_effect_elapsed_seconds()

        phase = (
            elapsed % cycle_seconds
        ) / cycle_seconds * 360.0

        for index in range(self.num_led):
            hue = (
                index * 6
                - direction * phase
            )

            self.np.pixel_set(
                index,
                self.hsv_to_rgb(hue)
            )

    def led_rainbow(self, cycle_seconds=2):
        if cycle_seconds <= 0:
            cycle_seconds = 2

        elapsed = self.get_effect_elapsed_seconds()

        phase = (
            elapsed % cycle_seconds
        ) / cycle_seconds * 360.0

        color = self.hsv_to_rgb(phase)

        for index in range(self.num_led):
            self.np.pixel_set(index, color)

    def led_pulse(
        self,
        color=WHITE,
        cycle_seconds=1
    ):
        if cycle_seconds <= 0:
            cycle_seconds = 1

        # ticks_diff で wrap-around を処理してから cycle_ms で割る
        cycle_ms = int(cycle_seconds * 1000)
        elapsed_ms = time.ticks_diff(time.ticks_ms(), self.effect_start_time)
        progress = (elapsed_ms % cycle_ms) / cycle_ms

        brightness = (1.0 - math.cos(progress * 2.0 * math.pi)) / 2.0

        red, green, blue = color

        pulse_color = (
            int(red * brightness),
            int(green * brightness),
            int(blue * brightness)
        )

        for index in range(self.num_led):
            self.np.pixel_set(
                index,
                pulse_color
            )

    def led_pulse_red(self):
        self.led_pulse(RED)

    def led_pulse_yellow(self):
        self.led_pulse(YELLOW)

    def led_pulse_green(self):
        self.led_pulse(GREEN)

    def led_pulse_cyan(self):
        self.led_pulse(CYAN)

    def led_pulse_blue(self):
        self.led_pulse(BLUE)

    def led_pulse_magenta(self):
        self.led_pulse(MAGENTA)

    def led_pulse_white(self):
        self.led_pulse(WHITE)

    def led_half(
        self,
        outward=True,
        cycle_seconds=1
    ):
        if cycle_seconds <= 0:
            cycle_seconds = 1

        half_count = self.num_led // 2

        if half_count <= 0:
            return

        elapsed = self.get_effect_elapsed_seconds()

        led_offset = (
            elapsed % cycle_seconds
        ) / cycle_seconds * half_count

        hue_per_led = 360.0 / half_count

        for index in range(self.num_led):
            if index < half_count:
                distance_from_center = (
                    half_count - 1 - index
                )
            else:
                distance_from_center = (
                    index - half_count
                )

            if outward:
                hue = (
                    distance_from_center
                    - led_offset
                ) * hue_per_led
            else:
                hue = (
                    distance_from_center
                    + led_offset
                ) * hue_per_led

            self.np.pixel_set(
                index,
                self.hsv_to_rgb(hue)
            )

    def reset_fall(
        self,
        direction=1,
        step_seconds=1
    ):
        if direction >= 0:
            self.fall_direction = 1
        else:
            self.fall_direction = -1

        if step_seconds <= 0:
            step_seconds = 1

        self.fall_step_seconds = step_seconds
        self.fall_landed_count = 0
        self.fall_landed_colors = []
        self.fall_active_color = (
            self.random_color()
        )
        self.fall_active_start_time = (
            time.ticks_ms()
        )

        self.np.clear()

    def led_fall(
        self,
        direction=1,
        step_seconds=1
    ):
        if direction >= 0:
            direction = 1
        else:
            direction = -1

        if step_seconds <= 0:
            step_seconds = 1

        if (
            direction != self.fall_direction
            or step_seconds
            != self.fall_step_seconds
        ):
            self.reset_fall(
                direction,
                step_seconds
            )

        if (
            self.fall_landed_count
            >= self.num_led
        ):
            self.reset_fall(
                direction,
                step_seconds
            )

        self.np.clear()

        if direction == 1:
            for index in range(
                self.fall_landed_count
            ):
                led_index = (
                    self.num_led - 1 - index
                )

                self.np.pixel_set(
                    led_index,
                    self.fall_landed_colors[
                        index
                    ]
                )

            start_index = 0
            target_index = (
                self.num_led
                - 1
                - self.fall_landed_count
            )
        else:
            for index in range(
                self.fall_landed_count
            ):
                self.np.pixel_set(
                    index,
                    self.fall_landed_colors[
                        index
                    ]
                )

            start_index = self.num_led - 1
            target_index = (
                self.fall_landed_count
            )

        elapsed_ms = time.ticks_diff(
            time.ticks_ms(),
            self.fall_active_start_time
        )

        step_interval_ms = int(
            step_seconds * 1000
        )

        if step_interval_ms <= 0:
            step_interval_ms = 1000

        moved_led_count = (
            elapsed_ms // step_interval_ms
        )

        move_distance = abs(
            target_index - start_index
        )

        if moved_led_count > move_distance:
            moved_led_count = move_distance

        if direction == 1:
            active_index = (
                start_index + moved_led_count
            )
        else:
            active_index = (
                start_index - moved_led_count
            )

        if active_index < 0:
            active_index = 0

        if active_index >= self.num_led:
            active_index = self.num_led - 1

        self.np.pixel_set(
            active_index,
            self.fall_active_color
        )

        if moved_led_count >= move_distance:
            self.fall_landed_colors.append(
                self.fall_active_color
            )

            self.fall_landed_count += 1

            if (
                self.fall_landed_count
                >= self.num_led
            ):
                self.np.clear()

                for index in range(
                    self.num_led
                ):
                    if direction == 1:
                        led_index = (
                            self.num_led
                            - 1
                            - index
                        )
                    else:
                        led_index = index

                    self.np.pixel_set(
                        led_index,
                        self.fall_landed_colors[
                            index
                        ]
                    )

                self.np.show()
                time.sleep_ms(100)

                self.reset_fall(
                    direction,
                    step_seconds
                )
            else:
                self.fall_active_color = (
                    self.random_color()
                )

                self.fall_active_start_time = (
                    time.ticks_ms()
                )

    def choose_random_effect(self):
        cycle_seconds = random.randint(1, 5)

        effect_number = random.randint(0, 7)

        if effect_number == 0:
            self.random_effect_func = (
                self.led_pulse_red
            )
            self.random_effect_args = ()

        elif effect_number == 1:
            self.random_effect_func = (
                self.led_pulse_yellow
            )
            self.random_effect_args = ()

        elif effect_number == 2:
            self.random_effect_func = (
                self.led_pulse_green
            )
            self.random_effect_args = ()

        elif effect_number == 3:
            self.random_effect_func = (
                self.led_pulse_cyan
            )
            self.random_effect_args = ()

        elif effect_number == 4:
            self.random_effect_func = (
                self.led_pulse_blue
            )
            self.random_effect_args = ()

        elif effect_number == 5:
            self.random_effect_func = (
                self.led_pulse_magenta
            )
            self.random_effect_args = ()

        elif effect_number == 6:
            self.random_effect_func = (
                self.led_pulse_white
            )
            self.random_effect_args = ()

        else:
            direction = random.choice(
                (-1, 1)
            )

            self.random_effect_func = (
                self.led_fall
            )
            self.random_effect_args = (
                direction,
                cycle_seconds
            )

            self.reset_fall(
                direction,
                cycle_seconds
            )

    def led_random(self):
        if self.random_effect_func is None:
            self.choose_random_effect()

        self.random_effect_func(
            *self.random_effect_args
        )

    def choose_random_rainbow_effect(self):
        cycle_seconds = random.randint(1, 5)
        effect_number = random.randint(0, 2)

        if effect_number == 0:
            direction = random.choice(
                (-1, 1)
            )

            self.random_rainbow_effect_func = (
                self.led_comet
            )

            self.random_rainbow_effect_args = (
                direction,
                cycle_seconds
            )

        elif effect_number == 1:
            self.random_rainbow_effect_func = (
                self.led_rainbow
            )

            self.random_rainbow_effect_args = (
                cycle_seconds,
            )

        else:
            outward = random.choice(
                (True, False)
            )

            self.random_rainbow_effect_func = (
                self.led_half
            )

            self.random_rainbow_effect_args = (
                outward,
                cycle_seconds
            )

    def led_random_rainbow(self):
        if (
            self.random_rainbow_effect_func
            is None
        ):
            self.choose_random_rainbow_effect()

        self.random_rainbow_effect_func(
            *self.random_rainbow_effect_args
        )

    def prepare_effect(self, label):
        self.reset_effect_time()

        if label == "random":
            self.random_effect_func = None
            self.random_effect_args = ()
            self.choose_random_effect()

        elif label == "random_rainbow":
            self.random_rainbow_effect_func = None
            self.random_rainbow_effect_args = ()
            self.choose_random_rainbow_effect()

        elif label == "fall":
            self.reset_fall()

    def get_effects(self):
        return [
            {
                "label": "blank",
                "func": self.led_blank
            },
            {
                "label": "comet",
                "func": self.led_comet
            },
            {
                "label": "rainbow",
                "func": self.led_rainbow
            },
            {
                "label": "pulse",
                "func": self.led_pulse
            },
            {
                "label": "pulse_red",
                "func": self.led_pulse_red
            },
            {
                "label": "pulse_yellow",
                "func": self.led_pulse_yellow
            },
            {
                "label": "pulse_green",
                "func": self.led_pulse_green
            },
            {
                "label": "pulse_cyan",
                "func": self.led_pulse_cyan
            },
            {
                "label": "pulse_blue",
                "func": self.led_pulse_blue
            },
            {
                "label": "pulse_magenta",
                "func": self.led_pulse_magenta
            },
            {
                "label": "pulse_white",
                "func": self.led_pulse_white
            },
            {
                "label": "half",
                "func": self.led_half
            },
            {
                "label": "random",
                "func": self.led_random
            },
            {
                "label": "random_rainbow",
                "func": self.led_random_rainbow
            },
            {
                "label": "fall",
                "func": self.led_fall
            }
        ]
