from __future__ import annotations
import pytest
from datetime import datetime
from .regex_patterns import (
    LOG_PATTERN,
    TIMESTAMP_PATTERN,
    is_valid_ip,
    is_valid_url,
    is_valid_timestamp,
    is_valid_method,
    classify_ip,
    clean_url,
    clean_whitespace,
)
from .decorators import timer, log_call, cache
from .log_parser import (
    build_pipeline,
    count_by_ip,
    count_by_status,
    count_by_url,
    extract_field,
    filter_by_ip,
    filter_by_method,
    filter_by_status,
    filter_by_status_range,
    filter_by_time_range,
    parse_line,
    parse_timestamp,
    total_bytes,
)
from .generators import (
    BatchIterator,
    group_by_hour,
    group_by_ip,
    group_by_status,
    paginate,
    parse_file,
    read_log_file,
    read_multiple_files,
    sliding_window,
    take_until_time,
)
from .analytics import (
    bandwidth_used,
    cached_top_urls,
    error_rate,
    filter_client_errors,
    filter_errors,
    filter_get,
    filter_post,
    filter_server_errors,
    filter_success,
    format_report,
    generate_report,
    status_breakdown,
    top_n_ips,
    top_n_urls,
)

SAMPLE_LOGS = [
    '192.168.1.1 - - [10/Oct/2023:08:00:01 -0700] "GET /index.html HTTP/1.1" 200 1024 "-" "Mozilla/5.0"',
    '192.168.1.2 - - [10/Oct/2023:08:00:05 -0700] "POST /login HTTP/1.1" 200 512 "-" "curl/7.68"',
    '10.0.0.5 - - [10/Oct/2023:08:01:10 -0700] "GET /missing HTTP/1.1" 404 128 "-" "Mozilla/5.0"',
    '10.0.0.5 - - [10/Oct/2023:08:01:15 -0700] "GET /admin HTTP/1.1" 403 64 "-" "Mozilla/5.0"',
    '172.16.0.1 - - [10/Oct/2023:09:00:00 -0700] "GET /api/data HTTP/1.1" 500 256 "-" "Python-requests"',
    '192.168.1.1 - - [10/Oct/2023:09:15:00 -0700] "GET /style.css HTTP/1.1" 200 2048 "-" "Mozilla/5.0"',
    '192.168.1.1 - - [10/Oct/2023:10:00:00 -0700] "GET /index.html HTTP/1.1" 200 1024 "-" "Mozilla/5.0"',
]


@pytest.fixture
def sample_entries():
    """Parse SAMPLE_LOGS into a list of LogEntry dicts"""
    return [e for e in map(parse_line, SAMPLE_LOGS) if e is not None]


@pytest.fixture
def sample_log_file(tmp_path):
    """Write SAMPLE_LOGS to a temporary file and return its path"""
    log_file = tmp_path / "access.log"
    log_file.write_text("\n".join(SAMPLE_LOGS) + "\n", encoding="utf-8")
    return log_file


class TestLogPattern:
    def test_parses_standard_line(self):
        el = LOG_PATTERN.match(SAMPLE_LOGS[0])
        assert el is not None
        assert el.group("ip") == "192.168.1.1"
        assert el.group("method") == "GET"
        assert el.group("status") == "200"

    def test_returns_none_for_garbage(self):
        assert LOG_PATTERN.match("this is not a log line") is None

    def test_captures_post_method(self):
        el = LOG_PATTERN.match(SAMPLE_LOGS[1])
        assert el.group("method") == "POST"

    def test_captures_error_status(self):
        el = LOG_PATTERN.match(SAMPLE_LOGS[2])
        assert el.group("status") == "404"


class TestTimePattern:
    def test_parses_time(self):
        timestamp = "10/Oct/2000:13:55:36 -0700"
        el = TIMESTAMP_PATTERN.match(timestamp)
        assert el is not None
        assert el.group("day") == "10"
        assert el.group("month") == "Oct"
        assert el.group("year") == "2000"
        assert el.group("hour") == "13"
        assert el.group("minute") == "55"
        assert el.group("second") == "36"
        assert el.group("tz") == "-0700"

    def test_returns_none_for_garbage(self):
        assert TIMESTAMP_PATTERN.match("this is not a valid time") is None


