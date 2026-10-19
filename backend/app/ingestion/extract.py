"""Step 1 of ingestion: get clean text out of a corpus PDF, page by page.

Paragraphs are kept apart by a blank line so the chunker (step 2) can split on them.
"""

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

# "habit-\nual" -> "habitual". Only when the next line starts in lower case, so
# "Self-\nControl" keeps its hyphen. Limitation: "self-\ncontrol" also loses it.
_HYPHENATED_LINE_BREAK = re.compile(r"(\w)-\n(?=[a-z])")
_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")
_WHITESPACE = re.compile(r"\s+")


class ExtractionError(Exception):
    """The file could not be read as a PDF."""


@dataclass(frozen=True)
class PageText:
    source: str  # file name, e.g. "habits.pdf"
    page: int  # page number, starting at 1
    text: str  # cleaned text; paragraphs separated by a blank line, "" if the page has none


def clean_text(raw: str) -> str:
    """Tidy text taken from a PDF.

    - turns ligatures and other look-alike characters into plain ones ("ﬁ" -> "fi")
    - joins words broken across lines with a hyphen
    - joins the lines inside a paragraph and collapses extra spaces
    - keeps paragraphs apart with one blank line
    """
    text = unicodedata.normalize("NFKC", raw).replace("\r\n", "\n").replace("\r", "\n")
    text = _HYPHENATED_LINE_BREAK.sub(r"\1", text)
    paragraphs = (_WHITESPACE.sub(" ", part).strip() for part in _PARAGRAPH_BREAK.split(text))
    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)


def extract_pages(path: Path) -> list[PageText]:
    """Return the cleaned text of every page, numbered from 1.

    Pages without text (for example scanned images) are kept with ``text=""`` so page
    numbers stay correct.
    """
    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            raise ExtractionError(f"{path.name} is password-protected")
        return [
            PageText(source=path.name, page=number, text=clean_text(page.extract_text() or ""))
            for number, page in enumerate(reader.pages, start=1)
        ]
    except (OSError, PdfReadError) as error:
        raise ExtractionError(f"cannot read {path.name}: {error}") from error


def file_sha256(path: Path) -> str:
    """Fingerprint of the file, used to skip files that were already ingested."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()
