from typing import Tuple

import mistletoe
from mistletoe.html_renderer import HtmlRenderer
from mistletoe.block_token import Document, Paragraph


class SummaryExtractor(HtmlRenderer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_first_paragraph = True
        self.preview = ""

    def render_paragraph(self, token: Paragraph) -> str:
        ret = super().render_paragraph(token)
        if self.is_first_paragraph:
            self.is_first_paragraph = False
            self.preview = ret
        return ret

    def render_with_preview(self, token):
        html = super().render(token)
        return html, self.preview


def render_markdown(markdown: str, preview=False) -> str | Tuple[str, str]:
    if preview:
        with SummaryExtractor() as renderer:
            return renderer.render_with_preview(Document(markdown))
    else:
        return mistletoe.markdown(markdown)
