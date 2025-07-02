import tomllib
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
CONTENT_DIR = PROJECT_ROOT / "content"
SRC_DIR = PROJECT_ROOT / "src"


def include_raw(file_path: str) -> Markup:
    """
    Replacement for {% include "file" %} tag, without processing "file" as a template.

    :param file_path: path of the file relative to the `/src/include` directory. The file being included must reside
    inside the include directory.
    :return: Escaped contents of the file.
    """
    include_path = SRC_DIR / "include"
    file_path = include_path / file_path

    if not file_path.is_relative_to(include_path):
        raise Exception("Reading files outside of the include directory is not allowed.")

    with open(file_path) as file:
        return Markup(file.read())


def main():
    env = Environment(
        loader=FileSystemLoader(PROJECT_ROOT / "src/templates"),
        autoescape=select_autoescape(["jinja2"]),
        trim_blocks=True,
    )

    # Load config
    with open(CONTENT_DIR / "config.toml", "rb") as file:
        cfg = tomllib.load(file)

    if cfg["license"]["start"] != str(current_year := date.today().year):
        cfg["license"]["start"] += f"-{current_year}"

    env.globals.update(cfg)
    env.globals["include_raw"] = include_raw


if __name__ == "__main__":
    main()
