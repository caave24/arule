#!/usr/bin/env python3

from pathlib import Path
import json
import re

from PIL import Image, ImageOps


# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

SOURCE_DIR = ROOT / "source"
OUTPUT_DIR = ROOT / "bgs"

CONFIG_PATH = ROOT / "configs" / "backgrounds.json"


# --------------------------------------------------
# OPTIMIZATION SETTINGS
# --------------------------------------------------

# Images larger than this are proportionally reduced.
# The longest side is capped at this value.
MAX_LONG_EDGE = 2560

# Good balance between visual quality and file size.
WEBP_QUALITY = 82

# Pillow compression effort.
# 0 = fastest / least compression
# 6 = slowest / best compression
WEBP_METHOD = 6


# --------------------------------------------------
# SUPPORTED SOURCE FORMATS
# --------------------------------------------------

VALID_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".tif",
    ".tiff",
}


# --------------------------------------------------
# FILENAME NORMALIZATION
# --------------------------------------------------

def normalized_name(path):
    """
    Normalize a filename stem for matching.

    Examples:

        Space Photo.jpg
        space-photo.webp

        -> space-photo


        bear_cub.png
        bear-cub.webp

        -> bear-cub
    """

    name = path.stem.lower()

    name = re.sub(
        r"[^a-z0-9]+",
        "-",
        name,
    )

    return name.strip("-")


def output_name(source):
    """
    Generate the optimized WebP filename.

    The optimized filename uses the normalized source name.

    Example:

        26447766349_22c8e2b0bb_o.jpg

        becomes:

        26447766349-22c8e2b0bb-o.webp
    """

    return (
        normalized_name(source)
        + ".webp"
    )


# --------------------------------------------------
# FILE SIZE FORMATTING
# --------------------------------------------------

def format_size(size):

    units = [
        "B",
        "KB",
        "MB",
        "GB",
    ]

    value = float(size)

    for unit in units:

        if value < 1024:

            return (
                f"{value:.1f} "
                f"{unit}"
            )

        value /= 1024

    return (
        f"{value:.1f} TB"
    )


# --------------------------------------------------
# IMAGE RESIZING
# --------------------------------------------------

def resize_preserving_aspect_ratio(image):
    """
    Resize only when the image's longest edge is larger
    than MAX_LONG_EDGE.

    This function never:

    - stretches
    - distorts
    - crops
    - changes aspect ratio
    - enlarges smaller images
    """

    width, height = image.size

    longest_edge = max(
        width,
        height,
    )

    # Do not enlarge smaller images.
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


# --------------------------------------------------
# IMAGE PREPARATION
# --------------------------------------------------

def prepare_image(image):
    """
    Correct orientation and prepare the image for WebP.
    """

    # Correct EXIF/camera rotation.
    image = ImageOps.exif_transpose(
        image
    )

    # Preserve transparency if present.
    #
    # WebP supports alpha, so there is no reason to
    # flatten transparent PNGs onto black.
    if image.mode in (
        "RGBA",
        "LA",
    ):

        return image.convert(
            "RGBA"
        )

    # Palette images with transparency.
    if (
        image.mode == "P"
        and "transparency" in image.info
    ):

        return image.convert(
            "RGBA"
        )

    # Standard photographic backgrounds.
    return image.convert(
        "RGB"
    )


# --------------------------------------------------
# OUTPUT VERIFICATION
# --------------------------------------------------

def verify_image(path):
    """
    Verify that the generated image:

    - exists
    - is not empty
    - can be opened by Pillow
    """

    if not path.exists():

        print(
            f"Verification failed: "
            f"{path.name} does not exist."
        )

        return False

    if path.stat().st_size <= 0:

        print(
            f"Verification failed: "
            f"{path.name} is empty."
        )

        return False

    try:

        with Image.open(path) as image:

            image.verify()

        return True

    except Exception as error:

        print(
            f"Verification failed for "
            f"{path.name}: {error}"
        )

        return False


# --------------------------------------------------
# MATCHING OUTPUT CHECK
# --------------------------------------------------

def has_matching_output(source):
    """
    Check whether bgs/ contains a verified file with
    the same normalized name as the source image.

    File extension does not matter.

    Example:

        source:
        image_name.jpg

        output:
        image-name.webp

        -> MATCH
    """

    source_name = normalized_name(
        source
    )

    for output in OUTPUT_DIR.iterdir():

        # Ignore directories, including bgs/source.
        if not output.is_file():

            continue

        # Ignore source files and unrelated formats.
        if output.suffix.lower() != ".webp":

            continue

        output_name_normalized = (
            normalized_name(output)
        )

        if (
            output_name_normalized
            == source_name
        ):

            if verify_image(output):

                return True

    return False


