"""Full pipeline generator - orchestrates image generation, script writing, and rendering."""

import os
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from PIL import Image

from .gemini import generate_aesthetic_image, generate_slide_images, generate_slideshow_script
from .image_source import resolve_image
from .renderer import (
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
    image_mode: str = "generate"  # "generate" (Nano Banana), "unsplash", "local"
    local_images: list[str] = field(default_factory=list)  # paths for "local" mode

    # Script mode
    script_mode: str = "generate"  # "generate" (AI), "manual"
    manual_script: dict | None = None  # for "manual" mode

    # Overlay settings
    overlay_top_opacity: int = 60
    overlay_bottom_opacity: int = 200

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
        images = generate_slide_images(
            topic=config.topic,
            aesthetic=config.aesthetic,
            num_slides=num_slides,
        )
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
