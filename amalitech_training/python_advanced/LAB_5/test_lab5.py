from __future__ import annotations
import pytest
import time
from .extractor import (
    extract_all,
    extract_headings,
    extract_links,
    extract_title,
    filter_successful,
    map_to_summary,
    process_results,
    word_count,
)
from .async_decorators import rate_limit, retry

SAMPLE_HTML = """
<html>
<head><title>  Test Page  </title></head>
<body>
  <h1>Main Heading</h1>
  <h2>Sub Heading</h2>
  <h3>Minor Heading</h3>
  <p>Visit <a href="https://example.com">Example</a> and
     <a href="/about">About</a>.</p>
  <p>Some visible text content for word counting purposes.</p>
</body>
</html>
"""

SAMPLE_RESULT = {
    "url": "https://example.com",
    "status": 200,
    "html": SAMPLE_HTML,
    "error": None,
}

FAILED_RESULT = {
    "url": "https://bad.example.com",
    "status": 404,
    "html": None,
    "error": None,
}


class TestExtractTitle:
    def test_extracts_title(self):
        assert extract_title(SAMPLE_HTML) == "Test Page"

    def test_returns_none_for_missing_title(self):
        assert extract_title("<html><body>no title</body></html>") is None

    def test_strips_whitespace(self):
        html = "<title>  Padded  </title>"
        assert extract_title(html) == "Padded"

    def test_case_insensitive(self):
        html = "<TITLE>Upper</TITLE>"
        assert extract_title(html) == "Upper"

    def test_empty_string(self):
        assert extract_title("") is None


class TestExtractLinks:
    def test_finds_absolute_links(self):
        links = extract_links(SAMPLE_HTML)
        assert "https://example.com" in links

    def test_finds_relative_links(self):
        links = extract_links(SAMPLE_HTML)
        assert "/about" in links

    def test_returns_empty_list_when_no_links(self):
        assert extract_links("<p>no links here</p>") == []

    def test_handles_single_quoted_hrefs(self):
        html = "<a href='/single'>text</a>"
        assert "/single" in extract_links(html)

    def test_skips_fragment_only_hrefs(self):
        links = extract_links("<a href='#section'>Jump</a>")
        assert "#section" not in links


class TestExtractHeadings:
    def test_finds_h1(self):
        assert "Main Heading" in extract_headings(SAMPLE_HTML)

    def test_finds_h2(self):
        assert "Sub Heading" in extract_headings(SAMPLE_HTML)

    def test_finds_h3(self):
        assert "Minor Heading" in extract_headings(SAMPLE_HTML)

    def test_returns_empty_for_no_headings(self):
        assert extract_headings("<p>no headings</p>") == []

    def test_strips_inner_whitespace(self):
        html = "<h1>  Spaced  </h1>"
        assert "Spaced" in extract_headings(html)


class TestWordCount:
    def test_counts_words(self):
        html = "<p>one two three</p>"
        assert word_count(html) == 3

    def test_strips_tags_before_counting(self):
        html = "<h1>Hello</h1><p>World</p>"
        assert word_count(html) == 2

    def test_zero_for_empty_html(self):
        assert word_count("") == 0

    def test_ignores_tag_attribute_text(self):
        # attribute values should not be counted as words
        html = '<a href="https://example.com">click</a>'
        assert word_count(html) == 1


class TestExtractAll:
    def test_returns_enriched_dict(self):
        result = extract_all(SAMPLE_RESULT)
        assert "title" in result
        assert "links" in result
        assert "headings" in result
        assert "words" in result

    def test_preserves_original_fields(self):
        result = extract_all(SAMPLE_RESULT)
        assert result["url"] == "https://example.com"
        assert result["status"] == 200

    def test_handles_none_html_gracefully(self):
        result = extract_all(FAILED_RESULT)
        assert result["title"] is None
        assert result["links"] == []
        assert result["headings"] == []
        assert result["words"] == 0

    def test_no_email_field_present(self):
        result = extract_all(SAMPLE_RESULT)
        assert "emails" not in result