class TestValidationHelpers:
    def test_valid_ip(self):
        assert is_valid_ip("192.168.1.1") is True
        assert is_valid_ip("0.0.0.0") is True
        assert is_valid_ip("255.255.255.255") is True

    def test_invalid_ip(self):
        assert is_valid_ip("999.0.0.1") is False
        assert is_valid_ip("192.168.1") is False
        assert is_valid_ip("not-an-ip") is False

    def test_valid_url(self):
        assert is_valid_url("https://example.com/path") is True
        assert is_valid_url("http://api.example.com") is True

    def test_invalid_url(self):
        assert is_valid_url("ftp://bad.com") is False
        assert is_valid_url("not-a-url") is False

    def test_valid_url_with_query_string(self):
        assert is_valid_url("https://example.com/path?q=1") is True

    def test_valid_timestamp(self):
        assert is_valid_timestamp("10/Oct/2000:13:55:36 -0700") is True
        assert is_valid_timestamp("01/Oct/1988:13:00:45 -0700") is True

    def test_invalid_timestamp(self):
        assert is_valid_timestamp("10/Oct/2000:13:55:36") is False
        assert is_valid_timestamp("2000:13:55:36 -0700") is False

    def test_invalid_timestamp_bad_date(self):
        assert is_valid_timestamp("32/Oct/2000:13:55:36 -0700") is False

    def test_classify_ip_internal(self):
        assert classify_ip("192.168.1.1") == "internal"
        assert classify_ip("10.0.0.1") == "internal"
        assert classify_ip("172.16.0.1") == "internal"

    def test_classify_ip_external(self):
        assert classify_ip("8.8.8.8") == "external"
        assert classify_ip("1.1.1.1") == "external"

    def test_is_valid_method_valid(self):
        assert is_valid_method("GET") is True
        assert is_valid_method("POST") is True
        assert is_valid_method("PUT") is True
        assert is_valid_method("DELETE") is True
        assert is_valid_method("PATCH") is True
        assert is_valid_method("HEAD") is True

    def test_is_valid_method_invalid(self):
        assert is_valid_method("INVALID") is False
        assert is_valid_method("get") is False

    def test_clean_url_strips_query(self):
        assert clean_url("/page?foo=bar") == "/page"
        assert clean_url("/plain") == "/plain"

    def test_clean_whitespace(self):
        assert clean_whitespace("too   many   spaces") == "too many spaces"


class TestTimerDecorator:
    def test_function_still_returns_value(self):
        @timer
        def add(a, b):
            return a + b

        assert add(2, 3) == 5

    def test_preserves_function_name(self):
        @timer
        def my_func():
            pass

        assert my_func.__name__ == "my_func"


class TestLogCallDecorator:
    def test_function_still_returns_value(self):
        @log_call
        def multiply(a, b):
            return a * b

        assert multiply(3, 4) == 12

    def test_preserves_function_name(self):
        @log_call
        def my_func():
            pass

        assert my_func.__name__ == "my_func"


class TestCacheDecorator:
    def test_returns_correct_value(self):
        @cache()
        def square(n):
            return n * n

        assert square(5) == 25

    def test_caches_result(self):
        call_count = {"n": 0}

        @cache(maxsize=128)
        def slow(x):
            call_count["n"] += 1
            return x * 2

        slow(10)
        slow(10)
        assert call_count["n"] == 1

    def test_cache_info_exposed(self):
        @cache()
        def identity(x):
            return x

        identity(1)
        info = identity.cache_info()
        assert info.currsize >= 1

    def test_stacked_decorators(self):
        @timer
        @log_call
        @cache()
        def triple(n):
            return n * 3

        assert triple(7) == 21


class TestParseLine:
    def test_returns_dict_for_valid_line(self):
        entry = parse_line(SAMPLE_LOGS[0])
        assert isinstance(entry, dict)

    def test_ip_field(self):
        entry = parse_line(SAMPLE_LOGS[0])
        assert entry["ip"] == "192.168.1.1"

    def test_status_is_int(self):
        entry = parse_line(SAMPLE_LOGS[0])
        assert entry["status"] == 200

    def test_size_is_int(self):
        entry = parse_line(SAMPLE_LOGS[0])
        assert entry["size"] == 1024

    def test_returns_none_for_bad_line(self):
        assert parse_line("garbage") is None

    def test_returns_none_for_empty_line(self):
        assert parse_line("") is None

    def test_method_field(self):
        entry = parse_line(SAMPLE_LOGS[1])
        assert entry["method"] == "POST"

    def test_url_has_no_query_string(self):
        line = '1.2.3.4 - - [10/Oct/2023:08:00:01 -0700] "GET /search?q=hello HTTP/1.1" 200 512 "-" "-"'
        entry = parse_line(line)
        assert "?" not in entry["url"]


class TestParseTimestamp:
    def test_returns_datetime(self):
        dt = parse_timestamp("10/Oct/2023:08:00:01 -0700")
        assert isinstance(dt, datetime)
        assert dt.year == 2023
        assert dt.month == 10
        assert dt.hour == 8

    def test_returns_none_for_invalid(self):
        assert parse_timestamp("not a timestamp") is None


