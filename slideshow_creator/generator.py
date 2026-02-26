"""Full pipeline generator - orchestrates image generation, script writing, and rendering."""

import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFilter

from .image_source import resolve_image
from .renderer import (
    SLIDE_HEIGHT,
    SLIDE_WIDTH,
    OverlayConfig,
    SlideLayout,
    crop_to_slide,
    render_gatekeep_slide,
    render_hook_slide,
    render_value_slide,
)


@dataclass
class SlideshowConfig:
    """Configuration for a slideshow generation run."""

    # Required
    app_name: str = "HabitAI"
    app_description: str = "AI-powered habit tracking and accountability coach"
    topic: str = "glow up protocol"

    # Visual style
    aesthetic: str = "clean girl"
    font_path: str | None = None

    # Output
    output_dir: str = "./output"
    filename_prefix: str = "slide"

    # Image sourcing mode
    image_mode: str = "generate"  # "generate" (Nano Banana), "unsplash", "local", "demo"
    local_images: list[str] = field(default_factory=list)  # paths for "local" mode

    # Script mode
    script_mode: str = "generate"  # "generate" (AI), "manual"
    manual_script: dict | None = None  # for "manual" mode

    # Overlay settings
    overlay_top_opacity: int = 60
    overlay_bottom_opacity: int = 200

    # Realism post-processing (de-perfect AI images)
    realism: bool = True  # apply de-perfecting pipeline
    grain: float = 0.30  # film grain intensity (0 = off)
    warmth: float | None = None  # color temp shift (None = random subtle)
    vignette: float = 0.35  # lens vignette strength (0 = off)
    jpeg_quality: int = 75  # JPEG compression artifacts (100 = off)
    lens_softness: float = 0.4  # corner blur (0 = off)

    # Layout tweaks
    content_top: float = 0.30
    title_size: int = 72
    subtitle_size: int = 48
    body_size: int = 44

    @classmethod
    def from_yaml(cls, path: str) -> "SlideshowConfig":
        """Load config from a YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_dict(cls, data: dict) -> "SlideshowConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# Color palettes for demo aesthetic images
DEMO_PALETTES = {
    "clean girl": [
        [(245, 228, 215), (210, 180, 160), (180, 150, 130)],  # warm beige
        [(220, 210, 200), (190, 175, 165), (160, 140, 125)],  # soft taupe
        [(235, 220, 210), (200, 185, 170), (170, 150, 135)],  # blush nude
        [(225, 215, 205), (195, 180, 168), (165, 145, 130)],  # cream latte
    ],
    "old money": [
        [(60, 70, 60), (40, 55, 45), (25, 35, 30)],  # deep forest
        [(80, 75, 65), (55, 50, 40), (35, 30, 25)],  # dark leather
        [(70, 65, 55), (50, 45, 35), (30, 25, 20)],  # aged mahogany
        [(65, 70, 75), (45, 50, 55), (25, 30, 35)],  # slate navy
    ],
    "that girl": [
        [(255, 220, 185), (240, 190, 150), (220, 160, 120)],  # golden sunrise
        [(250, 235, 210), (230, 205, 175), (210, 175, 140)],  # honey glow
        [(245, 225, 200), (225, 195, 165), (200, 165, 130)],  # warm peach
        [(240, 230, 215), (220, 200, 180), (195, 170, 145)],  # soft caramel
    ],
    "minimal": [
        [(240, 240, 240), (210, 210, 210), (180, 180, 180)],  # pure grey
        [(245, 245, 240), (215, 215, 210), (185, 185, 180)],  # warm white
        [(235, 240, 245), (205, 210, 215), (175, 180, 185)],  # cool grey
        [(238, 238, 235), (208, 208, 205), (178, 178, 175)],  # stone
    ],
    "cozy": [
        [(180, 120, 80), (150, 95, 60), (120, 70, 40)],  # warm brown
        [(165, 110, 75), (140, 85, 55), (110, 65, 35)],  # coffee
        [(175, 125, 90), (145, 100, 70), (115, 75, 50)],  # caramel
        [(160, 115, 80), (135, 90, 60), (105, 65, 40)],  # cinnamon
    ],
}


def _generate_demo_image(palette: list[tuple], seed: int = 0) -> Image.Image:
    """Generate a beautiful gradient placeholder image for demo mode."""
    random.seed(seed)
    img = Image.new("RGB", (SLIDE_WIDTH, SLIDE_HEIGHT))
    draw = ImageDraw.Draw(img)

    c1, c2, c3 = palette

    # Draw a smooth vertical gradient
    for y in range(SLIDE_HEIGHT):
        progress = y / SLIDE_HEIGHT
        if progress < 0.5:
            t = progress * 2
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
        else:
            t = (progress - 0.5) * 2
            r = int(c2[0] + (c3[0] - c2[0]) * t)
            g = int(c2[1] + (c3[1] - c2[1]) * t)
            b = int(c2[2] + (c3[2] - c2[2]) * t)
        draw.line([(0, y), (SLIDE_WIDTH, y)], fill=(r, g, b))

    # Add subtle noise/texture for organic feel
    noise = Image.new("RGB", (SLIDE_WIDTH, SLIDE_HEIGHT))
    noise_draw = ImageDraw.Draw(noise)
    for _ in range(8000):
        x = random.randint(0, SLIDE_WIDTH - 1)
        y = random.randint(0, SLIDE_HEIGHT - 1)
        v = random.randint(-15, 15)
        px = img.getpixel((x, y))
        noise_draw.point(
            (x, y),
            fill=(
                max(0, min(255, px[0] + v)),
                max(0, min(255, px[1] + v)),
                max(0, min(255, px[2] + v)),
            ),
        )

    # Blend noise into the gradient
    img = Image.blend(img, noise, 0.3)

    # Soft blur for smoothness
    img = img.filter(ImageFilter.GaussianBlur(2))

    return img


def _generate_demo_images(aesthetic: str, num_slides: int) -> list[Image.Image]:
    """Generate a set of demo placeholder images matching an aesthetic."""
    palette_key = aesthetic.lower()
    palettes = DEMO_PALETTES.get(palette_key, DEMO_PALETTES["clean girl"])
    images = []
    for i in range(num_slides):
        pal = palettes[i % len(palettes)]
        images.append(_generate_demo_image(pal, seed=i * 42))
    return images


def generate_slideshow(config: SlideshowConfig) -> list[Path]:
    """Run the full slideshow generation pipeline.

    Steps:
    1. Generate or load the slideshow script (hook, tips, gatekeep)
    2. Generate or source background images
    3. Render text overlays onto images
    4. Save final slides

    Args:
        config: SlideshowConfig with all parameters

    Returns:
        List of paths to the generated slide images
    """
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Step 1: Script ---
    print("[1/4] Generating slideshow script...")
    if config.script_mode == "generate":
        from .gemini import generate_slideshow_script

        script = generate_slideshow_script(
            app_name=config.app_name,
            app_description=config.app_description,
            topic=config.topic,
        )
    elif config.script_mode == "manual" and config.manual_script:
        script = config.manual_script
    else:
        raise ValueError(
            f"Invalid script_mode '{config.script_mode}'. Use 'generate' or 'manual'."
        )

    print(f"  Hook: {script['hook']['title']}")
    for vs in script["value_slides"]:
        print(f"  Tip {vs['number']}: {vs['title']}")
    print(f"  Gatekeep: {script['gatekeep']['title']}")

    # --- Step 2: Images ---
    num_slides = 2 + len(script["value_slides"])  # hook + value slides + gatekeep
    print(f"\n[2/4] {'Generating' if config.image_mode == 'generate' else 'Loading'} {num_slides} images...")

    if config.image_mode == "generate":
        from .gemini import generate_slide_images

        images = generate_slide_images(
            topic=config.topic,
            aesthetic=config.aesthetic,
            num_slides=num_slides,
        )
    elif config.image_mode == "demo":
        images = _generate_demo_images(config.aesthetic, num_slides)
    elif config.image_mode == "unsplash":
        api_key = os.environ.get("UNSPLASH_API_KEY")
        images = []
        for i in range(num_slides):
            query = f"{config.aesthetic} aesthetic {config.topic}"
            img = resolve_image(f"unsplash:{query}", api_key=api_key, index=i)
            images.append(img)
    elif config.image_mode == "local":
        if len(config.local_images) < num_slides:
            raise ValueError(
                f"Need {num_slides} local images, got {len(config.local_images)}"
            )
        images = [resolve_image(p) for p in config.local_images[:num_slides]]
    else:
        raise ValueError(f"Invalid image_mode '{config.image_mode}'.")

    # --- Step 2.5: De-perfect images for realism ---
    if config.realism:
        from .postprocess import make_realistic

        print("\n  Applying realism post-processing...")
        images = [
            make_realistic(
                img,
                grain=config.grain,
                warmth=config.warmth,
                vignette=config.vignette,
                jpeg_quality=config.jpeg_quality,
                lens_softness=config.lens_softness,
                seed=i,
            )
            for i, img in enumerate(images)
        ]
        print(f"  De-perfected {len(images)} images (grain={config.grain}, vignette={config.vignette})")

    # --- Step 3: Render ---
    print("\n[3/4] Rendering slides...")
    overlay = OverlayConfig(
        top_opacity=config.overlay_top_opacity,
        bottom_opacity=config.overlay_bottom_opacity,
    )
    layout = SlideLayout(
        content_top=config.content_top,
        title_size=config.title_size,
        subtitle_size=config.subtitle_size,
        body_size=config.body_size,
    )

    rendered_slides = []

    # Slide 1: Hook
    hook = script["hook"]
    slide1 = render_hook_slide(
        background=images[0],
        title=hook["title"],
        subtitle=hook.get("subtitle", ""),
        overlay=overlay,
        layout=layout,
        font_path=config.font_path,
    )
    rendered_slides.append(slide1)
    print("  Rendered: hook slide")

    # Slides 2-N-1: Value tips
    for i, vs in enumerate(script["value_slides"]):
        slide = render_value_slide(
            background=images[1 + i],
            number=vs["number"],
            title=vs["title"],
            body=vs["body"],
            overlay=overlay,
            layout=layout,
            font_path=config.font_path,
        )
        rendered_slides.append(slide)
        print(f"  Rendered: value slide {vs['number']}")

    # Last slide: Gatekeep
    gk = script["gatekeep"]
    slide_gk = render_gatekeep_slide(
        background=images[-1],
        number=gk["number"],
        title=gk["title"],
        body=gk["body"],
        app_name=gk.get("app_mention", config.app_name),
        cta=script.get("cta", "link in bio"),
        overlay=overlay,
        layout=layout,
        font_path=config.font_path,
    )
    rendered_slides.append(slide_gk)
    print("  Rendered: gatekeep slide")

    # --- Step 4: Save ---
    print(f"\n[4/4] Saving to {output_dir}/")
    output_paths = []
    for i, slide in enumerate(rendered_slides, 1):
        filename = f"{config.filename_prefix}_{i}.png"
        path = output_dir / filename
        slide.save(path, "PNG")
        output_paths.append(path)
        print(f"  Saved: {path}")

    # Also save the script as JSON for reference
    import json
    script_path = output_dir / f"{config.filename_prefix}_script.json"
    with open(script_path, "w") as f:
        json.dump(script, f, indent=2)
    print(f"  Saved: {script_path}")

    print(f"\nDone! {len(output_paths)} slides generated.")
    return output_paths


def quick_generate(
    app_name: str = "HabitAI",
    app_description: str = "AI-powered habit tracking and accountability coach",
    topic: str = "glow up protocol",
    aesthetic: str = "clean girl",
    output_dir: str = "./output",
) -> list[Path]:
    """Quick one-liner to generate a full slideshow.

    Example:
        quick_generate("HabitAI", "AI habit coach", "morning routine", "that girl")
    """
    config = SlideshowConfig(
        app_name=app_name,
        app_description=app_description,
        topic=topic,
        aesthetic=aesthetic,
        output_dir=output_dir,
    )
    return generate_slideshow(config)
