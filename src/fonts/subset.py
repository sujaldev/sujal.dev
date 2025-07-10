import shutil
from pathlib import Path

from fontTools.subset import main as subset

SRC_DIR = Path(__file__).parent.parent.resolve()
INPUT_FONT_DIR = SRC_DIR / "fonts"
OUTPUT_FONT_DIR = SRC_DIR / "static/fonts/Libertinus"

BASIC_LATIN = "0000-007F"
LATIN_SUPPLEMENT = "0080-00FF"
EVERYTHING_ELSE = "0100-10FFFF"


def build_libertinus():
    # Clean output directory
    if OUTPUT_FONT_DIR.exists():
        shutil.rmtree(OUTPUT_FONT_DIR)
    OUTPUT_FONT_DIR.mkdir(parents=True, exist_ok=True)

    for font in ("Sans-Regular", "Sans-Italic", "Sans-Bold", "Mono-Regular"):
        input_font = INPUT_FONT_DIR / f"Libertinus{font}.woff2"

        for i, block in enumerate((BASIC_LATIN, LATIN_SUPPLEMENT, EVERYTHING_ELSE)):
            subset(args=[
                str(input_font),
                "--output-file=" + str(OUTPUT_FONT_DIR / f"{font}-{i + 1}.woff2"),
                f"--unicodes={block}",
                "--flavor=woff2",
                "--layout-features='*'",
            ])

    # TODO: Figure out what to do regarding the math font.
    shutil.copyfile(INPUT_FONT_DIR / "LibertinusMath-Regular.woff2", OUTPUT_FONT_DIR / "Math-Regular.woff2")


if __name__ == "__main__":
    build_libertinus()
