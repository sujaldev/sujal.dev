import csv
import functools
import hashlib
import shutil
import tomllib
from datetime import date
from mimetypes import types_map as mimetype_map
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from ssg.constants import *
from ssg.markdown import render_markdown

import frontmatter
import minify
from jinja2 import ChoiceLoader
from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import PrefixLoader
from jinja2 import select_autoescape
from markupsafe import Markup

type PostList = Iterable[Dict]


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


class Builder:
    def __init__(self, minified=True, live=False, include_drafts=False):
        self.minified = minified
        self.live = live
        self.include_drafts = include_drafts

        self.env = self.make_jinja_env()

        self.hash_cache: dict = {}
        self.load_hash_cache()

    def load_hash_cache(self):
        if not HASH_CACHE_FILE.exists():
            self.hash_cache = {}
            return

        with open(HASH_CACHE_FILE) as file:
            self.hash_cache = {
                row[0]: {
                    "last_mtime": row[1],
                    "last_hash": row[2]
                } for row in csv.reader(file)
            }

    def dump_hash_cache(self) -> None:
        if not HASH_CACHE_FILE.parent.exists():
            HASH_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

        with open(HASH_CACHE_FILE, "w") as file:
            writer = csv.writer(file)
            writer.writerows([
                (path, data["last_mtime"], data["last_hash"])
                for path, data in self.hash_cache.items()
            ])

    def static_url(self, file_path: str) -> str:
        """
        Implements cache busting for static assets by appending the first 8 characters of the SHA1 hash of a file to its
        name. It also maintains a CSV file containing:
            name of the file, last modification time of that file, the last SHA1 hash calculated for that file
        which serves as a cache, as recalculating the hash each build is wasteful.

        This is intended to be used both inside Jinja templates and inside `build_static()`.

        :param file_path: Path of the file relative to `/src/static`. File MUST reside inside the static directory.
        :return: Path of the generated static asset relative to the build directory with the first 8 characters of the
        SHA1 hash of that file appended to the file name. Example: "/static/foo-SHA1HASH.bar".
        """

        static_path = SRC_DIR / "static"
        file_path = (static_path / file_path).resolve()

        if not file_path.is_relative_to(static_path):
            raise Exception(f"static_url called for file '{file_path}' not inside the static directory.")

        if self.live:
            url_without_hash = "/static/" + str(file_path.relative_to(static_path)).removesuffix(".jinja")
            return url_without_hash

        file_path_str = str(file_path)
        cache_hit = (file_path_str in self.hash_cache and
                     str(file_path.stat().st_mtime) == self.hash_cache[file_path_str]["last_mtime"])
        if not cache_hit:
            with open(file_path, "rb") as file:
                sha1hash = hashlib.sha1(file.read(), usedforsecurity=False).hexdigest()[:8]

            self.hash_cache[file_path_str] = {"last_mtime": str(file_path.stat().st_mtime), "last_hash": sha1hash}

        sha1hash = self.hash_cache[str(file_path)]["last_hash"]

        suffixes = "".join(file_path.suffixes)
        file_name_with_hash = str(file_path.name).removesuffix(suffixes) + "-" + sha1hash + suffixes
        url_with_hash = str(file_path.with_name(file_name_with_hash).relative_to(static_path))
        url_with_hash = "/static/" + url_with_hash.removesuffix(".jinja")

        return url_with_hash

    @staticmethod
    def read_config() -> dict:
        with open(CONTENT_DIR / "config.toml", "rb") as file:
            cfg = tomllib.load(file)

        if cfg["license"]["start"] != str(current_year := date.today().year):
            cfg["license"]["start"] += f"-{current_year}"

        return cfg

    def load_config(self):
        # This is meant to be called by the live server on changes to config.toml
        self.env.globals.update(self.read_config())

    def make_jinja_env(self) -> Environment:
        env = Environment(
            loader=ChoiceLoader([
                FileSystemLoader(SRC_DIR / "templates"),
                PrefixLoader({
                    "static": FileSystemLoader(SRC_DIR / "static")
                })
            ]),
            autoescape=select_autoescape(["jinja"]),
            trim_blocks=True,
        )

        env.globals.update(self.read_config())

        env.globals["include_raw"] = include_raw
        env.globals["static_url"] = self.static_url

        return env

    @staticmethod
    def handle_output(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            file_path, code = func(self, *args, **kwargs)
            file_path = Path(file_path)

            if self.minified:
                code = minify.string(mimetype_map[file_path.suffix], code)

            if not self.live:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, "w") as file:
                    file.write(code)

            return code

        return wrapper

    def load_posts(self, stop: int = None) -> PostList:
        files = sorted((CONTENT_DIR / "posts").rglob("*.md"), reverse=True)[:stop]
        posts = []

        for file_path in files:
            with open(file_path) as file:
                post = frontmatter.load(file)

            if post.get("draft", False) and not self.include_drafts:
                continue

            if "slug" not in post:
                post["slug"] = "-".join(file_path.stem.split("-")[1:])

            post["url"] = f"/post/{post['slug']}"
            post["html"], post["preview"] = render_markdown(post.content, preview=True)
            posts.append(post.to_dict())

        return posts

    # **************************************************************************************************************** #
    #                                                   Build Steps                                                    #
    # **************************************************************************************************************** #

    @handle_output
    def build_static_template(self, file_path: str | Path):
        static_dir = SRC_DIR / "static"
        file_path = (SRC_DIR / "static") / Path(file_path)
        file_path.resolve()
        if not file_path.is_relative_to(static_dir):
            raise Exception(f"File '{file_path}' does not reside inside the static directory.")

        file_path = file_path.relative_to(static_dir)
        return (
            (BUILD_DIR / "static") / file_path,
            self.env.get_template(f"static/{str(file_path).removesuffix('.jinja')}.jinja").render()
        )

    def build_static(self):
        static_dir = SRC_DIR / "static"
        build_dir = BUILD_DIR / "static"

        for file in static_dir.rglob("*"):
            if file.is_dir():
                continue

            dst_path = build_dir / self.static_url(str(file.relative_to(static_dir))).removeprefix("/static/")

            dst_path.parent.mkdir(parents=True, exist_ok=True)

            filetype = file.suffix.lstrip(".")
            if self.minified and filetype in ("html", "css", "js", "svg", "jinja"):
                if filetype == "jinja":
                    mimetype = mimetype_map[file.suffixes[-2]]
                    code = self.env.get_template("static/" + str(file.relative_to(static_dir))).render()
                else:
                    mimetype = mimetype_map[file.suffix]
                    with open(file) as src_file:
                        code = src_file.read()

                with open(dst_path, "w") as dst_file:
                    dst_file.write(minify.string(mimetype, code))
            else:
                shutil.copyfile(file, dst_path)

    @handle_output
    def build_home(self, recent_posts: PostList) -> Tuple[str | Path, str]:
        content = None
        content_filepath = CONTENT_DIR / "home.md"
        if content_filepath.exists():
            with open(content_filepath) as file:
                content = render_markdown(file.read())

        return (
            BUILD_DIR / "index.html",
            self.env.get_template("index.jinja").render(content=content, recent_posts=recent_posts)
        )

    @handle_output
    def build_blog_index(self, posts: PostList) -> Tuple[str | Path, str]:
        return (
            BUILD_DIR / "blog/index.html",
            self.env.get_template("blog.jinja").render(posts=posts)
        )

    @handle_output
    def build_blog_post(self, post: Dict) -> Tuple[str | Path, str]:
        required_keys = ("title", "date")
        for key in required_keys:
            if key == "date" and post.get("draft", False):
                continue

            if key not in post:
                raise Exception(f"Missing '{key}' key: {post['slug']}")

        post["author"] = post.get("author", self.env.globals["author"]["name"])

        html = self.env.get_template("post.jinja").render(
            post=post,
            content=post.get("html", render_markdown(post["content"]))
        )

        return (
            BUILD_DIR / f"post/{post['slug']}/index.html",
            html
        )

    def build(self):
        if BUILD_DIR.exists():
            # This is necessary as deleted files will be preserved from previous builds otherwise.
            shutil.rmtree(BUILD_DIR)

        self.build_static()
        self.dump_hash_cache()

        posts = self.load_posts()
        self.build_home(posts[:5])
        self.build_blog_index(posts)

        for post in posts:
            self.build_blog_post(post)


if __name__ == "__main__":
    Builder().build()
