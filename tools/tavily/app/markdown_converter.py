import html2text


def convert_html_to_markdown(html_content: str) -> str:
    """
    Convert HTML content to markdown using html2text.
    """
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = False
    converter.body_width = 0
    return converter.handle(html_content)
