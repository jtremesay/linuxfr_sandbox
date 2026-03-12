from pathlib import Path

from lfr.settings import HTML_DIR


def path_to_url(path: Path) -> str:
    """Convert a file path to a URL relative to the HTML directory."""
    return "/" + str(path.relative_to(HTML_DIR).parent / path.stem)


def url_to_path(url: str) -> Path:
    """Convert a URL to a file path relative to the HTML directory."""
    return HTML_DIR / (url[1:] + ".html")