class TestProcessResults:
    def test_is_async_generator(self):
        import inspect

        gen = process_results([SAMPLE_RESULT])
        assert inspect.isasyncgen(gen)

    @pytest.mark.asyncio
    async def test_yields_correct_count(self):
        results = []
        async for item in process_results([SAMPLE_RESULT, FAILED_RESULT]):
            results.append(item)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_each_item_has_title_key(self):
        results = []
        async for item in process_results([SAMPLE_RESULT]):
            results.append(item)
        assert "title" in results[0]

    @pytest.mark.asyncio
    async def test_yields_nothing_for_empty_input(self):
        results = []
        async for item in process_results([]):
            results.append(item)
        assert results == []


class TestFilterSuccessful:
    def test_keeps_200_results(self):
        enriched = [extract_all(SAMPLE_RESULT)]
        assert len(filter_successful(enriched)) == 1

    def test_drops_non_200(self):
        enriched = [extract_all(FAILED_RESULT)]
        assert filter_successful(enriched) == []

    def test_empty_input(self):
        assert filter_successful([]) == []


class TestMapToSummary:
    def test_returns_summary_keys(self):
        enriched = [extract_all(SAMPLE_RESULT)]
        summaries = map_to_summary(enriched)
        assert "url" in summaries[0]
        assert "title" in summaries[0]
        assert "headings" in summaries[0]
        assert "words" in summaries[0]
        assert "links" in summaries[0]

    def test_links_is_count_not_list(self):
        enriched = [extract_all(SAMPLE_RESULT)]
        summary = map_to_summary(enriched)[0]
        assert isinstance(summary["links"], int)

    def test_no_emails_key_in_summary(self):
        enriched = [extract_all(SAMPLE_RESULT)]
        summary = map_to_summary(enriched)[0]
        assert "emails" not in summary

    def test_headings_is_list(self):
        enriched = [extract_all(SAMPLE_RESULT)]
        summary = map_to_summary(enriched)[0]
        assert isinstance(summary["headings"], list)


class TestRetryDecorator:
    @pytest.mark.asyncio
    async def test_returns_value_on_success(self):
        @retry(max_attempts=3)
        async def ok():
            return "ok"

        assert await ok() == "ok"

    @pytest.mark.asyncio
    async def test_retries_then_succeeds(self):
        calls = {"n": 0}

        @retry(max_attempts=3, delay=0.01)
        async def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise ValueError("not yet")
            return "done"

        assert await flaky() == "done"
        assert calls["n"] == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_attempts(self):
        @retry(max_attempts=2, delay=0.01)
        async def always_fails():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            await always_fails()

    @pytest.mark.asyncio
    async def test_preserves_function_name(self):
        @retry()
        async def my_func():
            return 1

        assert my_func.__name__ == "my_func"

    @pytest.mark.asyncio
    async def test_only_catches_specified_exceptions(self):
        @retry(max_attempts=2, delay=0.01, exceptions=(ValueError,))
        async def wrong_exc():
            raise TypeError("not caught")

        with pytest.raises(TypeError):
            await wrong_exc()


class TestRateLimitDecorator:
    @pytest.mark.asyncio
    async def test_returns_correct_value(self):
        @rate_limit(calls_per_second=100.0)
        async def fast():
            return 42

        assert await fast() == 42

    @pytest.mark.asyncio
    async def test_preserves_function_name(self):
        @rate_limit(calls_per_second=10.0)
        async def named():
            return 1

        assert named.__name__ == "named"

    @pytest.mark.asyncio
    async def test_throttles_rapid_calls(self):
        @rate_limit(calls_per_second=1.0)
        async def timed():
            return time.monotonic()

        t1 = await timed()
        t2 = await timed()
        assert (t2 - t1) >= 0.9
