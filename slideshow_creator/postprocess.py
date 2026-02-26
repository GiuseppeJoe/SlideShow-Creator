"""Post-processing module - makes AI-generated images look like real phone photos.

AI images are too clean. Real Pinterest/TikTok photos have:
- Sensor noise / film grain
- Slight color temperature shifts
- JPEG compression artifacts from resharing
- Natural lens vignetting
- Minor exposure variance
- Subtle softness in corners

This module applies those imperfections to bypass the "AI look."
"""

import random
from io import BytesIO

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter


def add_film_grain(img: Image.Image, intensity: float = 0.35) -> Image.Image:
    """Add realistic film/sensor grain noise.

    Args:
        img: Input image
        intensity: Grain strength 0.0-1.0 (0.3-0.5 = phone camera range)
    """
    arr = np.array(img, dtype=np.float32)
    noise = np.random.normal(0, intensity * 25, arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def shift_color_temperature(img: Image.Image, warmth: float | None = None) -> Image.Image:
    """Apply a subtle color temperature shift like real ambient lighting.

    Args:
        img: Input image
        warmth: -1.0 (cool/blue) to 1.0 (warm/golden). None = random subtle shift.
    """
    if warmth is None:
        warmth = random.uniform(-0.3, 0.5)  # bias slightly warm (indoor lighting)

    arr = np.array(img, dtype=np.float32)

    # Warm = boost red/green, cool = boost blue
    if warmth > 0:
        arr[:, :, 0] = np.clip(arr[:, :, 0] + warmth * 15, 0, 255)  # red
        arr[:, :, 1] = np.clip(arr[:, :, 1] + warmth * 5, 0, 255)   # green
        arr[:, :, 2] = np.clip(arr[:, :, 2] - warmth * 8, 0, 255)   # blue
    else:
        arr[:, :, 0] = np.clip(arr[:, :, 0] + warmth * 10, 0, 255)
        arr[:, :, 2] = np.clip(arr[:, :, 2] - warmth * 12, 0, 255)

    return Image.fromarray(arr.astype(np.uint8))


def add_vignette(img: Image.Image, strength: float = 0.4) -> Image.Image:
    """Add natural lens vignetting (darker corners).

    Args:
        img: Input image
        strength: Vignette darkness 0.0-1.0 (0.3-0.5 = phone camera range)
    """
    w, h = img.size
    arr = np.array(img, dtype=np.float32)

    # Create radial gradient from center
    y, x = np.ogrid[:h, :w]
    cx, cy = w / 2, h / 2
    # Normalize to 0-1 distance from center
    dist = np.sqrt((x - cx) ** 2 / (cx ** 2) + (y - cy) ** 2 / (cy ** 2))
    # Vignette mask: 1.0 at center, darker at edges
    vignette = 1.0 - np.clip(dist * strength, 0, 0.7)
    vignette = vignette[:, :, np.newaxis]

    arr = np.clip(arr * vignette, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def jpeg_degrade(img: Image.Image, quality: int = 72) -> Image.Image:
    """Simulate JPEG compression artifacts from social media resharing.

    Args:
        img: Input image
        quality: JPEG quality 1-100 (60-80 = reshared photo range)
    """
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    return Image.open(buffer).convert("RGB")


def vary_exposure(img: Image.Image, amount: float | None = None) -> Image.Image:
    """Slightly over/under-expose like a real camera auto-exposure miss.

    Args:
        img: Input image
        amount: Exposure multiplier. None = random subtle variation.
    """
    if amount is None:
        amount = random.uniform(0.92, 1.08)
    enhancer = ImageEnhance.Brightness(img)
    return enhancer.enhance(amount)


def soften_corners(img: Image.Image, radius: float = 1.5) -> Image.Image:
    """Add subtle softness to simulate phone lens imperfections.

    Blurs the image very slightly, mimicking the natural softness
    of a phone camera lens (especially at the edges).
    """
    return img.filter(ImageFilter.GaussianBlur(radius))


def make_realistic(
    img: Image.Image,
    grain: float = 0.30,
    warmth: float | None = None,
    vignette: float = 0.35,
    jpeg_quality: int = 75,
    exposure: float | None = None,
    lens_softness: float = 0.4,
    seed: int | None = None,
) -> Image.Image:
    """Apply the full de-perfecting pipeline to make an AI image look real.

    Each effect is tuned to subtle phone-camera levels by default.
    Set any parameter to 0 / None to skip that effect.

    Args:
        img: AI-generated image to de-perfect
        grain: Film grain intensity (0 to skip)
        warmth: Color temp shift, None for random
        vignette: Vignette strength (0 to skip)
        jpeg_quality: JPEG compression quality (100 to skip)
        exposure: Exposure shift, None for random
        lens_softness: Blur radius for lens softness (0 to skip)
        seed: Random seed for reproducible results

    Returns:
        De-perfected image that looks like a real phone photo
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    # Order matters: grain -> color -> exposure -> softness -> vignette -> jpeg
    if grain > 0:
        img = add_film_grain(img, grain)

    if warmth is not None or True:  # always apply some color shift
        img = shift_color_temperature(img, warmth)

    if exposure is not None or True:
        img = vary_exposure(img, exposure)

    if lens_softness > 0:
        img = soften_corners(img, lens_softness)

    if vignette > 0:
        img = add_vignette(img, vignette)

    if jpeg_quality < 100:
        img = jpeg_degrade(img, jpeg_quality)

    return img
