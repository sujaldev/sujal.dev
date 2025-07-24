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

__all__ = [
    "load_config", "make_jinja_env", "build_home", "build_blog",
]

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
CONTENT_DIR = PROJECT_ROOT / "content"
SRC_DIR = PROJECT_ROOT / "ssg"
BUILD_DIR = PROJECT_ROOT / "build"
HASH_CACHE_FILE = PROJECT_ROOT / ".cache/hashes.csv"
HASH_CACHE = dict()


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


def load_hash_cache():
    global HASH_CACHE

    if not HASH_CACHE_FILE.exists():
        return dict()

    with open(HASH_CACHE_FILE) as file:
        HASH_CACHE = {
            row[0]: {
                "last_mtime": row[1],
                "last_hash": row[2]
            } for row in csv.reader(file)
        }


def dump_hash_cache() -> None:
    if not HASH_CACHE_FILE.parent.exists():
        HASH_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(HASH_CACHE_FILE, "w") as file:
        writer = csv.writer(file)
        writer.writerows([
            (path, data["last_mtime"], data["last_hash"])
            for path, data in HASH_CACHE.items()
        ])


def static_url(file_path: str, live=False) -> str:
    """
    Implements cache busting for static assets by appending the first 8 characters of the SHA1 hash of a file to its
    name. It also maintains a CSV file containing:
        name of the file, last modification time of that file, the last SHA1 hash calculated for that file
    which serves as a cache, as recalculating the hash each build is wasteful.

    This is intended to be used both inside Jinja templates and inside `build_static()`.

    :param file_path: Path of the file relative to `/src/static`. File MUST reside inside the static directory.
    :param live: When live is True, files are being served live from the server script.
    :return: Path of the generated static asset relative to the build directory with the first 8 characters of the
    SHA1 hash of that file appended to the file name. Example: "/static/foo-SHA1HASH.bar"bar.
    """

    static_path = SRC_DIR / "static"
    file_path = (static_path / file_path).resolve()

    if not file_path.is_relative_to(static_path):
        raise Exception("static_url must be called only for files inside the static directory.")

    if live:
        return f"/{file_path.relative_to(SRC_DIR).parent}/{file_path.name}"

    file_path_str = str(file_path)
    cache_hit = (file_path_str in HASH_CACHE and
                 str(file_path.stat().st_mtime) == HASH_CACHE[file_path_str]["last_mtime"])
    if not cache_hit:
        with open(file_path, "rb") as file:
            sha1hash = hashlib.sha1(file.read(), usedforsecurity=False).hexdigest()[:8]

        HASH_CACHE[file_path_str] = {"last_mtime": str(file_path.stat().st_mtime), "last_hash": sha1hash}

    sha1hash = HASH_CACHE[str(file_path)]["last_hash"]

    return f"/{file_path.relative_to(SRC_DIR).parent}/{file_path.stem}-{sha1hash}{file_path.suffix}"


def load_config():
    with open(CONTENT_DIR / "config.toml", "rb") as file:
        cfg = tomllib.load(file)

    if cfg["license"]["start"] != str(current_year := date.today().year):
        cfg["license"]["start"] += f"-{current_year}"

    return cfg


def make_jinja_env(live=False) -> Environment:
    env = Environment(
        loader=FileSystemLoader(SRC_DIR / "templates"),
        autoescape=select_autoescape(["jinja"]),
        trim_blocks=True,
    )

    env.globals.update(load_config())
    env.globals["include_raw"] = include_raw

    if not live:
        load_hash_cache()
        env.globals["HASH_CACHE"] = HASH_CACHE
    env.globals["static_url"] = lambda file_path: static_url(file_path, live=live)

    return env


def render_markdown(file_path: str | Path) -> str:
    with open(file_path) as file:
        return mistletoe.markdown(file)


def build_static(minified=True):
    static_dir = SRC_DIR / "static"
    build_dir = BUILD_DIR / "static"

    for file in static_dir.rglob("*"):
        if file.is_dir():
            continue

        dst_path = build_dir / static_url(str(file.relative_to(static_dir))).removeprefix("/static/")

        if not dst_path.parent.exists():
            dst_path.parent.mkdir(parents=True, exist_ok=True)

        filetype = file.suffix.lstrip(".")
        if minified and filetype in ("html", "css", "js", "svg"):
            with open(file) as src_file:
                code = src_file.read()

            with open(dst_path, "w") as dst_file:
                dst_file.write(minify.string(mimetype_map[file.suffix], code))
        else:
            shutil.copyfile(file, dst_path)


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


def build_blog(jinja_env: Environment, minified=True, live=False):
    html = jinja_env.get_template("blog.jinja").render()

    if minified:
        html = minify.string(mimetype_map[".html"], html)

    if live:
        return html

    filepath = BUILD_DIR / "blog/index.html"
    filepath.parent.mkdir(parents=True)

    with open(filepath, "w") as file:
        file.write(html)


def build(minified=True):
    env = make_jinja_env()
    if BUILD_DIR.exists():
        # This is necessary as deleted files will be preserved from previous builds otherwise.
        shutil.rmtree(BUILD_DIR)

    kwargs = {
        "jinja_env": env,
        "minified": minified,
    }

    build_static(minified)
    dump_hash_cache()

    build_blog(**kwargs)

    build_home(**kwargs)


if __name__ == "__main__":
    build()
