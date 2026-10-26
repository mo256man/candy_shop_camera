from PIL import Image, ImageDraw, ImageFont


class IconGenerator:
    def __init__(
        self,
        width=64,
        height=64,
        radius=10,
        padding=8,
        font_path="C:/Windows/Fonts/msgothic.ttc",
        font_size=30,
    ):
        self.width = width
        self.height = height
        self.radius = radius
        self.padding = padding
        self.font_path = font_path
        self.font_size = font_size

    def create_background(self, color):
        image = Image.new(
            "RGBA",
            (self.width, self.height),
            (0, 0, 0, 0),
        )

        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle(
            (0, 0, self.width - 1, self.height - 1),
            radius=self.radius,
            fill=(*color, 255),
        )

        return image

    def create_text_icon(self, background_color, text, output_path):
        image = self.create_background(background_color)
        draw = ImageDraw.Draw(image)

        font = ImageFont.truetype(
            self.font_path,
            self.font_size,
        )

        draw.text(
            (self.width // 2, self.height // 2),
            text,
            font=font,
            fill=(255, 255, 255, 255),
            anchor="mm",
        )

        image.save(output_path)

    def create_image_icon(
        self,
        background_color,
        source_path,
        output_path,
    ):
        background = self.create_background(background_color)
        foreground = Image.open(source_path).convert("RGBA")

        max_width = self.width - self.padding * 2
        max_height = self.height - self.padding * 2

        foreground.thumbnail(
            (max_width, max_height),
            Image.Resampling.LANCZOS,
        )

        x = (self.width - foreground.width) // 2
        y = (self.height - foreground.height) // 2

        background.alpha_composite(
            foreground,
            (x, y),
        )

        background.save(output_path)


generator = IconGenerator()

generator.create_text_icon(
    background_color=(0, 165, 191),
    text="誠",
    output_path="shinsengumi.png",
)

# generator.create_image_icon(
#     background_color=(73, 55, 89),
#     source_path="image1.png",
#     output_path="tyoutei.png",
# )

# generator.create_image_icon(
#     background_color=(35, 59, 108),
#     source_path="image2.png",
#     output_path="tokugawa.png",
# )
