"""Image sourcing module - fetches aesthetic images from Unsplash or loads local files."""

import os
import hashlib
from pathlib import Path
from io import BytesIO

import requests
from PIL import Image


UNSPLASH_API_URL = "https://api.unsplash.com/search/photos"

# Curated search term mappings for aesthetic categories
AESTHETIC_QUERIES = {
    "old_money": "old money aesthetic luxury lifestyle",
    "clean_girl": "clean girl aesthetic minimal skincare",
    "that_girl": "that girl morning routine aesthetic",
    "glow_up": "glow up transformation aesthetic",
    "beach": "aesthetic beach sunset golden hour",
    "morning": "aesthetic morning routine cozy",
    "kitchen": "aesthetic kitchen healthy food",
    "fitness": "aesthetic gym fitness lifestyle",
    "study": "aesthetic study desk cozy",
    "travel": "luxury travel aesthetic hotel",
    "fashion": "aesthetic fashion outfit minimal",
    "nature": "aesthetic nature peaceful landscape",
    "city": "aesthetic city night lights",
    "cozy": "cozy aesthetic warm blanket coffee",
    "minimal": "minimal aesthetic white clean",
}

CACHE_DIR = Path.home() / ".slideshow_creator" / "image_cache"


def _ensure_cache_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_key(query: str, index: int) -> str:
    h = hashlib.md5(f"{query}:{index}".encode()).hexdigest()
    return f"{h}.jpg"


def fetch_unsplash_image(
    query: str,
    api_key: str,
    index: int = 0,
    orientation: str = "portrait",
) -> Image.Image:
    """Fetch an image from Unsplash API.

    Args:
        query: Search query (can be a key from AESTHETIC_QUERIES or freeform text)
        api_key: Unsplash API access key
        index: Which result to pick (0 = first result)
        orientation: Image orientation (portrait for TikTok 9:16)

    Returns:
        PIL Image object
    """
    _ensure_cache_dir()

    resolved_query = AESTHETIC_QUERIES.get(query, query)
    cache_file = CACHE_DIR / _cache_key(resolved_query, index)

    if cache_file.exists():
        return Image.open(cache_file).convert("RGB")

    params = {
        "query": resolved_query,
        "orientation": orientation,
        "per_page": max(index + 1, 10),
        "page": 1,
    }
    headers = {"Authorization": f"Client-ID {api_key}"}

    resp = requests.get(UNSPLASH_API_URL, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    results = resp.json().get("results", [])

    if not results or index >= len(results):
        raise ValueError(
            f"No Unsplash results for '{resolved_query}' at index {index}"
        )

    image_url = results[index]["urls"]["regular"]
    img_resp = requests.get(image_url, timeout=30)
    img_resp.raise_for_status()

    img = Image.open(BytesIO(img_resp.content)).convert("RGB")

    img.save(cache_file, "JPEG", quality=90)
    return img


def load_local_image(path: str) -> Image.Image:
    """Load an image from a local file path."""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Image not found: {path}")
    return Image.open(path).convert("RGB")


def resolve_image(
    source: str,
    api_key: str | None = None,
    index: int = 0,
) -> Image.Image:
    """Resolve an image source string to a PIL Image.

    Source formats:
        - "unsplash:beach sunset" -> Unsplash API search
        - "aesthetic:old_money" -> Curated aesthetic category via Unsplash
        - "/path/to/image.jpg" -> Local file
        - "beach" (key from AESTHETIC_QUERIES) -> Curated search via Unsplash

    Args:
        source: Image source string
        api_key: Unsplash API key (required for Unsplash sources)
        index: Which search result to use

    Returns:
        PIL Image object
    """
    if source.startswith("unsplash:"):
        query = source[len("unsplash:"):]
        if not api_key:
            raise ValueError("Unsplash API key required. Set UNSPLASH_API_KEY env var.")
        return fetch_unsplash_image(query, api_key, index=index)

    if source.startswith("aesthetic:"):
        category = source[len("aesthetic:"):]
        if category not in AESTHETIC_QUERIES:
            raise ValueError(
                f"Unknown aesthetic: '{category}'. "
                f"Available: {', '.join(AESTHETIC_QUERIES.keys())}"
            )
        if not api_key:
            raise ValueError("Unsplash API key required. Set UNSPLASH_API_KEY env var.")
        return fetch_unsplash_image(category, api_key, index=index)

    if os.path.exists(os.path.expanduser(source)):
        return load_local_image(source)

    if source in AESTHETIC_QUERIES:
        if not api_key:
            raise ValueError("Unsplash API key required. Set UNSPLASH_API_KEY env var.")
        return fetch_unsplash_image(source, api_key, index=index)

    if api_key:
        return fetch_unsplash_image(source, api_key, index=index)

    raise ValueError(
        f"Cannot resolve image source '{source}'. "
        "Provide a local file path, or set UNSPLASH_API_KEY for web sourcing."
    )
