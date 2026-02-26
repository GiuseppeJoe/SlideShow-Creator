"""CLI entry point - run with: python -m slideshow_creator"""

import argparse
import sys

from .generator import SlideshowConfig, generate_slideshow, quick_generate


def main():
    parser = argparse.ArgumentParser(
        description="Generate Pinterest-style TikTok slideshows for app promotion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Quick generate with defaults (HabitAI glow up)
  python -m slideshow_creator

  # Custom topic and aesthetic
  python -m slideshow_creator --topic "morning routine" --aesthetic "that girl"

  # From a YAML config file
  python -m slideshow_creator --config my_slideshow.yaml

  # Use local images instead of AI generation
  python -m slideshow_creator --image-mode local --images img1.jpg img2.jpg img3.jpg img4.jpg

  # Manual script with AI images
  python -m slideshow_creator --script-mode manual --script-file script.json

Environment variables:
  GEMINI_API_KEY    - Required for AI image/script generation (get free at https://aistudio.google.com/apikey)
  UNSPLASH_API_KEY  - Required if using --image-mode unsplash
""",
    )

    parser.add_argument(
        "--config", "-c",
        help="Path to YAML config file (overrides all other options)",
    )
    parser.add_argument(
        "--app-name",
        default="HabitAI",
        help="App name to promote (default: HabitAI)",
    )
    parser.add_argument(
        "--app-description",
        default="AI-powered habit tracking and accountability coach",
        help="Brief app description for script generation",
    )
    parser.add_argument(
        "--topic", "-t",
        default="glow up protocol",
        help="Content topic/hook theme (default: 'glow up protocol')",
    )
    parser.add_argument(
        "--aesthetic", "-a",
        default="clean girl",
        help="Visual aesthetic style (default: 'clean girl'). Options: old money, clean girl, that girl, minimal, cozy",
    )
    parser.add_argument(
        "--output", "-o",
        default="./output",
        help="Output directory (default: ./output)",
    )
    parser.add_argument(
        "--image-mode",
        choices=["generate", "unsplash", "local", "demo"],
        default="generate",
        help="Image sourcing: 'generate' (Nano Banana AI), 'unsplash', 'local', or 'demo' (gradient placeholders) (default: generate)",
    )
    parser.add_argument(
        "--images",
        nargs="+",
        help="Local image paths (required if --image-mode local)",
    )
    parser.add_argument(
        "--script-mode",
        choices=["generate", "manual"],
        default="generate",
        help="Script mode: 'generate' (AI) or 'manual' (default: generate)",
    )
    parser.add_argument(
        "--script-file",
        help="Path to manual script JSON file (required if --script-mode manual)",
    )
    parser.add_argument(
        "--font",
        help="Path to a .ttf font file for text rendering",
    )
    parser.add_argument(
        "--prefix",
        default="slide",
        help="Output filename prefix (default: slide)",
    )

    args = parser.parse_args()

    # Build config
    if args.config:
        config = SlideshowConfig.from_yaml(args.config)
    else:
        manual_script = None
        if args.script_mode == "manual":
            if not args.script_file:
                parser.error("--script-file required when --script-mode is 'manual'")
            import json
            with open(args.script_file) as f:
                manual_script = json.load(f)

        config = SlideshowConfig(
            app_name=args.app_name,
            app_description=args.app_description,
            topic=args.topic,
            aesthetic=args.aesthetic,
            output_dir=args.output,
            image_mode=args.image_mode,
            local_images=args.images or [],
            script_mode=args.script_mode,
            manual_script=manual_script,
            font_path=args.font,
            filename_prefix=args.prefix,
        )

    print("=" * 60)
    print("  SlideShow Creator - Pinterest Aesthetic TikTok Ads")
    print("=" * 60)
    print(f"  App:       {config.app_name}")
    print(f"  Topic:     {config.topic}")
    print(f"  Aesthetic: {config.aesthetic}")
    print(f"  Images:    {config.image_mode}")
    print(f"  Script:    {config.script_mode}")
    print(f"  Output:    {config.output_dir}")
    print("=" * 60)
    print()

    try:
        paths = generate_slideshow(config)
        print(f"\nSlideshow ready! Upload these {len(paths)} slides to TikTok.")
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
