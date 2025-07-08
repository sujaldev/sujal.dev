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


def minify(code, lang="html"):
    if lang == "css":
        code = f"<style>\n{code}\n</style>"
        return minify_html.minify(code, minify_css=True).lstrip("<style>").rstrip("</style>")
    elif lang == "js":
        code = f"<script>\n{code}\n</script>"
        return minify_html.minify(code, minify_js=True).lstrip("<script>").rstrip("</script>")
    elif lang == "svg":
        # TODO: Implement svg minification.
        return code
    else:
        return minify_html.minify(code, minify_js=True, minify_css=True)


def build_static(minified=True):
    static_dir = SRC_DIR / "static"
    build_dir = BUILD_DIR / "static"

    # Copy everything as it is first, then if minification is enabled do a second pass for html, css, js and svg files.
    # The benefit of this approach is that the correct directory structure will be created beforehand in the build
    # directory.
    if build_dir.exists():
        # This is necessary as deleted files will be preserved from previous builds otherwise.
        shutil.rmtree(build_dir)
    shutil.copytree(static_dir, build_dir)

    if not minified:
        return

    for file in static_dir.rglob("*"):
        if file.is_dir():
            continue

        filetype = file.suffix.lstrip(".")
        if filetype not in ("html", "css", "js", "svg"):
            continue

        dst_path = build_dir / file.relative_to(static_dir)

        with open(file) as src_file:
            code = src_file.read()

        with open(dst_path, "w") as dst_file:
            dst_file.write(minify(code, lang=filetype))


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
