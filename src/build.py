import csv
import hashlib
import shutil
import tomllib
from datetime import date
from mimetypes import types_map as mimetype_map
from pathlib import Path

import minify
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
    file_path = (include_path / file_path).resolve()

    if not file_path.is_relative_to(include_path):
        raise Exception("Reading files outside of the include directory is not allowed.")

    with open(file_path) as file:
        return Markup(file.read())


def static_url(file_path: str) -> str:
    """
    Implements cache busting for static assets by appending the first 8 characters of the SHA1 hash of a file to its
    name. It also maintains a CSV file containing:
        name of a file, last modification time of a file, the last SHA1 hash calculated for that file
    which serves as a cache, as recalculating the hash each build is wasteful.

    This is intended to be used both inside Jinja templates and inside `build_static()`.

    :param file_path: Path of the file relative to `/src/static`. File MUST reside inside the static directory.
    :return: Path of the generated static asset relative to the build directory with the first 8 characters of the
    SHA1 hash of that file appended to the file name. Example: "/static/foo-SHA1HASH.bar"bar.
    """

    static_path = SRC_DIR / "static"
    file_path = (static_path / file_path).resolve()

    if not file_path.is_relative_to(static_path):
        raise Exception("static_url must be called only for files inside the static directory.")


def load_config():
    with open(CONTENT_DIR / "config.toml", "rb") as file:
        cfg = tomllib.load(file)

    if cfg["license"]["start"] != str(current_year := date.today().year):
        cfg["license"]["start"] += f"-{current_year}"

    return cfg


def make_jinja_env():
    env = Environment(
        loader=FileSystemLoader(SRC_DIR / "templates"),
        autoescape=select_autoescape(["jinja"]),
        trim_blocks=True,
    )

    env.globals.update(load_config())
    env.globals["include_raw"] = include_raw

    return env


def render_markdown(file_path: str | Path) -> str:
    with open(file_path) as file:
        return mistletoe.markdown(file)


def build_static(minified=True):
    static_dir = SRC_DIR / "static"
    build_dir = BUILD_DIR / "static"

    # Copy everything as it is first, then if minification is enabled do a second pass for html, css, js and svg files.
    # The benefit of this approach is that the correct directory structure will be created beforehand in the build
    # directory.
    shutil.copytree(static_dir, build_dir)

    if not minified:
        return

    for file in static_dir.rglob("*"):
        if file.is_dir():
            continue

        filetype = file.suffix.lstrip(".")

        if filetype == "woff2":
            # TODO: Implement font subsetting.
            pass

        if filetype not in ("html", "css", "js", "svg"):
            continue

        dst_path = build_dir / file.relative_to(static_dir)

        with open(file) as src_file:
            code = src_file.read()

        with open(dst_path, "w") as dst_file:
            dst_file.write(minify.string(mimetype_map[file.suffix], code))


def build_home(jinja_env: Environment, recent_posts=None, minified=True, live=False):
    content = None
    content_filepath = CONTENT_DIR / "home.md"
    if content_filepath.exists():
        content = render_markdown(content_filepath)

    html = jinja_env.get_template("index.jinja").render(content=content, recent_posts=recent_posts)

    if minified:
        html = minify.string(mimetype_map[".html"], html)

    if live:
        return html

    with open(BUILD_DIR / "index.html", "w") as file:
        file.write(html)
    return None


def build(minified=True):
    env = make_jinja_env()
    if BUILD_DIR.exists():
        # This is necessary as deleted files will be preserved from previous builds otherwise.
        shutil.rmtree(BUILD_DIR)
    build_static(minified)
    build_home(env, minified=minified)

    # TODO: Implement blog, projects and more pages.
    for page_name in ("blog", "projects", "more"):
        build_path = BUILD_DIR / f"{page_name}/index.html"
        build_path.parent.mkdir(parents=True, exist_ok=True)
        with open(build_path, "w") as file:
            file.write(env.get_template("base.jinja").render(
                selected_tab=page_name,
                content='<main><article><p class="placeholder-text">As I said, this is still a work in '
                        'progress.</p></article><aside></aside></main>'
            ))


if __name__ == "__main__":
    build()
