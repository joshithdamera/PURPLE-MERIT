from __future__ import annotations

import re
from collections.abc import Iterable

import requests
from bs4 import BeautifulSoup

from catalog_assistant.models import RawDocument, SourceEntry


def fetch_html(url: str) -> str:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def clean_text(html: str) -> tuple[str, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    headings: list[str] = []
    for heading in soup.find_all(re.compile("^h[1-4]$")):
        text = heading.get_text(" ", strip=True)
        if text:
            headings.append(text)

    blocks: list[str] = []
    for node in soup.find_all(["h1", "h2", "h3", "h4", "p", "li", "td"]):
        text = node.get_text(" ", strip=True)
        if text:
            blocks.append(text)

    merged = "\n".join(blocks)
    merged = re.sub(r"[ \t]+", " ", merged)
    merged = re.sub(r"\n{2,}", "\n", merged)
    return merged.strip(), headings


def ingest_source(entry: SourceEntry) -> RawDocument:
    html = fetch_html(entry.url)
    text, headings = clean_text(html)
    title = headings[0] if headings else entry.note
    return RawDocument(
        source_id=entry.id,
        category=entry.category,
        url=entry.url,
        title=title,
        headings=headings,
        text=text,
    )


def ingest_all(entries: Iterable[SourceEntry]) -> list[RawDocument]:
    return [ingest_source(entry) for entry in entries]

