from __future__ import annotations

import ipaddress
import json
import os
import socket
from html.parser import HTMLParser
from typing import Literal, Type
from urllib.parse import urlparse

import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class SearchInput(BaseModel):
    query: str = Field(description="A focused search query for products, competitors, business models, pricing, or public market signals")
    search_type: Literal["web", "news"] = Field(default="web", description="Use web for product/company sources and news for recent coverage")
    country_code: str = Field(default="", description="Two-letter country code for local results, such as mx")
    language: str = Field(default="", description="Two-letter result language code, such as es")


class MarketWebSearchTool(BaseTool):
    name: str = "search_market_sources"
    description: str = (
        "Searches current public web or news results in a target country/language. Use specific queries and search both "
        "local-language and English terms when useful. Results are leads, not proof: verify important claims by reading "
        "the linked page, prefer primary sources, and cite URLs. Requires SERPER_API_KEY."
    )
    args_schema: Type[BaseModel] = SearchInput

    def _run(self, query: str, search_type: str = "web", country_code: str = "", language: str = "") -> str:
        api_key = os.getenv("SERPER_API_KEY")
        if not api_key:
            return "Search unavailable: SERPER_API_KEY is not set. Do not invent current market information."
        endpoint = "https://google.serper.dev/news" if search_type == "news" else "https://google.serper.dev/search"
        payload: dict[str, object] = {"q": query.strip(), "num": 10}
        country_code = country_code or os.getenv("MARKET_SEARCH_COUNTRY", "")
        language = language or os.getenv("MARKET_SEARCH_LANGUAGE", "")
        if country_code.strip():
            payload["gl"] = country_code.strip().lower()
        if language.strip():
            payload["hl"] = language.strip().lower()
        try:
            response = httpx.post(
                endpoint,
                headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                json=payload,
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            return f"Search failed: {type(exc).__name__}: {exc}"
        result_key = "news" if search_type == "news" else "organic"
        results = []
        for item in data.get(result_key, [])[:10]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "date": item.get("date", ""),
                "source": item.get("source", ""),
            })
        return json.dumps(results, ensure_ascii=False) if results else "No results found for this query."


class FetchPageInput(BaseModel):
    url: str = Field(description="HTTPS public webpage URL returned by search_market_sources")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.skip_depth += 1
        elif tag.lower() in {"p", "div", "li", "h1", "h2", "h3", "h4", "tr", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self.skip_depth:
            self.skip_depth -= 1
        elif tag.lower() in {"p", "div", "li", "h1", "h2", "h3", "h4", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth and data.strip():
            self.parts.append(data.strip())


def _resolves_publicly(host: str) -> bool:
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)}
        return bool(addresses) and all(ipaddress.ip_address(address).is_global for address in addresses)
    except (OSError, ValueError):
        return False


class MarketPageFetchTool(BaseTool):
    name: str = "read_public_market_source"
    description: str = (
        "Reads text from one public HTTPS page found by search_market_sources. Do not fetch private/local addresses. "
        "Use the page to verify claims and cite the exact URL. Some app stores or sites may block automated reading; "
        "in that case report the access limitation and use other public evidence."
    )
    args_schema: Type[BaseModel] = FetchPageInput

    def _run(self, url: str) -> str:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        if parsed.scheme != "https" or not host or not _resolves_publicly(host):
            return "Rejected URL: only public HTTPS pages can be read."
        try:
            with httpx.Client(follow_redirects=True, timeout=15, headers={"User-Agent": "MarketOpportunityAnalyst/0.1"}) as client:
                response = client.get(url)
                response.raise_for_status()
                final = urlparse(str(response.url))
                if final.scheme != "https" or not final.hostname or not _resolves_publicly(final.hostname):
                    return "Rejected redirect: the final host is not a public HTTPS address."
                parser = _TextExtractor()
                parser.feed(response.text)
                text = " ".join(" ".join(parser.parts).split())
                return f"Page URL: {response.url}\n\n{text[:14000]}"
        except (httpx.HTTPError, ValueError) as exc:
            return f"Page fetch failed: {type(exc).__name__}: {exc}"
