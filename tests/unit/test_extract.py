"""Text extraction from PDFs (CPE-FR-02, step 1).

The sample PDFs are built inside the tests, so no real corpus file is needed.
"""

import hashlib
from pathlib import Path

import pytest

from app.ingestion.extract import ExtractionError, clean_text, extract_pages, file_sha256


def make_pdf(pages: list[list[str]]) -> bytes:
    """Build a small PDF: one list of text lines per page, in the built-in Helvetica font."""
    page_ids = [4 + 2 * index for index in range(len(pages))]
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for page_id, lines in zip(page_ids, pages, strict=True):
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {page_id + 1} 0 R >>".encode()
        )
        text = " ".join(f"({line}) Tj T*" for line in lines)
        stream = f"BT /F1 12 Tf 14 TL 72 720 Td {text} ET".encode()
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_start = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n".encode()
    pdf += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_start}\n%%EOF\n".encode()
    )
    return bytes(pdf)


# --- clean_text -----------------------------------------------------------------------


def test_joins_words_broken_across_lines() -> None:
    assert clean_text("Repeated actions become habit-\nual over time.") == (
        "Repeated actions become habitual over time."
    )


def test_keeps_hyphens_inside_a_line() -> None:
    assert clean_text("A well-known habit loop.") == "A well-known habit loop."


def test_joins_lines_and_collapses_spaces_inside_a_paragraph() -> None:
    assert clean_text("Habits   form\nthrough\t repetition.") == "Habits form through repetition."


def test_keeps_paragraphs_apart_with_one_blank_line() -> None:
    raw = "First paragraph.\n\n\n  \nSecond paragraph\ncontinues here."

    assert clean_text(raw) == "First paragraph.\n\nSecond paragraph continues here."


def test_replaces_ligatures_with_plain_letters() -> None:
    assert clean_text("ﬁrst ﬂow") == "first flow"


def test_whitespace_only_text_becomes_empty() -> None:
    assert clean_text(" \n\n \t ") == ""


# --- extract_pages --------------------------------------------------------------------


def test_extracts_each_page_with_file_name_and_page_number(tmp_path: Path) -> None:
    pdf = tmp_path / "habits.pdf"
    pdf.write_bytes(make_pdf([["Habits form through repetition."], ["Rewards make them stick."]]))

    pages = extract_pages(pdf)

    assert [(page.source, page.page) for page in pages] == [("habits.pdf", 1), ("habits.pdf", 2)]
    assert pages[0].text == "Habits form through repetition."
    assert pages[1].text == "Rewards make them stick."


def test_cleans_the_text_it_extracts(tmp_path: Path) -> None:
    pdf = tmp_path / "habits.pdf"
    pdf.write_bytes(make_pdf([["Repeated actions become habit-", "ual over time."]]))

    assert extract_pages(pdf)[0].text == "Repeated actions become habitual over time."


def test_keeps_a_page_without_text_so_numbering_stays_correct(tmp_path: Path) -> None:
    pdf = tmp_path / "habits.pdf"
    pdf.write_bytes(make_pdf([["Page one."], [], ["Page three."]]))

    pages = extract_pages(pdf)

    assert [(page.page, page.text) for page in pages] == [
        (1, "Page one."),
        (2, ""),
        (3, "Page three."),
    ]


def test_missing_file_raises_extraction_error(tmp_path: Path) -> None:
    with pytest.raises(ExtractionError, match=r"missing\.pdf"):
        extract_pages(tmp_path / "missing.pdf")


def test_file_that_is_not_a_pdf_raises_extraction_error(tmp_path: Path) -> None:
    fake = tmp_path / "notes.pdf"
    fake.write_text("just some text, not a PDF")

    with pytest.raises(ExtractionError, match=r"notes\.pdf"):
        extract_pages(fake)


# --- file_sha256 ----------------------------------------------------------------------


def test_sha256_matches_the_file_contents(tmp_path: Path) -> None:
    pdf = tmp_path / "habits.pdf"
    content = make_pdf([["Habits."]])
    pdf.write_bytes(content)

    assert file_sha256(pdf) == hashlib.sha256(content).hexdigest()
