from __future__ import annotations
import pytest
import time
import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
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
from .fetcher import fetch_all, fetch_url, fetch_with_timeout
from .storage import build_filename, ensure_output_dir, load_results, save_results
from .performance import _blocking_fetch, benchmark, run_async, run_sequential, run_threaded

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

MOCK_FETCH = {
    "url": "https://example.com",
    "status": 200,
    "html": SAMPLE_HTML,
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


def _mock_response(status: int, text: str = SAMPLE_HTML):
    """Build a mock aiohttp response context manager."""
    resp = AsyncMock()
    resp.status = status
    resp.text = AsyncMock(return_value=text)
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


def _mock_session(status: int = 200, text: str = SAMPLE_HTML):
    session = MagicMock()
    session.get = MagicMock(return_value=_mock_response(status, text))
    return session


class TestFetchUrl:
    @pytest.mark.asyncio
    async def test_returns_required_keys(self):
        result = await fetch_url(_mock_session(200), "https://example.com")
        assert {"url", "status", "html", "error"} <= result.keys()

    @pytest.mark.asyncio
    async def test_200_status_returned(self):
        result = await fetch_url(_mock_session(200), "https://example.com")
        assert result["status"] == 200

    @pytest.mark.asyncio
    async def test_200_returns_html(self):
        result = await fetch_url(_mock_session(200, SAMPLE_HTML), "https://example.com")
        assert result["html"] == SAMPLE_HTML

    @pytest.mark.asyncio
    async def test_non_200_gives_none_html(self):
        result = await fetch_url(_mock_session(404), "https://example.com/x")
        assert result["html"] is None
        assert result["status"] == 404

    @pytest.mark.asyncio
    async def test_url_preserved_in_result(self):
        url = "https://example.com/page"
        result = await fetch_url(_mock_session(200), url)
        assert result["url"] == url

    @pytest.mark.asyncio
    async def test_exception_returns_error_dict(self):
        session = MagicMock()
        session.get = MagicMock(side_effect=Exception("connection refused"))
        result = await fetch_url(session, "https://unreachable.example.com")
        assert result["error"] is not None
        assert result["html"] is None
        assert result["status"] is None


class TestFetchAll:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        with patch(
            "amalitech_training.python_advanced.LAB_5.fetcher.fetch_url",
            new=AsyncMock(return_value=MOCK_FETCH),
        ):
            results = await fetch_all(["https://a.com", "https://b.com"])
        assert isinstance(results, list)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_empty_urls_returns_empty(self):
        results = await fetch_all([])
        assert results == []

    @pytest.mark.asyncio
    async def test_each_result_has_required_keys(self):
        with patch(
            "amalitech_training.python_advanced.LAB_5.fetcher.fetch_url",
            new=AsyncMock(return_value=MOCK_FETCH),
        ):
            results = await fetch_all(["https://example.com"])
        assert {"url", "status", "html", "error"} <= results[0].keys()


class TestFetchWithTimeout:
    @pytest.mark.asyncio
    async def test_returns_result_on_success(self):
        with patch(
            "amalitech_training.python_advanced.LAB_5.fetcher.fetch_url",
            new=AsyncMock(return_value=MOCK_FETCH),
        ):
            result = await fetch_with_timeout("https://example.com", timeout=5.0)
        assert result["url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_timeout_returns_error_dict(self):
        with patch(
            "amalitech_training.python_advanced.LAB_5.fetcher.asyncio.wait_for",
            side_effect=asyncio.TimeoutError,
        ):
            result = await fetch_with_timeout("https://slow.example.com", timeout=0.01)
        assert result["error"] == "timeout"
        assert result["html"] is None


class TestEnsureOutputDir:
    def test_creates_directory(self, tmp_path):
        target = tmp_path / "nested" / "output"
        result = ensure_output_dir(target)
        assert result.is_dir()

    def test_returns_path_object(self, tmp_path):
        result = ensure_output_dir(tmp_path / "out")
        assert isinstance(result, Path)

    def test_existing_dir_does_not_raise(self, tmp_path):
        ensure_output_dir(tmp_path)  # already exists
        ensure_output_dir(tmp_path)  # second call must not raise


class TestBuildFilename:
    def test_json_extension(self, tmp_path, monkeypatch):
        from amalitech_training.python_advanced.LAB_5 import storage

        monkeypatch.setattr(storage, "OUTPUT_DIR", tmp_path)
        assert build_filename("run").suffix == ".json"

    def test_prefix_in_name(self, tmp_path, monkeypatch):
        from amalitech_training.python_advanced.LAB_5 import storage

        monkeypatch.setattr(storage, "OUTPUT_DIR", tmp_path)
        assert "run_" in build_filename("run").name

    def test_file_inside_output_dir(self, tmp_path, monkeypatch):
        from amalitech_training.python_advanced.LAB_5 import storage

        monkeypatch.setattr(storage, "OUTPUT_DIR", tmp_path)
        assert build_filename("x").parent == tmp_path


class TestSaveAndLoad:
    @pytest.mark.asyncio
    async def test_save_creates_file(self, tmp_path):
        path = tmp_path / "out.json"
        returned = await save_results([MOCK_FETCH], path)
        assert returned == path
        assert path.exists()

    @pytest.mark.asyncio
    async def test_content_is_valid_json(self, tmp_path):
        path = tmp_path / "out.json"
        await save_results([{"url": "x", "words": 7}], path)
        loaded = json.loads(path.read_text())
        assert loaded[0]["words"] == 7

    @pytest.mark.asyncio
    async def test_roundtrip(self, tmp_path):
        data = [{"url": "a"}, {"url": "b"}]
        path = tmp_path / "rt.json"
        await save_results(data, path)
        loaded = await load_results(path)
        assert len(loaded) == 2
        assert loaded[0]["url"] == "a"

    @pytest.mark.asyncio
    async def test_empty_list(self, tmp_path):
        path = tmp_path / "empty.json"
        await save_results([], path)
        assert json.loads(path.read_text()) == []

    @pytest.mark.asyncio
    async def test_save_uses_default_path(self, tmp_path, monkeypatch):
        """Test save_results with default path uses build_filename."""
        from amalitech_training.python_advanced.LAB_5 import storage

        monkeypatch.setattr(storage, "OUTPUT_DIR", tmp_path)
        returned = await save_results([MOCK_FETCH])
        assert returned.parent == tmp_path
        assert returned.suffix == ".json"
        assert returned.exists()

    @pytest.mark.asyncio
    async def test_load_reads_json_content(self, tmp_path):
        """Test load_results correctly reads stored JSON."""
        path = tmp_path / "data.json"
        test_data = [{"url": "test", "status": 200}]
        await save_results(test_data, path)
        loaded = await load_results(path)
        assert loaded == test_data

    def test_ensure_output_dir_uses_default_output_dir(self, monkeypatch, tmp_path):
        """Test ensure_output_dir defaults to OUTPUT_DIR."""
        from amalitech_training.python_advanced.LAB_5 import storage

        monkeypatch.setattr(storage, "OUTPUT_DIR", tmp_path)
        result = ensure_output_dir()
        assert result == tmp_path
        assert tmp_path.exists()

    def test_build_filename_uses_default_output_dir(self, tmp_path, monkeypatch):
        """Test build_filename creates file in OUTPUT_DIR when needed."""
        from amalitech_training.python_advanced.LAB_5 import storage

        monkeypatch.setattr(storage, "OUTPUT_DIR", tmp_path)
        filename = build_filename()
        assert filename.parent == tmp_path


class TestFetchWithDummySession:
    """Test fallback behavior when aiohttp is unavailable."""

    @pytest.mark.asyncio
    async def test_dummy_session_raises_on_get(self):
        """Test _DummySession raises ModuleNotFoundError when accessed."""
        from amalitech_training.python_advanced.LAB_5.fetcher import _DummySession

        dummy = _DummySession()
        with pytest.raises(ModuleNotFoundError):
            dummy.get("any_url")

    @pytest.mark.asyncio
    async def test_fetch_with_tasks_empty_list(self):
        """Test fetch_with_tasks returns empty list for empty URLs."""
        from .fetcher import fetch_with_tasks

        results = await fetch_with_tasks([])
        assert results == []

    @pytest.mark.asyncio
    async def test_fetch_with_tasks_uses_create_task(self):
        """Test fetch_with_tasks wraps each call in asyncio.create_task."""
        from .fetcher import fetch_with_tasks

        with patch(
            "amalitech_training.python_advanced.LAB_5.fetcher.fetch_url",
            new=AsyncMock(return_value=MOCK_FETCH),
        ):
            results = await fetch_with_tasks(["https://a.com", "https://b.com"])
        assert len(results) == 2


class TestPerformance:
    """Test benchmark and concurrency patterns."""

    def test_blocking_fetch_success(self):
        """Test _blocking_fetch returns result dict on success."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.read.return_value = b"<html>test</html>"
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = _blocking_fetch("https://example.com")
            assert result["url"] == "https://example.com"
            assert result["status"] == 200
            assert result["html"] == "<html>test</html>"
            assert result["error"] is None

    def test_blocking_fetch_url_error(self):
        """Test _blocking_fetch handles URLError gracefully."""
        from urllib.error import URLError

        with patch("urllib.request.urlopen", side_effect=URLError("not found")):
            result = _blocking_fetch("https://bad.example.com")
            assert result["url"] == "https://bad.example.com"
            assert result["status"] is None
            assert result["html"] is None
            assert result["error"] is not None

    def test_blocking_fetch_generic_exception(self):
        """Test _blocking_fetch handles generic exceptions."""
        with patch("urllib.request.urlopen", side_effect=Exception("connection failed")):
            result = _blocking_fetch("https://fail.example.com")
            assert result["error"] is not None

    def test_run_sequential_returns_timing(self):
        """Test run_sequential returns (results, elapsed_time)."""
        with patch(
            "amalitech_training.python_advanced.LAB_5.performance._blocking_fetch",
            return_value={
                "url": "https://a.com",
                "status": 200,
                "html": SAMPLE_HTML,
                "error": None,
            },
        ):
            results, elapsed = run_sequential(["https://a.com"])
        assert isinstance(results, list)
        assert len(results) == 1
        assert isinstance(elapsed, float)
        assert elapsed >= 0

    def test_run_threaded_returns_timing(self):
        """Test run_threaded returns (results, elapsed_time)."""
        with patch(
            "amalitech_training.python_advanced.LAB_5.performance._blocking_fetch",
            return_value={
                "url": "https://a.com",
                "status": 200,
                "html": SAMPLE_HTML,
                "error": None,
            },
        ):
            results, elapsed = run_threaded(["https://a.com"], max_workers=2)
        assert isinstance(results, list)
        assert len(results) == 1
        assert isinstance(elapsed, float)

    def test_run_async_returns_timing(self):
        """Test run_async returns (results, elapsed_time)."""
        with patch(
            "amalitech_training.python_advanced.LAB_5.performance._async_scrape",
            return_value=[extract_all(MOCK_FETCH)],
        ):
            results, elapsed = run_async(["https://a.com"])
        assert isinstance(results, list)
        assert isinstance(elapsed, float)

    def test_benchmark_returns_comparison_dict(self):
        """Test benchmark returns a dict with timing comparisons."""
        with patch(
            "amalitech_training.python_advanced.LAB_5.performance.run_sequential"
        ) as mock_seq, patch(
            "amalitech_training.python_advanced.LAB_5.performance.run_threaded"
        ) as mock_thread, patch(
            "amalitech_training.python_advanced.LAB_5.performance.run_async"
        ) as mock_async:
            mock_seq.return_value = ([extract_all(MOCK_FETCH)], 1.0)
            mock_thread.return_value = ([extract_all(MOCK_FETCH)], 0.5)
            mock_async.return_value = ([extract_all(MOCK_FETCH)], 0.3)

            result = benchmark(["https://a.com"])

        assert "urls_count" in result
        assert "sequential_s" in result
        assert "threaded_s" in result
        assert "async_s" in result
        assert result["urls_count"] == 1


class TestMain:
    """Test CLI entry point and main flow."""

    def test_main_with_demo_flag(self, capsys, monkeypatch):
        """Test main runs with --demo flag."""
        monkeypatch.setattr("sys.argv", ["prog", "--demo"])
        with patch("amalitech_training.python_advanced.LAB_5.main.scrape") as mock_scrape:
            from .main import main

            main()
        mock_scrape.assert_called_once()

    def test_main_with_urls(self, capsys, monkeypatch):
        """Test main accepts URLs as positional arguments."""
        test_urls = ["https://a.com", "https://b.com"]
        monkeypatch.setattr("sys.argv", ["prog"] + test_urls)
        with patch("amalitech_training.python_advanced.LAB_5.main.scrape") as mock_scrape:
            from .main import main

            main()
        mock_scrape.assert_called_once()
        call_args = mock_scrape.call_args[0][0]
        assert test_urls[0] in call_args or call_args == test_urls

    def test_main_with_bench_flag(self, monkeypatch):
        """Test main runs benchmark with --bench flag."""
        monkeypatch.setattr("sys.argv", ["prog", "--demo", "--bench"])
        with patch(
            "amalitech_training.python_advanced.LAB_5.performance.benchmark"
        ) as mock_bench:
            from .main import main

            main()
        mock_bench.assert_called_once()

    @pytest.mark.asyncio
    async def test_scrape_workflow(self, capsys, monkeypatch):
        """Test scrape function orchestrates the full pipeline."""
        test_urls = ["https://a.com"]
        mock_result = extract_all(MOCK_FETCH)

        with patch(
            "amalitech_training.python_advanced.LAB_5.main.fetch_all",
            new=AsyncMock(return_value=[MOCK_FETCH]),
        ), patch(
            "amalitech_training.python_advanced.LAB_5.main.process_results"
        ) as mock_process, patch(
            "amalitech_training.python_advanced.LAB_5.main.filter_successful",
            return_value=[mock_result],
        ), patch(
            "amalitech_training.python_advanced.LAB_5.main.map_to_summary"
        ) as mock_summary, patch(
            "amalitech_training.python_advanced.LAB_5.main.save_results",
            new=AsyncMock(),
        ):
            # Mock process_results async generator
            async def mock_gen(results):
                for r in results:
                    yield extract_all(r)

            mock_process.return_value = mock_gen([MOCK_FETCH])
            mock_summary.return_value = [
                {
                    "url": "https://a.com",
                    "title": "Test",
                    "words": 10,
                    "links": 2,
                    "headings": ["Main Heading"],
                    "status": 200,
                }
            ]

            from .main import scrape

            await scrape(test_urls)

        captured = capsys.readouterr()
        assert "Fetching" in captured.out
        assert "Saved to:" in captured.out


class TestAiohttpFallback:
    """Test aiohttp import fallback in fetcher."""

    @pytest.mark.asyncio
    async def test_fetch_url_without_aiohttp_mock(self):
        """Test fetch_url works when aiohttp is missing (uses mocked session)."""
        from .fetcher import fetch_url

        # Use a mock session that doesn't require aiohttp
        mock_session = MagicMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=SAMPLE_HTML)
        mock_session.get = MagicMock(return_value=mock_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        result = await fetch_url(mock_session, "https://test.com")
        assert result["url"] == "https://test.com"
        assert result["status"] == 200


class TestAiofilesFallback:
    """Test aiofiles import fallback in storage."""

    @pytest.mark.asyncio
    async def test_save_results_fallback_sync(self, tmp_path):
        """Test save_results falls back to sync write when aiofiles is None."""
        from amalitech_training.python_advanced.LAB_5 import storage

        original_aiofiles = storage.aiofiles
        try:
            storage.aiofiles = None
            path = tmp_path / "test.json"
            returned = await storage.save_results([MOCK_FETCH], path)
            assert returned == path
            assert path.exists()
            loaded = json.loads(path.read_text())
            assert loaded[0]["url"] == "https://example.com"
        finally:
            storage.aiofiles = original_aiofiles

    @pytest.mark.asyncio
    async def test_load_results_fallback_sync(self, tmp_path):
        """Test load_results falls back to sync read when aiofiles is None."""
        from amalitech_training.python_advanced.LAB_5 import storage

        path = tmp_path / "test.json"
        test_data = [{"url": "test", "data": "value"}]
        path.write_text(json.dumps(test_data))

        original_aiofiles = storage.aiofiles
        try:
            storage.aiofiles = None
            loaded = await storage.load_results(path)
            assert loaded == test_data
        finally:
            storage.aiofiles = original_aiofiles


class TestPerformanceEdgeCases:
    """Test performance module edge cases and exception handling."""

    def test_run_threaded_with_exception_in_future(self):
        """Test run_threaded handles exceptions from ThreadPoolExecutor futures."""
        with patch(
            "amalitech_training.python_advanced.LAB_5.performance._blocking_fetch",
            side_effect=Exception("fetch failed"),
        ):
            results, elapsed = run_threaded(["https://a.com"], max_workers=1)
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["error"] is not None


class TestBlockingFetch:
    def test_returns_required_keys(self):
        with patch("amalitech_training.python_advanced.LAB_5.performance.urllib_request.urlopen") as mock_open:
            resp = MagicMock()
            resp.status = 200
            resp.read.return_value = b"<html><title>T</title></html>"
            resp.__enter__ = MagicMock(return_value=resp)
            resp.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = resp
            result = _blocking_fetch("https://example.com")
        assert {"url", "status", "html", "error"} <= result.keys()

    def test_url_error_returns_error_dict(self):
        from urllib.error import URLError
        with patch("amalitech_training.python_advanced.LAB_5.performance.urllib_request.urlopen", side_effect=URLError("no route")):
            result = _blocking_fetch("https://unreachable.example.com")
        assert result["error"] is not None
        assert result["html"] is None

    def test_url_preserved(self):
        with patch("amalitech_training.python_advanced.LAB_5.performance.urllib_request.urlopen") as mock_open:
            resp = MagicMock()
            resp.status = 200
            resp.read.return_value = b"<html></html>"
            resp.__enter__ = MagicMock(return_value=resp)
            resp.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = resp
            result = _blocking_fetch("https://example.com/page")
        assert result["url"] == "https://example.com/page"


class TestRunSequential:
    def test_returns_results_and_time(self):
        with patch("amalitech_training.python_advanced.LAB_5.performance._blocking_fetch", return_value=MOCK_FETCH):
            results, elapsed = run_sequential(["https://a.com", "https://b.com"])
        assert isinstance(results, list)
        assert isinstance(elapsed, float)

    def test_count_matches_urls(self):
        with patch("amalitech_training.python_advanced.LAB_5.performance._blocking_fetch", return_value=MOCK_FETCH):
            results, _ = run_sequential(["https://a.com", "https://b.com"])
        assert len(results) == 2

    def test_results_enriched_by_extractor(self):
        with patch("amalitech_training.python_advanced.LAB_5.performance._blocking_fetch", return_value=MOCK_FETCH):
            results, _ = run_sequential(["https://example.com"])
        assert "title" in results[0]

    def test_empty_urls(self):
        results, _ = run_sequential([])
        assert results == []


class TestRunThreaded:
    def test_returns_results_and_time(self):
        with patch("amalitech_training.python_advanced.LAB_5.performance._blocking_fetch", return_value=MOCK_FETCH):
            results, elapsed = run_threaded(["https://a.com", "https://b.com"])
        assert isinstance(results, list)
        assert isinstance(elapsed, float)

    def test_count_matches_urls(self):
        with patch("amalitech_training.python_advanced.LAB_5.performance._blocking_fetch", return_value=MOCK_FETCH):
            results, _ = run_threaded(["https://a.com", "https://b.com"])
        assert len(results) == 2

    def test_results_enriched(self):
        with patch("amalitech_training.python_advanced.LAB_5.performance._blocking_fetch", return_value=MOCK_FETCH):
            results, _ = run_threaded(["https://example.com"])
        assert "title" in results[0]

    def test_single_worker_still_works(self):
        with patch("amalitech_training.python_advanced.LAB_5.performance._blocking_fetch", return_value=MOCK_FETCH):
            results, _ = run_threaded(["https://example.com"], max_workers=1)
        assert len(results) == 1


class TestRunAsync:
    def test_returns_results_and_time(self):
        async def mock_scrape(urls):
            return [MOCK_FETCH for _ in urls]

        with patch("amalitech_training.python_advanced.LAB_5.performance._async_scrape", mock_scrape):
            results, elapsed = run_async(["https://a.com"])
        assert isinstance(results, list)
        assert isinstance(elapsed, float)

    def test_count_matches_urls(self):
        async def mock_scrape(urls):
            return [MOCK_FETCH for _ in urls]

        with patch("amalitech_training.python_advanced.LAB_5.performance._async_scrape", mock_scrape):
            results, _ = run_async(["https://a.com", "https://b.com"])
        assert len(results) == 2


class TestBenchmark:
    def test_returns_required_keys(self):
        async def mock_scrape(urls):
            return [MOCK_FETCH for _ in urls]

        with patch("amalitech_training.python_advanced.LAB_5.performance._blocking_fetch", return_value=MOCK_FETCH):
            with patch("amalitech_training.python_advanced.LAB_5.performance._async_scrape", mock_scrape):
                report = benchmark(["https://example.com"])

        required = {"urls_count", "sequential_s", "threaded_s",
                    "async_s", "threaded_speedup", "async_speedup"}
        assert required <= report.keys()

    def test_urls_count_correct(self):
        async def mock_scrape(urls):
            return [MOCK_FETCH for _ in urls]

        with patch("amalitech_training.python_advanced.LAB_5.performance._blocking_fetch", return_value=MOCK_FETCH):
            with patch("amalitech_training.python_advanced.LAB_5.performance._async_scrape", mock_scrape):
                report = benchmark(["https://example.com", "https://b.com"])

        assert report["urls_count"] == 2

    def test_speedup_is_numeric(self):
        async def mock_scrape(urls):
            return [MOCK_FETCH for _ in urls]

        with patch("amalitech_training.python_advanced.LAB_5.performance._blocking_fetch", return_value=MOCK_FETCH):
            with patch("amalitech_training.python_advanced.LAB_5.performance._async_scrape", mock_scrape):
                report = benchmark(["https://example.com"])

        assert isinstance(report["threaded_speedup"], (int, float))
        assert isinstance(report["async_speedup"], (int, float))
