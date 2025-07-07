import shutil
import tomllib
from datetime import date
from pathlib import Path

import minify_html
import mistletoe
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
CONTENT_DIR = PROJECT_ROOT / "content"
SRC_DIR = PROJECT_ROOT / "src"
BUILD_DIR = PROJECT_ROOT / "build"


def include_raw(file_path: str) -> Markup:
    """
    Returns the contents of the given file as-is without processing it as a jinja template. This is meant to replace the
    built-in {% include "file" %} statement in jinja which looks for files in the templates directory.

    :param file_path: Path of the file relative to the `/src/include` directory. The file being included MUST reside
    inside the include directory.
    :return: Contents of the input file.
    """
    include_path = SRC_DIR / "include"
    file_path = include_path / file_path

    if not file_path.is_relative_to(include_path):
        raise Exception("Reading files outside of the include directory is not allowed.")

    with open(file_path) as file:
        return Markup(file.read())


def make_jinja_env():
    env = Environment(
        loader=FileSystemLoader(SRC_DIR / "templates"),
        autoescape=select_autoescape(["jinja"]),
        trim_blocks=True,
    )

    # Load config
    with open(CONTENT_DIR / "config.toml", "rb") as file:
        cfg = tomllib.load(file)

    if cfg["license"]["start"] != str(current_year := date.today().year):
        cfg["license"]["start"] += f"-{current_year}"

    env.globals.update(cfg)
    env.globals["include_raw"] = include_raw

    return env


def render_markdown(file_path: str | Path) -> str:
    with open(file_path) as file:
        return mistletoe.markdown(file)


def minify(code):
    return minify_html.minify(code, minify_js=True, minify_css=True)


def build_static(minified=True):
    shutil.copytree(SRC_DIR / "static", BUILD_DIR / "static", dirs_exist_ok=True)


def build_home(jinja_env: Environment, recent_posts=None, minified=True):
    content = render_markdown(CONTENT_DIR / "home.md")
    html = jinja_env.get_template("index.jinja").render(content=content, recent_posts=recent_posts)

    if minified:
        html = minify(html)

    with open(BUILD_DIR / "index.html", "w") as file:
        file.write(html)


def build(minified=True):
    env = make_jinja_env()
    build_static(minified)
    build_home(env, minified=minified)


if __name__ == "__main__":
    build()
