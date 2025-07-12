import shutil
from pathlib import Path

from fontTools.subset import main as subset
from fontTools.ttLib import TTFont

SRC_DIR = Path(__file__).parent.parent.resolve()
INPUT_FONT_DIR = SRC_DIR / "fonts/"
OUTPUT_FONT_DIR = SRC_DIR / "static/fonts/"

WOFF_DIR = OUTPUT_FONT_DIR / "WOFF"
WOFF2_DIR = OUTPUT_FONT_DIR / "WOFF2"


def remaining_blocks(input_font: Path) -> str:
    """
    Calculates the Unicode ranges left after removing Basic Latin and Latin Supplement blocks from a font.

    The reason to not use the much simpler U+100-10FFFF range instead is that the output from this function can be
    passed to the stylesheet as a more accurate value for the unicode-range property. A precise value is beneficial as
    it will prevent unnecessary downloads due to glyphs that aren't defined in the font but are still covered by the
    broad U+100-10FFFF range.
    """

    font = TTFont(input_font)
    all_unicodes = sorted(set([
        char for char in font.getBestCmap()
        if char not in range(0x0, 0xFF + 0x1)
    ]))

    # Group chars into ranges.
    char_count = len(all_unicodes)
    ranges = []
    start = None
    i = 0
    while i < char_count:
        if start is None:
            start = all_unicodes[i]

        while (i + 1) < char_count and all_unicodes[i] + 1 == all_unicodes[i + 1]:
            i += 1

        end = all_unicodes[i]

        ranges.append(f"{start:0>4X}" if start == end else f"{start:0>4X}-{end:0>4X}")

        start = None
        i += 1

    # print("U+" + ",U+".join(ranges))
    return ",".join(ranges)


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


def build_libertinus(input_font_dir: Path, subsets: dict):
    for font in input_font_dir.rglob("*.woff2"):
        print(f"Subsetting {font.name}: ", end="")

        # TODO: Not sure if I should subset the math font, so it remains a special case for now.
        if "math" in font.name.lower():
            subset_to_woff_and_woff2(font, font.stem, "0000-10FFFF")
            print()
            continue

        for block_name, unicode_range in subsets.items():
            print(block_name, end=" ")

            if callable(unicode_range):
                unicode_range = unicode_range(font)
            else:
                unicode_range = f"{unicode_range[0]:0>4X}-{unicode_range[1]:0>4X}"

            subset_to_woff_and_woff2(font, f"{font.stem}-{block_name}", unicode_range)

        print()


def build():
    # Clean output directory
    if OUTPUT_FONT_DIR.exists():
        shutil.rmtree(OUTPUT_FONT_DIR)
    WOFF_DIR.mkdir(parents=True)
    WOFF2_DIR.mkdir()

    build_libertinus(INPUT_FONT_DIR / "Libertinus", {
        "basic": (0x0, 0xFF),
        "extras": remaining_blocks
    })


if __name__ == "__main__":
    build()
