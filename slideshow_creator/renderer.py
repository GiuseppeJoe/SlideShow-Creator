"""Slide renderer - handles image processing, overlays, and text rendering."""

import textwrap
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# TikTok slideshow dimensions (9:16 portrait)
SLIDE_WIDTH = 1080
SLIDE_HEIGHT = 1920

FONTS_DIR = Path(__file__).parent / "fonts"


@dataclass
class TextStyle:
    """Configuration for text rendering."""

    font_path: str | None = None
    size: int = 64
    color: str = "#FFFFFF"
    bold: bool = False
    italic: bool = False
    line_spacing: int = 12
    shadow: bool = True
    shadow_color: str = "#000000"
    shadow_offset: tuple[int, int] = (3, 3)
    shadow_blur: int = 5
    max_width_ratio: float = 0.85  # % of slide width for text wrapping
    align: str = "left"


@dataclass
class OverlayConfig:
    """Configuration for the dark gradient overlay on images."""

    enabled: bool = True
    # Gradient goes from top opacity to bottom opacity
    top_opacity: int = 60  # 0-255
    bottom_opacity: int = 200  # 0-255
    color: tuple[int, int, int] = (0, 0, 0)


@dataclass
class SlideLayout:
    """Defines where text elements are positioned on a slide."""

    # All values are ratios of slide dimensions (0.0 - 1.0)
    content_top: float = 0.30  # Where main content starts vertically
    content_bottom: float = 0.85  # Where main content ends
    padding_x: float = 0.075  # Horizontal padding from edges
    title_size: int = 72
    subtitle_size: int = 48
    body_size: int = 44
    number_size: int = 120
    cta_size: int = 36


DEFAULT_OVERLAY = OverlayConfig()
DEFAULT_LAYOUT = SlideLayout()


def _load_font(style: TextStyle) -> ImageFont.FreeTypeFont:
    """Load a font, falling back through available options."""
    if style.font_path and Path(style.font_path).exists():
        return ImageFont.truetype(style.font_path, style.size)

    # Try bundled fonts
    weight = "Bold" if style.bold else "Regular"
    for font_name in [
        f"Montserrat-{weight}.ttf",
        f"Inter-{weight}.ttf",
        f"Roboto-{weight}.ttf",
    ]:
        bundled = FONTS_DIR / font_name
        if bundled.exists():
            return ImageFont.truetype(str(bundled), style.size)

    # Try common system font paths
    system_paths = [
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if style.bold else ''}.ttf",
        f"/usr/share/fonts/truetype/liberation/LiberationSans{'-Bold' if style.bold else '-Regular'}.ttf",
        f"/usr/share/fonts/TTF/DejaVuSans{'-Bold' if style.bold else ''}.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for p in system_paths:
        if Path(p).exists():
            return ImageFont.truetype(p, style.size)

    return ImageFont.load_default()


def crop_to_slide(img: Image.Image) -> Image.Image:
    """Crop and resize an image to fit the 9:16 slide dimensions."""
    target_ratio = SLIDE_WIDTH / SLIDE_HEIGHT
    img_ratio = img.width / img.height

    if img_ratio > target_ratio:
        # Image is wider - crop sides
        new_width = int(img.height * target_ratio)
        left = (img.width - new_width) // 2
        img = img.crop((left, 0, left + new_width, img.height))
    else:
        # Image is taller - crop top/bottom
        new_height = int(img.width / target_ratio)
        top = (img.height - new_height) // 2
        img = img.crop((0, top, img.width, top + new_height))

    return img.resize((SLIDE_WIDTH, SLIDE_HEIGHT), Image.LANCZOS)


def apply_overlay(img: Image.Image, config: OverlayConfig | None = None) -> Image.Image:
    """Apply a dark gradient overlay to make text readable."""
    if config is None:
        config = DEFAULT_OVERLAY
    if not config.enabled:
        return img.copy()

    result = img.copy()
    overlay = Image.new("RGBA", (SLIDE_WIDTH, SLIDE_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for y in range(SLIDE_HEIGHT):
        progress = y / SLIDE_HEIGHT
        opacity = int(config.top_opacity + (config.bottom_opacity - config.top_opacity) * progress)
        r, g, b = config.color
        draw.line([(0, y), (SLIDE_WIDTH, y)], fill=(r, g, b, opacity))

    result = result.convert("RGBA")
    result = Image.alpha_composite(result, overlay)
    return result.convert("RGB")


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = font.getbbox(test_line)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines if lines else [""]


def _draw_text_with_shadow(
    draw: ImageDraw.Draw,
    position: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    style: TextStyle,
    img: Image.Image | None = None,
):
    """Draw text with optional shadow/glow effect."""
    x, y = position

    if style.shadow and img is not None:
        # Draw shadow on a separate layer and blur it
        shadow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_layer)
        sx = x + style.shadow_offset[0]
        sy = y + style.shadow_offset[1]
        shadow_draw.text((sx, sy), text, font=font, fill=style.shadow_color)
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(style.shadow_blur))
        img.paste(Image.alpha_composite(img.convert("RGBA"), shadow_layer).convert("RGB"))

    draw.text((x, y), text, font=font, fill=style.color)


