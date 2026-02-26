"""Gemini / Nano Banana integration for AI image generation and script writing."""

import json
import os
import re
from io import BytesIO
from pathlib import Path

from PIL import Image

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

IMAGE_MODEL = "gemini-2.5-flash-image"
TEXT_MODEL = "gemini-2.5-flash"


def _get_client():
    """Create a Gemini API client."""
    if genai is None:
        raise ImportError(
            "google-genai package required. Install with: pip install google-genai"
        )
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable. "
            "Get a free key at https://aistudio.google.com/apikey"
        )
    return genai.Client(api_key=api_key)


def generate_aesthetic_image(
    prompt: str,
    aspect_ratio: str = "9:16",
    style_prefix: str = (
        "candid iPhone photo, slightly imperfect casual photography, "
        "Pinterest aesthetic repost, natural unposed look, "
    ),
) -> Image.Image:
    """Generate an aesthetic image using Nano Banana (Gemini 2.5 Flash Image).

    Args:
        prompt: Description of the desired image
        aspect_ratio: Image aspect ratio (default 9:16 for TikTok)
        style_prefix: Prefix added to all prompts for consistent aesthetic

    Returns:
        PIL Image object
    """
    client = _get_client()

    full_prompt = f"{style_prefix}{prompt}"

    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=full_prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
            ),
        ),
    )

    for part in response.parts:
        if part.inline_data is not None:
            # part.as_image() returns a google.genai Image wrapper, not PIL.
            # Extract raw bytes and open with PIL directly.
            return Image.open(BytesIO(part.inline_data.data)).convert("RGB")

    raise RuntimeError("Nano Banana did not return an image. Try a different prompt.")


def generate_slide_images(
    topic: str,
    aesthetic: str = "clean girl",
    num_slides: int = 4,
) -> list[Image.Image]:
    """Generate a set of aesthetic background images for a slideshow.

    Each image is generated with a prompt tailored to the slide's role
    while maintaining a cohesive aesthetic across all slides.

    Args:
        topic: The slideshow topic (e.g., "glow up", "productivity")
        aesthetic: Visual aesthetic style (e.g., "old money", "clean girl", "that girl")
        num_slides: Number of slides to generate

    Returns:
        List of PIL Image objects
    """
    # Candid phone-quality prompts — NOT studio perfection.
    # These read like real photos someone saved from Pinterest.
    candid = (
        "shot on iPhone, casual unposed photography, slightly imperfect framing, "
        "natural indoor or outdoor lighting with visible ambient color cast, "
        "NOT a studio photo, NOT AI-looking, NOT perfectly symmetrical, "
    )

    slide_prompts = [
        # Slide 1: Hook - aspirational but real
        (
            f"{candid}{aesthetic} aesthetic, lifestyle moment related to {topic}, "
            "golden hour or window light, slightly off-center composition, "
            "background has natural depth of field blur, no text, no faces"
        ),
        # Slide 2: Value tip 1 - casual flat lay or scene
        (
            f"{candid}{aesthetic} aesthetic, cozy flat lay or candid scene, "
            f"wellness vibes related to {topic}, "
            "slightly messy or lived-in look, warm tones, no text"
        ),
        # Slide 3: Value tip 2 - different casual moment
        (
            f"{candid}{aesthetic} aesthetic, morning routine or daily life moment, "
            f"related to {topic}, natural daylight from a window, "
            "casual composition like someone quickly snapped it, no text"
        ),
        # Slide 4: Gatekeep/CTA - phone screenshot vibe
        (
            f"{candid}{aesthetic} aesthetic, close-up detail shot of a lifestyle moment, "
            f"related to {topic}, shallow depth of field, "
            "warm ambient light, feels like a saved Pinterest pin, no text"
        ),
    ]

    images = []
    for i in range(min(num_slides, len(slide_prompts))):
        img = generate_aesthetic_image(slide_prompts[i])
        images.append(img)

    return images


SCRIPT_SYSTEM_PROMPT = """\
You are an expert TikTok slideshow copywriter specializing in the "Pinterest Aesthetic Slideshow" ad format.

This format disguises ads as aesthetic content. The strategy:
- Slides 1-3 look like organic Pinterest-style tips (the "bait" and "value trap")
- Slide 4 is the "gatekeep" frame that subtly promotes the app as a discovered secret

Rules:
- Write in lowercase, casual tone (like texting a friend)
- Keep text SHORT - each slide text must be readable in 3-4 seconds
- Never use "DOWNLOAD NOW" or obvious ad language
- The app promotion on slide 4 must feel like a personal recommendation, not an ad
- Frame the app as a "secret" or "habit" the creator personally uses
- Use psychological framing: discovery > selling
"""


def generate_slideshow_script(
    app_name: str,
    app_description: str,
    topic: str,
    num_value_slides: int = 2,
) -> dict:
    """Use Gemini to generate the full slideshow script.

    Args:
        app_name: Name of the app to promote (e.g., "HabitAI")
        app_description: Brief description of what the app does
        topic: Content topic/hook theme (e.g., "glow up", "productivity")
        num_value_slides: Number of value/tip slides (default 2)

    Returns:
        Dict with the slideshow structure:
        {
            "hook": {"title": "...", "subtitle": "..."},
            "value_slides": [{"number": 1, "title": "...", "body": "..."}, ...],
            "gatekeep": {"number": 3, "title": "...", "body": "...", "app_mention": "..."},
            "cta": "link in bio"
        }
    """
    client = _get_client()

    user_prompt = f"""\
Generate a TikTok Pinterest-style slideshow script.

App: {app_name}
App description: {app_description}
Topic/Theme: {topic}
Number of value slides: {num_value_slides}

Return ONLY valid JSON in this exact format (no markdown, no code fences):
{{
    "hook": {{
        "title": "the main hook title that makes people stop scrolling",
        "subtitle": "optional subtitle in parentheses for extra intrigue"
    }},
    "value_slides": [
        {{
            "number": 1,
            "title": "short punchy tip title",
            "body": "2-3 sentences expanding on the tip. casual tone. relatable."
        }},
        {{
            "number": 2,
            "title": "another tip title",
            "body": "2-3 sentences. keep it feeling like genuine advice."
        }}
    ],
    "gatekeep": {{
        "number": {num_value_slides + 1},
        "title": "the secret/habit framing title",
        "body": "personal recommendation copy that mentions {app_name} naturally as something you discovered, not an ad. make it feel like sharing a secret with a friend.",
        "app_mention": "{app_name}"
    }},
    "cta": "link in bio"
}}

Important:
- The hook title should be compelling and specific to {topic}
- Value slides should give REAL advice (builds trust before the sell)
- The gatekeep slide must NOT feel like an ad - it's a "secret I use"
- All text should be lowercase casual style
- Keep body text under 30 words per slide
"""

    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=SCRIPT_SYSTEM_PROMPT,
            temperature=0.9,
        ),
    )

    text = response.text.strip()

    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        script = json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from the response
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            script = json.loads(match.group())
        else:
            raise ValueError(f"Failed to parse Gemini response as JSON:\n{text}")

    return script