class TestFilterFunctions:
    def test_filter_by_status_200(self, sample_entries):
        results = list(filter_by_status(sample_entries, 200))
        assert all(e["status"] == 200 for e in results)
        assert len(results) == 4

    def test_filter_by_status_range_4xx(self, sample_entries):
        results = list(filter_by_status_range(sample_entries, 400, 499))
        assert all(400 <= e["status"] <= 499 for e in results)

    def test_filter_by_ip(self, sample_entries):
        results = list(filter_by_ip(sample_entries, "10.0.0.5"))
        assert all(e["ip"] == "10.0.0.5" for e in results)
        assert len(results) == 2

    def test_filter_by_method_get(self, sample_entries):
        results = list(filter_by_method(sample_entries, "GET"))
        assert all(e["method"] == "GET" for e in results)

    def test_filter_by_time_range(self, sample_entries):
        start = datetime(2023, 10, 10, 8, 0, 0)
        end = datetime(2023, 10, 10, 8, 59, 59)
        results = list(filter_by_time_range(sample_entries, start, end))
        assert all(start <= e["timestamp"] <= end for e in results)


class TestAggregations:
    def test_total_bytes(self, sample_entries):
        total = total_bytes(sample_entries)
        assert total == sum(e["size"] for e in sample_entries)

    def test_count_by_status_keys(self, sample_entries):
        counts = count_by_status(sample_entries)
        assert 200 in counts
        assert 404 in counts

    def test_count_by_ip(self, sample_entries):
        counts = count_by_ip(sample_entries)
        assert counts["192.168.1.1"] == 3

    def test_count_by_url(self, sample_entries):
        counts = count_by_url(sample_entries)
        assert "/index.html" in counts

    def test_extract_field_ips(self, sample_entries):
        ips = list(extract_field(sample_entries, "ip"))
        assert all(isinstance(ip, str) for ip in ips)
        assert "192.168.1.1" in ips

    def test_extract_field_status(self, sample_entries):
        statuses = list(extract_field(sample_entries, "status"))
        assert all(isinstance(s, int) for s in statuses)
        assert 200 in statuses


class TestBuildPipeline:
    def test_returns_list(self, sample_entries):
        result = build_pipeline(SAMPLE_LOGS)
        assert isinstance(result, list)

    def test_with_status_filter(self):
        result = build_pipeline(
            SAMPLE_LOGS, filters=[lambda e: filter_by_status(e, 200)]
        )
        assert all(e["status"] == 200 for e in result)

    def test_chained_filters(self):
        result = build_pipeline(
            SAMPLE_LOGS,
            filters=[
                lambda e: filter_by_method(e, "GET"),
                lambda e: filter_by_status(e, 200),
            ],
        )
        assert all(e["method"] == "GET" and e["status"] == 200 for e in result)


class TestReadLogFile:
    def test_yields_strings(self, sample_log_file):
        lines = list(read_log_file(sample_log_file))
        assert all(isinstance(line, str) for line in lines)

    def test_correct_line_count(self, sample_log_file):
        lines = list(read_log_file(sample_log_file))
        assert len(lines) == len(SAMPLE_LOGS)


class TestReadMultipleFiles:
    def test_chains_two_files(self, tmp_path):
        f1 = tmp_path / "a.log"
        f2 = tmp_path / "b.log"
        f1.write_text(SAMPLE_LOGS[0] + "\n")
        f2.write_text(SAMPLE_LOGS[1] + "\n")
        lines = list(read_multiple_files(f1, f2))
        assert len(lines) == 2


class TestParseFile:
    def test_yields_dicts(self, sample_log_file):
        entries = list(parse_file(sample_log_file))
        assert all(isinstance(e, dict) for e in entries)

    def test_skips_blank_lines(self, tmp_path):
        f = tmp_path / "with_blanks.log"
        f.write_text(SAMPLE_LOGS[0] + "\n\n" + SAMPLE_LOGS[1] + "\n")
        entries = list(parse_file(f))
        assert len(entries) == 2


class TestBatchIterator:
    def test_batch_size(self, sample_entries):
        batches = list(BatchIterator(iter(sample_entries), size=2))
        for batch in batches[:-1]:
            assert len(batch) == 2

    def test_last_batch_can_be_smaller(self, sample_entries):
        batches = list(BatchIterator(iter(sample_entries), size=4))
        assert sum(len(b) for b in batches) == len(sample_entries)

    def test_empty_source(self):
        batches = list(BatchIterator(iter([]), size=5))
        assert batches == []


