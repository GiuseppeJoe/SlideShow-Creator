from setuptools import setup, find_packages

setup(
    name="slideshow-creator",
    version="1.0.0",
    description="Automated Pinterest-style TikTok slideshow generator for app promotion",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "Pillow>=10.0.0",
        "requests>=2.28.0",
        "PyYAML>=6.0",
        "google-genai>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "slideshow-creator=slideshow_creator.cli:main",
        ],
    },
)
