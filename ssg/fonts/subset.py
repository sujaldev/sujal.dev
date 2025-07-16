import shutil
from copy import deepcopy
from pathlib import Path
from typing import List

from fontTools.subset import main as subset
from fontTools.ttLib import TTFont
from jinja2 import Environment, DictLoader

SRC_DIR = Path(__file__).parent.parent.resolve()
INPUT_FONT_DIR = SRC_DIR / "fonts/"
OUTPUT_FONT_DIR = SRC_DIR / "static/fonts/"

WOFF_DIR = OUTPUT_FONT_DIR / "WOFF"
WOFF2_DIR = OUTPUT_FONT_DIR / "WOFF2"


def all_chars(input_font: Path) -> set:
    # Returns all characters defined in a font.
    return set(TTFont(input_font).getBestCmap())


def group_nums(nums: List[int]) -> List[str]:
    """
    Groups consecutive numbers in a sorted list of integers.
    Example: [1, 2, 3, 5, 7, 8, 9] -> ["0001-0003", "0005", "0007-0009"]
    """

    length = len(nums)
    groups = []
    start = None
    i = 0

    while i < length:
        if start is None:
            start = nums[i]

        while (i + 1) < length and nums[i] + 1 == nums[i + 1]:
            i += 1

        end = nums[i]

        groups.append(
            f"{start:0>4X}"
            if start == end else
            f"{start:0>4X}-{end:0>4X}"
        )

        start = None
        i += 1

    return groups


def remaining_blocks(input_font: Path) -> list:
    """
    Calculates the Unicode ranges left after removing Basic Latin and Latin Supplement blocks from a font.

    The reason to not use the much simpler U+100-10FFFF range instead is that the output from this function can be
    passed to the stylesheet as a more accurate value for the unicode-range property. A precise value is beneficial as
    it will prevent unnecessary downloads due to glyphs that aren't defined in the font but are still covered by the
    broad U+100-10FFFF range.
    """
    blacklist = range(0x0, 0xFF + 0x1)
    remaining_chars = [char for char in all_chars(input_font) if char not in blacklist]
    return group_nums(remaining_chars)


def subset_to_woff_and_woff2(input_font: Path, output_font_name: str, unicode_range: str):
    subset(args=[
        str(input_font),
        "--output-file=" + str(WOFF2_DIR / f"{output_font_name}.woff2"),
        f"--unicodes={unicode_range}",
        "--flavor=woff2",
        "--layout-features=*",
    ])

    subset(args=[
        str(input_font),
        "--output-file=" + str(WOFF_DIR / f"{output_font_name}.woff"),
        f"--unicodes={unicode_range}",
        "--flavor=woff",
        "--layout-features=*",
    ])


def build_libertinus(input_font_dir: Path, subsets: dict, css_only=False):
    defaults = {
        "LibertinusMath-Regular.woff2": {
            "family": "Libertinus Math",
            "sources": [],
        },
        "LibertinusMono-Regular.woff2": {
            "family": "Libertinus Mono",
            "sources": [],
        },
        "LibertinusSans-Regular.woff2": {
            "family": "Libertinus Sans",
            "sources": [],
        },
        "LibertinusSans-Bold.woff2": {
            "family": "Libertinus Sans",
            "sources": [],
            "weight": "bold",
        },
        "LibertinusSans-Italic.woff2": {
            "family": "Libertinus Sans",
            "sources": [],
            "style": "italic",
        },
    }
    css_props = []

    for font in input_font_dir.rglob("*.woff2"):
        print(f"Subsetting {font.name}: ", end="")

        # TODO: Not sure if I should subset the math font, so it remains a special case for now.
        if "math" in font.name.lower():
            if not css_only:
                subset_to_woff_and_woff2(font, font.stem, "0000-10FFFF")

            css_props.append(deepcopy(defaults[font.name]))
            css_props[-1]["sources"].extend([
                (f"fonts/WOFF2/{font.name}", "woff2"),
                (f"fonts/WOFF/{font.with_suffix('.woff').name}", "woff"),
            ])
            print()
            continue

        for block_name, unicode_range in subsets.items():
            css_props.append(deepcopy(defaults[font.name]))
            print(block_name, end=" ")

            if callable(unicode_range):
                unicode_range = unicode_range(font)
                css_props[-1]["unicode_range"] = "U+" + ", U+".join(unicode_range)
                unicode_range = ",".join(unicode_range)
            else:
                unicode_range = f"{unicode_range[0]:0>4X}-{unicode_range[1]:0>4X}"
                css_props[-1]["unicode_range"] = "U+" + unicode_range

            output_name = f"{font.stem}-{block_name}"
            if not css_only:
                subset_to_woff_and_woff2(font, output_name, unicode_range)

            css_props[-1]["sources"].extend([
                (f"fonts/WOFF2/{output_name}.woff2", "woff2"),
                (f"fonts/WOFF/{output_name}.woff", "woff"),
            ])

        print()

    # Render font-faces stylesheet
    with open(INPUT_FONT_DIR / "font-faces.css.jinja") as file:
        env = Environment(
            loader=DictLoader({"font-faces": file.read()}),
            lstrip_blocks=True,
            trim_blocks=True,
        )

    env.globals["fonts"] = css_props

    with open(SRC_DIR / "templates/font-faces.css.jinja", "w") as file:
        file.write(env.get_template("font-faces").render())


def build(css_only=False):
    # Clean output directory
    if not css_only and OUTPUT_FONT_DIR.exists():
        shutil.rmtree(OUTPUT_FONT_DIR)
    WOFF_DIR.mkdir(parents=True, exist_ok=True)
    WOFF2_DIR.mkdir(exist_ok=True)

    build_libertinus(INPUT_FONT_DIR / "Libertinus", {
        "basic": (0x0, 0xFF),
        "extras": remaining_blocks
    }, css_only)


if __name__ == "__main__":
    build()