class TestGroupBy:
    def test_group_by_status(self, sample_entries):
        groups = group_by_status(sample_entries)
        assert 200 in groups
        assert all(e["status"] == 200 for e in groups[200])

    def test_group_by_hour(self, sample_entries):
        groups = group_by_hour(sample_entries)
        for hour, entries in groups.items():
            assert all(e["timestamp"].hour == hour for e in entries)

    def test_group_by_ip(self, sample_entries):
        groups = group_by_ip(sample_entries)
        for ip, entries in groups.items():
            assert all(e["ip"] == ip for e in entries)


class TestPaginate:
    def test_first_page(self, sample_entries):
        page = paginate(iter(sample_entries), page=0, page_size=3)
        assert len(page) == 3

    def test_second_page(self, sample_entries):
        page = paginate(iter(sample_entries), page=1, page_size=3)
        assert len(page) == 3

    def test_page_beyond_end(self, sample_entries):
        page = paginate(iter(sample_entries), page=99, page_size=3)
        assert page == []


class TestTakeUntilTime:
    def test_stops_at_cutoff(self, sample_entries):
        cutoff = datetime(2023, 10, 10, 9, 0, 0)
        result = list(take_until_time(iter(sample_entries), cutoff))
        assert all(e["timestamp"] < cutoff for e in result)


class TestSlidingWindow:
    def test_window_size(self, sample_entries):
        windows = list(sliding_window(iter(sample_entries), size=3))
        assert all(len(w) == 3 for w in windows)

    def test_window_count(self, sample_entries):
        n = len(sample_entries)
        windows = list(sliding_window(iter(sample_entries), size=3))
        assert len(windows) == n - 3 + 1

    def test_window_smaller_than_data(self):
        small_data = [
            {"ip": "1.1.1.1", "status": 200},
            {"ip": "2.2.2.2", "status": 404},
        ]
        windows = list(sliding_window(iter(small_data), size=5))
        assert windows == []


class TestAnalyticsFunctions:
    def test_top_n_ips_returns_n(self, sample_entries):
        result = top_n_ips(sample_entries, n=2)
        assert len(result) == 2

    def test_top_n_ips_sorted_desc(self, sample_entries):
        result = top_n_ips(sample_entries, n=3)
        counts = [c for _, c in result]
        assert counts == sorted(counts, reverse=True)

    def test_top_n_urls_returns_n(self, sample_entries):
        result = top_n_urls(sample_entries, n=2)
        assert len(result) == 2

    def test_status_breakdown_keys(self, sample_entries):
        result = status_breakdown(sample_entries)
        assert 200 in result

    def test_error_rate_between_0_and_1(self, sample_entries):
        rate = error_rate(sample_entries)
        assert 0.0 <= rate <= 1.0

    def test_error_rate_empty(self):
        assert error_rate([]) == 0.0

    def test_bandwidth_used(self, sample_entries):
        bw = bandwidth_used(sample_entries)
        assert bw > 0

    def test_cached_top_urls(self, sample_entries):
        result = cached_top_urls(sample_entries, n=3)
        assert len(result) <= 3


class TestPartialFilters:
    def test_filter_success(self, sample_entries):
        result = list(filter_success(sample_entries))
        assert all(200 <= e["status"] <= 299 for e in result)

    def test_filter_errors(self, sample_entries):
        result = list(filter_errors(sample_entries))
        assert all(e["status"] >= 400 for e in result)

    def test_filter_client_errors(self, sample_entries):
        result = list(filter_client_errors(sample_entries))
        assert all(400 <= e["status"] <= 499 for e in result)

    def test_filter_server_errors(self, sample_entries):
        result = list(filter_server_errors(sample_entries))
        assert all(500 <= e["status"] <= 599 for e in result)

    def test_filter_get(self, sample_entries):
        result = list(filter_get(sample_entries))
        assert all(e["method"] == "GET" for e in result)

    def test_filter_post(self, sample_entries):
        result = list(filter_post(sample_entries))
        assert all(e["method"] == "POST" for e in result)


class TestGenerateReport:
    def test_report_has_required_keys(self, sample_entries):
        report = generate_report(sample_entries)
        required = {
            "total_requests",
            "total_bytes",
            "error_rate",
            "status_breakdown",
            "top_ips",
            "top_urls",
            "error_count",
            "server_error_count",
        }
        assert required <= report.keys()

    def test_total_requests_matches(self, sample_entries):
        report = generate_report(sample_entries)
        assert report["total_requests"] == len(sample_entries)

    def test_error_count_positive(self, sample_entries):
        report = generate_report(sample_entries)
        assert report["error_count"] >= 0


class TestFormatReport:
    def test_returns_string(self, sample_entries):
        report = generate_report(sample_entries)
        output = format_report(report)
        assert isinstance(output, str)

    def test_contains_total_requests(self, sample_entries):
        report = generate_report(sample_entries)
        output = format_report(report)
        assert "Total requests" in output
