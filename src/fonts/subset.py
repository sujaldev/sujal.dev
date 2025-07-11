import shutil
from pathlib import Path

from fontTools.subset import main as subset

SRC_DIR = Path(__file__).parent.parent.resolve()

BASIC_LATIN = "0000-007F"
LATIN_SUPPLEMENT = "0080-00FF"
EVERYTHING_ELSE = "0100-10FFFF"


def build_libertinus(input_font_dir: Path, output_font_dir: Path):
    # Clean output directory
    if output_font_dir.exists():
        shutil.rmtree(output_font_dir)
    output_font_dir.mkdir(parents=True, exist_ok=True)

    for font in ("Sans-Regular", "Sans-Italic", "Sans-Bold", "Mono-Regular"):
        input_font = input_font_dir / f"Libertinus{font}.woff2"

        for i, block in enumerate((BASIC_LATIN, LATIN_SUPPLEMENT, EVERYTHING_ELSE)):
            subset(args=[
                str(input_font),
                "--output-file=" + str(output_font_dir / f"{font}-{i + 1}.woff2"),
                f"--unicodes={block}",
                "--flavor=woff2",
                "--layout-features='*'",
            ])

    # TODO: Figure out what to do regarding the math font.
    shutil.copyfile(input_font_dir / "LibertinusMath-Regular.woff2", output_font_dir / "Math-Regular.woff2")


if __name__ == "__main__":
    build_libertinus(SRC_DIR / "fonts/Libertinus", SRC_DIR / "static/fonts/Libertinus")
