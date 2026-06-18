from __future__ import annotations

from crypto_radar.utils.urls import normalize_url


def test_normalize_url_removes_fragment() -> None:
    assert normalize_url("https://Example.com/path#section") == "https://example.com/path"


def test_normalize_url_removes_utm_parameters() -> None:
    assert (
        normalize_url("https://example.com/post?utm_source=x&a=1&utm_campaign=y")
        == "https://example.com/post?a=1"
    )


def test_normalize_url_sorts_parameters() -> None:
    assert normalize_url("https://example.com/post?b=2&a=1") == "https://example.com/post?a=1&b=2"


def test_normalize_url_unifies_trailing_slash() -> None:
    assert normalize_url("https://example.com/post/") == "https://example.com/post"
    assert normalize_url("https://example.com/") == "https://example.com"
