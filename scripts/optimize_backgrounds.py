from pathlib import Path
import json
import re

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]

SOURCE_DIR = ROOT / "bgs" / "source"
OUTPUT_DIR = ROOT / "bgs"
CONFIG_PATH = ROOT / "configs" / "backgrounds.json"


# Maximum size of either dimension.
# Images retain their original aspect ratio.
MAX_LONG_EDGE = 2560

# WebP quality: good visual quality with significant file-size reduction.
WEBP_QUALITY = 82

VALID_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".tif",
    ".tiff",
}


def safe_name(path):
    """Create a predictable web-safe filename."""

    name = path.stem.lower()

    name = re.sub(
        r"[^a-z0-9]+",
        "-",
        name,
    )

    name = name.strip("-")

    return name or "background"


def resize_preserving_aspect_ratio(image):
    """
    Reduce an image only when its longest edge exceeds MAX_LONG_EDGE.

    This never:
    - stretches the image
    - crops the image
    - changes its aspect ratio
    - enlarges smaller images
    """

    width, height = image.size

    longest_edge = max(
        width,
        height,
    )

    # Leave smaller images completely alone.
    if longest_edge <= MAX_LONG_EDGE:
        return image

    scale = (
        MAX_LONG_EDGE
        / longest_edge
    )

    new_width = round(
        width * scale
    )

    new_height = round(
        height * scale
    )

    return image.resize(
        (
            new_width,
            new_height,
        ),
        Image.Resampling.LANCZOS,
    )


def prepare_image(image):
    """
    Normalize the image before optimization.
    """

    # Correct camera/EXIF rotation.
    image = ImageOps.exif_transpose(
        image
    )

    # Convert everything to RGB for photographic WebP output.
    #
    # Transparent images are composited onto black.
    if (
        image.mode in ("RGBA", "LA")
        or (
            image.mode == "P"
            and "transparency" in image.info
        )
    ):

        rgba = image.convert(
            "RGBA"
        )

        background = Image.new(
            "RGB",
            image.size,
            (0, 0, 0),
        )

        background.paste(
            rgba,
            mask=rgba.getchannel("A"),
        )

        return background

    return image.convert(
        "RGB"
    )


def optimize_image(source):

    output_name = (
        f"{safe_name(source)}.webp"
    )

    output = (
        OUTPUT_DIR
        / output_name
    )

    with Image.open(source) as image:

        # Fix orientation.
        image = ImageOps.exif_transpose(
            image
        )

        # Normalize format.
        image = prepare_image(
            image
        )

        original_size = image.size

        # Resize proportionally.
        image = resize_preserving_aspect_ratio(
            image
        )

        optimized_size = image.size

        # Re-encode as optimized WebP.
        image.save(
            output,
            "WEBP",
            quality=WEBP_QUALITY,
            method=6,
        )

    print(
        f"Optimized: "
        f"{source.name}"
    )

    print(
        f"  {original_size[0]}×{original_size[1]}"
        f" → "
        f"{optimized_size[0]}×{optimized_size[1]}"
    )

    return output


def main():

    SOURCE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    source_files = sorted(
        file
        for file in SOURCE_DIR.rglob("*")
        if (
            file.is_file()
            and file.suffix.lower()
            in VALID_EXTENSIONS
        )
    )

    optimized_files = []

    for source in source_files:

        try:

            optimized = optimize_image(
                source
            )

            optimized_files.append(
                optimized
            )

        except Exception as error:

            print(
                f"WARNING: "
                f"Could not process "
                f"{source}: "
                f"{error}"
            )

    # Automatically regenerate the background list.
    config = {

        "_comment": (
            "AUTO-GENERATED. "
            "Add original images to "
            "bgs/source/ and push to main."
        ),

        "changeEveryMs": 45000,

        "transitionDurationMs": 1800,

        "images": [

            f"./bgs/{image.name}"

            for image in optimized_files

        ],

    }

    CONFIG_PATH.write_text(
        json.dumps(
            config,
            indent=2,
        )
        + "\\n",

        encoding="utf-8",
    )

    print(
        f"Updated "
        f"{CONFIG_PATH.relative_to(ROOT)}"
    )

    print(
        f"{len(optimized_files)} "
        f"background(s) ready."
    )


if __name__ == "__main__":
    main()
