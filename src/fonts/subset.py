import shutil
from pathlib import Path

from fontTools.subset import main as subset
from fontTools.ttLib import TTFont

SRC_DIR = Path(__file__).parent.parent.resolve()


def remaining_blocks(input_font: Path) -> str:
    # Calculates the Unicode ranges left after removing basic-latin and latin-supplement from a font.
    # The reason to not use the much simpler 0x100-0x10FFFF range instead is that the output from this function can be
    # passed to the stylesheet as a more accurate value for the unicode-ranges property.

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

    return ",".join(ranges)


unicode_blocks = {
    "basic-latin": (0x0, 0x7F),
    "latin-supplement": (0x80, 0xFF),
    "extras": remaining_blocks
}


def build_libertinus(input_font_dir: Path, output_font_dir: Path):
    # Clean output directory
    if output_font_dir.exists():
        shutil.rmtree(output_font_dir)
    output_font_dir.mkdir(parents=True, exist_ok=True)

    for font in ("Sans-Regular", "Sans-Italic", "Sans-Bold", "Mono-Regular"):
        input_font = input_font_dir / f"Libertinus{font}.woff2"

        for block_name, unicode_range in unicode_blocks.items():
            if callable(unicode_range):
                unicode_range = unicode_range(input_font)
            else:
                unicode_range = f"{unicode_range[0]:0>4X}-{unicode_range[1]:0>4X}"

            subset(args=[
                str(input_font),
                "--output-file=" + str(output_font_dir / f"{font}-{block_name}.woff2"),
                f"--unicodes={unicode_range}",
                "--flavor=woff2",
                "--layout-features='*'",
            ])

            print(f"Libertinus{font}-{block_name}.woff2 generated.")

    # TODO: Figure out what to do regarding the math font.
    shutil.copyfile(input_font_dir / "LibertinusMath-Regular.woff2", output_font_dir / "Math-Regular.woff2")


if __name__ == "__main__":
    build_libertinus(SRC_DIR / "fonts/Libertinus", SRC_DIR / "static/fonts/Libertinus")