# --------------------------------------------------
# OPTIMIZATION
# --------------------------------------------------

def optimize_image(source):

    destination = (
        OUTPUT_DIR
        / output_name(source)
    )

    original_file_size = (
        source.stat().st_size
    )

    with Image.open(source) as image:

        # Normalize orientation and mode.
        image = prepare_image(
            image
        )

        original_dimensions = (
            image.size
        )

        # Proportional resize.
        image = (
            resize_preserving_aspect_ratio(
                image
            )
        )

        optimized_dimensions = (
            image.size
        )

        # Save optimized WebP.
        image.save(
            destination,
            "WEBP",
            quality=WEBP_QUALITY,
            method=WEBP_METHOD,
        )

    # Verify generated output before proceeding.
    if not verify_image(destination):

        raise RuntimeError(
            f"Generated image failed verification: "
            f"{destination.name}"
        )

    optimized_file_size = (
        destination.stat().st_size
    )

    saved_bytes = (
        original_file_size
        - optimized_file_size
    )

    if original_file_size > 0:

        saved_percent = (
            saved_bytes
            / original_file_size
            * 100
        )

    else:

        saved_percent = 0

    print()

    print(
        f"Optimized: "
        f"{source.name}"
    )

    print(
        f"Dimensions: "
        f"{original_dimensions[0]}×"
        f"{original_dimensions[1]}"
        f" → "
        f"{optimized_dimensions[0]}×"
        f"{optimized_dimensions[1]}"
    )

    print(
        f"Size: "
        f"{format_size(original_file_size)}"
        f" → "
        f"{format_size(optimized_file_size)}"
    )

    print(
        f"Saved: "
        f"{format_size(abs(saved_bytes))}"
        f" "
        f"({saved_percent:.1f}%)"
    )

    print(
        f"Output: "
        f"{destination.relative_to(ROOT)}"
    )

    return destination


# --------------------------------------------------
# SOURCE CLEANUP
# --------------------------------------------------

def delete_source_if_matching(source):
    """
    Delete the original source image only when a verified
    WebP with the same normalized filename exists in bgs/.
    """

    if has_matching_output(source):

        source.unlink()

        print(
            f"Deleted source: "
            f"{source.relative_to(ROOT)}"
        )

        return True

    print(
        f"Keeping source: "
        f"{source.relative_to(ROOT)}"
    )

    print(
        "Reason: no verified matching "
        "optimized WebP was found."
    )

    return False


# --------------------------------------------------
# BACKGROUND CONFIG GENERATION
# --------------------------------------------------

def generate_background_config():
    """
    Regenerate configs/backgrounds.json using all
    optimized WebP files directly inside bgs/.
    """

    images = sorted(

        file

        for file in OUTPUT_DIR.iterdir()

        if (
            file.is_file()
            and file.suffix.lower()
            == ".webp"
        )

    )

    config = {

        "_comment": (
            "AUTO-GENERATED by "
            "scripts/optimize_backgrounds.py. "
            "Add originals to source/."
        ),

        "changeEveryMs": 45000,

        "transitionDurationMs": 1800,

        "images": [

            f"./bgs/{image.name}"

            for image in images

        ],

    }

    CONFIG_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    CONFIG_PATH.write_text(

        json.dumps(
            config,
            indent=2,
        )
        + "\n",

        encoding="utf-8",
    )

    print()

    print(
        f"Updated: "
        f"{CONFIG_PATH.relative_to(ROOT)}"
    )

    print(
        f"Background count: "
        f"{len(images)}"
    )


# --------------------------------------------------
# MAIN
# --------------------------------------------------

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

        for file in SOURCE_DIR.iterdir()

        if (
            file.is_file()
            and file.suffix.lower()
            in VALID_EXTENSIONS
        )

    )

    if not source_files:

        print(
            "No source images found in "
            "source/."
        )

        # Still regenerate the config from existing WebPs.
        generate_background_config()

        return

    print(
        f"Found "
        f"{len(source_files)} "
        f"source image(s)."
    )

    successful = 0

    for source in source_files:

        try:

            optimize_image(
                source
            )

            if delete_source_if_matching(
                source
            ):

                successful += 1

        except Exception as error:

            print()

            print(
                f"WARNING: "
                f"Could not process "
                f"{source.name}"
            )

            print(
                f"Error: {error}"
            )

            print(
                "The original source file "
                "was kept."
            )

    # Rebuild the JSON config from all optimized WebPs.
    generate_background_config()

    print()

    print(
        "Optimization complete."
    )

    print(
        f"Successfully processed: "
        f"{successful}/"
        f"{len(source_files)}"
    )


if __name__ == "__main__":
    main()
