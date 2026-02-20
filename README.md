# SlideShow Creator

Automated Pinterest-style TikTok slideshow generator for app promotion. Uses **Nano Banana** (Gemini 2.5 Flash Image) to generate aesthetic images and AI-written scripts that follow the high-converting "Pinterest Slideshow" ad format.

## The Format

This tool automates the exact strategy that bypasses TikTok "ad blindness":

| Slide | Role | What It Does |
|-------|------|-------------|
| **1** | Hook/Bait | Aesthetic image + compelling title that stops the scroll |
| **2** | Value Tip 1 | Real advice that builds trust (demographic filter) |
| **3** | Value Tip 2 | More genuine value — user is now engaged with the carousel |
| **4** | Gatekeep | Soft-sell disguised as a "secret" — user feels they *discovered* the app |

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Set your Gemini API key (free at https://aistudio.google.com/apikey)
export GEMINI_API_KEY="your-key-here"

# Generate a full slideshow (images + script, fully automated)
python -m slideshow_creator
```

That's it. 4 slides land in `./output/` ready to upload to TikTok.

## Usage

### Fully Automated (default)

```bash
# Glow up topic with clean girl aesthetic
python -m slideshow_creator --topic "glow up protocol" --aesthetic "clean girl"

# Morning routine with that girl aesthetic
python -m slideshow_creator --topic "morning routine" --aesthetic "that girl"

# Productivity with old money aesthetic
python -m slideshow_creator --topic "productivity habits" --aesthetic "old money"
```

### From Config File

```bash
python -m slideshow_creator --config examples/habitai_glow_up.yaml
```

### With Local Images

```bash
python -m slideshow_creator --image-mode local --images beach.jpg kitchen.jpg morning.jpg lifestyle.jpg
```

### With Manual Script

```bash
python -m slideshow_creator --script-mode manual --script-file examples/manual_script.json
```

### All Options

```
--app-name          App name to promote (default: HabitAI)
--app-description   Brief app description for AI script generation
--topic, -t         Content topic/hook theme
--aesthetic, -a     Visual style: clean girl, old money, that girl, minimal, cozy
--output, -o        Output directory (default: ./output)
--image-mode        generate (Nano Banana AI), unsplash, or local
--images            Local image paths (for --image-mode local)
--script-mode       generate (AI) or manual
--script-file       Path to manual script JSON
--font              Custom .ttf font path
--config, -c        YAML config file (overrides other options)
```

## Python API

```python
from slideshow_creator.generator import quick_generate

# One-liner
quick_generate(
    app_name="HabitAI",
    app_description="AI habit tracking coach",
    topic="morning routine that changed my life",
    aesthetic="that girl",
)
```

## How It Works

1. **Script Generation** — Gemini writes the hook, value tips, and gatekeep copy following the Pinterest slideshow ad psychology
2. **Image Generation** — Nano Banana (Gemini 2.5 Flash Image) creates aesthetic Pinterest-style photos tailored to each slide
3. **Rendering** — Pillow composites dark gradient overlays + styled text onto the generated images
4. **Output** — 4 publication-ready 1080x1920 PNG slides

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes (for AI mode) | Google AI Studio API key |
| `UNSPLASH_API_KEY` | Only for unsplash mode | Unsplash developer key |

## Examples

Pre-built configs in `examples/`:
- `habitai_glow_up.yaml` — Glow up protocol, clean girl aesthetic
- `habitai_morning_routine.yaml` — Morning routine, that girl aesthetic
- `habitai_productivity.yaml` — Productivity, old money aesthetic
- `manual_script.json` — Example manual script for the 4-slide format
