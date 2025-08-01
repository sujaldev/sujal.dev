import sys
import argparse


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="ssg",
        description="Static site generator for sujal.dev",
    )

    subparser = parser.add_subparsers(
        title="command",
        dest="command",
    )

    build_parser = subparser.add_parser(
        name="build",
        help="Build the site into build/ directory."
    )
    build_parser.add_argument(
        "-m", "--minify", action="store_true", help="Enable minification."
    )

    live_parser = subparser.add_parser("live", help="Start a live server, only build pages on request.")
    live_parser.add_argument(
        "-b", "--bind", help="Bind to this address. (Default: 0.0.0.0)", dest="address", default="0.0.0.0"
    )
    live_parser.add_argument(
        "-p", "--port", help="Bind to this port. (Default: 5000)", dest="port", default="5000"
    )
    live_parser.add_argument(
        "-m", "--minify", action="store_true", help="Enable minification."
    )

    subset_fonts_parser = subparser.add_parser(
        "subset-fonts", help="Generate font subsets and associated stylesheets."
    )
    subset_fonts_parser.add_argument(
        "-c", "--css-only", action="store_true",
        help="Do not regenerate font subsets, only font-face rules stylesheet template."
    )

    args = parser.parse_args(argv)

    match args.command:
        case "build":
            from ssg.build import Builder
            Builder(args.minify).build()
        case "live":
            from ssg.server import run as live
            live(args.address, args.port, args.minify)
        case "subset-fonts":
            from ssg.fonts.subset import build as subset_fonts
            subset_fonts(args.css_only)


if __name__ == "__main__":
    main()
