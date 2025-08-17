import ast

from mistletoe import block_token
from mistletoe.html_renderer import HtmlRenderer
from mistletoe.block_token import Document, Paragraph
from pygments.formatters.html import HtmlFormatter
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.styles import get_style_by_name
from pygments.util import ClassNotFound


class BaseRender(HtmlRenderer):
    def __init__(self, *extras, **kwargs):
        super().__init__(*extras, **kwargs)

        # This allows the parsing process to request additional css as it sees fit per document.
        self.additional_stylesheets = []
        self.preview = ""


class PygmentsRenderer(BaseRender):
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
        The line numbers use absolute numbering from the original markdown file. This can be disabled by passing the
        `relative_numbering` argument.
        """
        args = {
            "linenos": False,
            "highlight": [],
            "relative_numbering": False,
        }

        if not hasattr(token, "info_string"):
            return args

        for arg in token.info_string.split("|"):
            arg: str = arg.strip()

            if arg == "linenos":
                args["linenos"] = True

            elif arg == "relative_numbering":
                args["relative_numbering"] = True

            elif arg.startswith("highlight"):
                lines = ast.literal_eval(arg.split("=")[1].strip())
                if isinstance(lines, list):
                    args["highlight"] = lines

        # Parse highlighted line numbers
        if not args["relative_numbering"]:
            # noinspection PyUnresolvedReferences
            offset = token.line_number + self.frontmatter_linenos_offset
            args["highlight"] = [
                line - offset if isinstance(line, int) else (line[0] - offset, line[1] - offset)
                for line in args["highlight"]
            ]

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

        return highlight(code, lexer, self.formatter)


class SummaryRenderer(BaseRender):
    def __init__(self, *extras, **kwargs):
        super().__init__(*extras, **kwargs)
        self.is_first_paragraph = True

    def render_paragraph(self, token: Paragraph) -> str:
        ret = super().render_paragraph(token)
        if self.is_first_paragraph:
            self.is_first_paragraph = False
            self.preview = ret
        return ret


class ExtendedRenderer(PygmentsRenderer, SummaryRenderer):
    def render_markdown(self, markdown: str) -> str:
        return self.render(Document(markdown))