def render_text_block(
    img: Image.Image,
    text: str,
    style: TextStyle,
    y_start: int,
    x_start: int | None = None,
    layout: SlideLayout | None = None,
) -> int:
    """Render a block of wrapped text onto an image.

    Returns the y position after the last line of text.
    """
    if layout is None:
        layout = DEFAULT_LAYOUT

    font = _load_font(style)
    max_width = int(SLIDE_WIDTH * style.max_width_ratio)
    pad_x = int(SLIDE_WIDTH * layout.padding_x) if x_start is None else x_start

    lines = _wrap_text(text, font, max_width)
    draw = ImageDraw.Draw(img)

    y = y_start
    for line in lines:
        if style.align == "center":
            bbox = font.getbbox(line)
            line_width = bbox[2] - bbox[0]
            x = (SLIDE_WIDTH - line_width) // 2
        elif style.align == "right":
            bbox = font.getbbox(line)
            line_width = bbox[2] - bbox[0]
            x = SLIDE_WIDTH - pad_x - line_width
        else:
            x = pad_x

        _draw_text_with_shadow(draw, (x, y), line, font, style, img)
        bbox = font.getbbox(line)
        line_height = bbox[3] - bbox[1]
        y += line_height + style.line_spacing

    return y


def render_hook_slide(
    background: Image.Image,
    title: str,
    subtitle: str = "",
    overlay: OverlayConfig | None = None,
    layout: SlideLayout | None = None,
    font_path: str | None = None,
) -> Image.Image:
    """Render a hook/cover slide (Slide 1).

    Big bold title text centered, optional subtitle below.
    """
    if layout is None:
        layout = DEFAULT_LAYOUT

    img = crop_to_slide(background)
    img = apply_overlay(img, overlay)

    # Title - big, bold, centered
    title_style = TextStyle(
        font_path=font_path,
        size=layout.title_size,
        bold=True,
        shadow=True,
        shadow_blur=8,
        align="left",
        line_spacing=16,
    )
    y = int(SLIDE_HEIGHT * layout.content_top)
    y = render_text_block(img, title, title_style, y, layout=layout)

    # Subtitle
    if subtitle:
        y += 20
        sub_style = TextStyle(
            font_path=font_path,
            size=layout.subtitle_size,
            bold=False,
            color="#E0E0E0",
            shadow=True,
            align="left",
        )
        render_text_block(img, subtitle, sub_style, y, layout=layout)

    return img


def render_value_slide(
    background: Image.Image,
    number: int,
    title: str,
    body: str,
    overlay: OverlayConfig | None = None,
    layout: SlideLayout | None = None,
    font_path: str | None = None,
) -> Image.Image:
    """Render a value/tip slide (Slides 2-3).

    Shows a numbered tip with title and body text.
    """
    if layout is None:
        layout = DEFAULT_LAYOUT

    img = crop_to_slide(background)
    img = apply_overlay(img, overlay)

    pad_x = int(SLIDE_WIDTH * layout.padding_x)
    y = int(SLIDE_HEIGHT * layout.content_top)

    # Number + Title combined: "1. Title Here"
    header_text = f"{number}. {title}"
    header_style = TextStyle(
        font_path=font_path,
        size=layout.subtitle_size + 8,
        bold=True,
        shadow=True,
        shadow_blur=6,
        align="left",
        line_spacing=14,
    )
    y = render_text_block(img, header_text, header_style, y, layout=layout)

    # Body text
    y += 24
    body_style = TextStyle(
        font_path=font_path,
        size=layout.body_size,
        bold=False,
        color="#E8E8E8",
        shadow=True,
        shadow_blur=4,
        align="left",
        line_spacing=10,
    )
    render_text_block(img, body, body_style, y, layout=layout)

    return img


def render_gatekeep_slide(
    background: Image.Image,
    number: int,
    title: str,
    body: str,
    app_name: str = "",
    cta: str = "",
    overlay: OverlayConfig | None = None,
    layout: SlideLayout | None = None,
    font_path: str | None = None,
) -> Image.Image:
    """Render the 'gatekeep' soft-sell slide (Slide 4).

    Looks like another tip but subtly promotes the app.
    The app name gets slightly highlighted. CTA at bottom.
    """
    if layout is None:
        layout = DEFAULT_LAYOUT

    img = crop_to_slide(background)

    # Slightly heavier overlay for the sell slide
    sell_overlay = overlay or OverlayConfig(top_opacity=80, bottom_opacity=220)
    img = apply_overlay(img, sell_overlay)

    pad_x = int(SLIDE_WIDTH * layout.padding_x)
    y = int(SLIDE_HEIGHT * layout.content_top)

    # Number + Title
    header_text = f"{number}. {title}"
    header_style = TextStyle(
        font_path=font_path,
        size=layout.subtitle_size + 8,
        bold=True,
        shadow=True,
        shadow_blur=6,
        align="left",
        line_spacing=14,
    )
    y = render_text_block(img, header_text, header_style, y, layout=layout)

    # Body text (the soft sell copy)
    y += 24
    body_style = TextStyle(
        font_path=font_path,
        size=layout.body_size,
        bold=False,
        color="#E8E8E8",
        shadow=True,
        shadow_blur=4,
        align="left",
        line_spacing=10,
    )
    y = render_text_block(img, body, body_style, y, layout=layout)

    # App name highlight
    if app_name:
        y += 30
        app_style = TextStyle(
            font_path=font_path,
            size=layout.subtitle_size,
            bold=True,
            color="#F5E6CA",
            shadow=True,
            shadow_blur=6,
            align="left",
        )
        y = render_text_block(img, app_name, app_style, y, layout=layout)

    # CTA at bottom
    if cta:
        cta_style = TextStyle(
            font_path=font_path,
            size=layout.cta_size,
            bold=False,
            color="#AAAAAA",
            shadow=True,
            shadow_blur=3,
            align="center",
        )
        cta_y = int(SLIDE_HEIGHT * 0.90)
        render_text_block(img, cta, cta_style, cta_y, layout=layout)

    return img
