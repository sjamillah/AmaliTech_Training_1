from .regex_patterns import (
    LOG_PATTERN,
    TIMESTAMP_PATTERN,
    is_valid_ip,
    is_valid_url,
    is_valid_timestamp,
    clean_url,
    clean_whitespace,
)
from .decorators import timer, log_call, cache

SAMPLE_LOGS = [
    '192.168.1.1 - - [10/Oct/2023:08:00:01 -0700] "GET /index.html HTTP/1.1" 200 1024 "-" "Mozilla/5.0"',
    '192.168.1.2 - - [10/Oct/2023:08:00:05 -0700] "POST /login HTTP/1.1" 200 512 "-" "curl/7.68"',
    '10.0.0.5 - - [10/Oct/2023:08:01:10 -0700] "GET /missing HTTP/1.1" 404 128 "-" "Mozilla/5.0"',
    '10.0.0.5 - - [10/Oct/2023:08:01:15 -0700] "GET /admin HTTP/1.1" 403 64 "-" "Mozilla/5.0"',
    '172.16.0.1 - - [10/Oct/2023:09:00:00 -0700] "GET /api/data HTTP/1.1" 500 256 "-" "Python-requests"',
    '192.168.1.1 - - [10/Oct/2023:09:15:00 -0700] "GET /style.css HTTP/1.1" 200 2048 "-" "Mozilla/5.0"',
    '192.168.1.1 - - [10/Oct/2023:10:00:00 -0700] "GET /index.html HTTP/1.1" 200 1024 "-" "Mozilla/5.0"',
]


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

    def test_valid_timestamp(self):
        assert is_valid_timestamp("10/Oct/2000:13:55:36 -0700") is True
        assert is_valid_timestamp("01/Oct/1988:13:00:45 -0700") is True

    def test_invalid_timestamp(self):
        assert is_valid_timestamp("10/Oct/2000:13:55:36") is False
        assert is_valid_timestamp("20/Oct/200:13:00:98 -0700") is False
        assert is_valid_timestamp("2000:13:55:36 -0700") is False

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
