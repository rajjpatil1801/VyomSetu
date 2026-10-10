def compact(html: str) -> str:
    """Remove indentation and line breaks so Markdown cannot treat the HTML as a code block."""
    if html is None:
        return ""
    return "".join(line.strip() for line in html.splitlines())
