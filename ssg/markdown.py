import ast
import re

from mistletoe import block_token
from mistletoe.html_renderer import HtmlRenderer
from mistletoe.block_token import BlockToken, Document, Paragraph, tokenize
from pygments.formatters.html import HtmlFormatter
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.styles import get_style_by_name
from pygments.util import ClassNotFound


class CustomBlock(BlockToken):
    """
    This allows for custom blocks with the following syntax:

    ::: block_type
    content here rendered as normal markdown.
    :::
    """

    pattern = re.compile(r"::: *((\S*)[^\n]*)")
    _open_info = None

    def __init__(self, match):
        lines, (self.block_type, self.info_string) = match
        super().__init__(lines, tokenize)

    @classmethod
    def start(cls, line):
        match_obj = cls.pattern.match(line)
        if not match_obj:
            return False

        info_string, block_type = match_obj.groups()
        if not block_type:
            return False

        cls._open_info = block_type, info_string
        return True

    @classmethod
    def read(cls, lines):
        next(lines)
        line_buffer = []
        for line in lines:
            if line.lstrip().startswith(":::"):
                break
            line_buffer.append(line)
        return line_buffer, cls._open_info


class BaseRenderer(HtmlRenderer):
    def __init__(self, *extras, **kwargs):
        # noinspection PyTypeChecker
        super().__init__(CustomBlock, *extras, **kwargs)

        # This allows the parsing process to request additional css as it sees fit per document.
        self.additional_stylesheets = []
        self.preview = ""


class PygmentsRenderer(BaseRenderer):
    def __init__(self, frontmatter_linenos_offset=0, code_style="sas", *extras, **kwargs):
        super().__init__(*extras, **kwargs)

        # Frontmatter is stripped from the markdown before being parsed, this number stores how many lines were used up
        # by the frontmatter. Add this as `Token.line_number + self.line_number_offset` to get absolute line number
        # in the file.
        self.frontmatter_linenos_offset = frontmatter_linenos_offset

        self.formatter = HtmlFormatter()
        self.formatter.style = get_style_by_name(code_style)

        self.is_first_paragraph = True
        self.preview = ""

    def parse_code_block_arguments(self, token: block_token.CodeFence):
        """
        This implements the following additional syntax:

        ```language | linenos | highlight=[1,(2, 3)] | relative_numbering
        import foo
        bar = "example"
        print(bar)
        ```

        Where everything after the starting triple backticks is optional. Parameters are case-insensitive.
        The `highlight` argument must be of type `List[int | Tuple[int, int]]`, where the Tuple serves as a range.
        The line numbers use relative numbering by default (relative to the line where your code fence starts). This can
        be disabled by passing the `absolute_numbering` argument.
        """
        args = {
            "linenos": False,
            "highlight": [],
            "absolute_numbering": False,
        }

        if not hasattr(token, "info_string"):
            return args

        for arg in token.info_string.split("|"):
            arg: str = arg.strip()

            if arg == "linenos":
                args["linenos"] = True

            elif arg == "absolute_numbering":
                args["absolute_numbering"] = True

            elif arg.startswith("highlight"):
                lines = ast.literal_eval(arg.split("=")[1].strip())
                if isinstance(lines, list):
                    args["highlight"] = lines

        # noinspection PyUnresolvedReferences
        offset = token.line_number + self.frontmatter_linenos_offset if args["absolute_numbering"] else 0

        hl_lines = []
        for line in args["highlight"]:
            if isinstance(line, tuple) or isinstance(line, list):
                hl_lines.extend(list(range(
                    line[0] - offset,
                    line[1] - offset + 1
                )))
            elif isinstance(line, int):
                hl_lines.append(line - offset)

        args["highlight"] = hl_lines

        return args

    def render_block_code(self, token: block_token.BlockCode | block_token.CodeFence) -> str:
        code = token.content
        lexer = None
        args = self.parse_code_block_arguments(token)

        if token.language:
            try:
                lexer = get_lexer_by_name(token.language)
            except ClassNotFound:
                pass

        if lexer is None:
            lexer = guess_lexer(code)

        self.additional_stylesheets.append("pygments.css.jinja")

        self.formatter.linenos = args["linenos"]
        self.formatter.hl_lines.update(set(args["highlight"]))
        return highlight(code, lexer, self.formatter)


class SummaryRenderer(BaseRenderer):
    def __init__(self, *extras, **kwargs):
        super().__init__(*extras, **kwargs)
        self.is_first_paragraph = True

    def render_paragraph(self, token: Paragraph) -> str:
        ret = super().render_paragraph(token)
        if self.is_first_paragraph and isinstance(token.parent, Document):
            self.is_first_paragraph = False
            self.preview = ret
        return ret


class CustomBlocksRenderer(BaseRenderer):
    def render_custom_block(self, token: CustomBlock):
        if token.block_type == "aside":
            return '<aside>{}</aside>'.format(self.render_inner(token))


class TOCRenderer(BaseRenderer):
    MAX_DEPTH = 4

    def __init__(self, section_numbering=False, *extras, **kwargs):
        super().__init__(*extras, **kwargs)
        self.section_numbering = section_numbering
        self.counter_stack = []
        self.last_level = None
        self.toc = []

    def update_counters(self, curr_level):
        if self.last_level is None:
            # The top-level heading isn't necessarily h1 (blog posts use h2 as the top-most heading).
            self.last_level = curr_level - 1

        if self.last_level < curr_level:
            self.counter_stack.extend([1] * (curr_level - self.last_level))
        elif self.last_level == curr_level:
            self.counter_stack[-1] += 1
        else:
            self.counter_stack = self.counter_stack[:-(self.last_level - curr_level)]
            self.counter_stack[-1] += 1

        self.last_level = curr_level

    def render_heading(self, token: block_token.Heading) -> str:
        ret = super().render_heading(token)
        if token.level > self.MAX_DEPTH:
            return ret

        match = re.match(r"(^<.*>)(.*)(</.*>$)", ret)
        open_tag, content, close_tag = match.group(1), match.group(2), match.group(3)

        if self.section_numbering:
            self.update_counters(token.level)
            section_number = ".".join([str(c) for c in self.counter_stack])
            if section_number.isdigit():
                # Adds a trailing dot for top-level headings.
                # Example: "1 Heading" becomes "1. Heading", but "1.1 Sub Heading" remains as is.
                section_number += "."

            content = f"<span class=section-numbers>{section_number}</span>" + content

        self.toc.append({
            "level": token.level,
            "content": content
        })

        return open_tag + content + close_tag


class ExtendedRenderer(PygmentsRenderer, SummaryRenderer, CustomBlocksRenderer, TOCRenderer):
    def render_markdown(self, markdown: str) -> str:
        return self.render(Document(markdown))
