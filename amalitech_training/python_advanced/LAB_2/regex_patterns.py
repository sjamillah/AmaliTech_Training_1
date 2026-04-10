"""
Compiled regex patterns for Apache/Nginx log parsing and validation.
All patterns use named groups for readability and reliable extraction.
"""

import re
from datetime import datetime

LOG_PATTERN = re.compile(
    r"(?P<ip>\d{1,3}(?:\.\d{1,3}){3})\s+"  # IP address
    r"(?P<ident>\S+)\s+"  # ident (-)
    r"(?P<user>\S+)\s+"  # user
    r"\[(?P<timestamp>[^\]]+)\]\s+"  # timestamp
    r'"(?P<method>[A-Z]+)\s+'  # HTTP method
    r"(?P<url>\S+)\s+"  # requested URL
    r'(?P<protocol>HTTP/\d\.\d)"\s+'  # protocol
    r"(?P<status>\d{3})\s+"  # status code
    r"(?P<size>\d+|-)"  # response size
    r'(?:\s+"(?P<referer>[^"]*)"\s+"(?P<agent>[^"]*)")?'  # optional referer+agent
)

TIMESTAMP_PATTERN = re.compile(
    r"(?P<day>\d{2})/(?P<month>[A-Za-z]{3})/(?P<year>\d{4})"
    r":(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})"
    r"\s+(?P<tz>[+-]\d{4})"
)

IP_VALIDATION = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}" r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$"
)

URL_VALIDATION = re.compile(
    r"^https?://"
    r"(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}"
    r"(?:/[^?#]*)?"
    r"(?:\?[^#]*)?"
    r"(?:#.*)?$"
)

TIMESTAMP_VALIDATION = re.compile(
    r"^(?P<day>\d{2})/(?P<month>[A-Za-z]{3})/(?P<year>\d{4}):"
    r"(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2}) "
    r"(?P<tz>[+-]\d{4})$"
)

# Data cleaning patterns
QUERY_STRING_PATTERN = re.compile(r"\?.*$")  # strips query params from URL
MULTIPLE_SPACES = re.compile(r" {2,}")  # collapses extra whitespace
NON_PRINTABLE = re.compile(r"[^\x20-\x7E]")  # strips non-printable chars


def clean_url(url: str) -> str:
    """Remove query string from a URL path."""
    return QUERY_STRING_PATTERN.sub("", url)


def clean_whitespace(text: str) -> str:
    """Collapse multiple spaces into one."""
    return MULTIPLE_SPACES.sub(" ", text).strip()


def clean_log_line(line: str) -> str:
    """Strip non-printable characters from a raw log line."""
    return NON_PRINTABLE.sub("", line)


def is_valid_ip(ip: str) -> bool:
    """Return True if ip matches a valid IPv4 address."""
    return bool(IP_VALIDATION.match(ip))


def classify_ip(ip: str) -> str:
    """Returns 'internal' or 'external' without rejecting any IP"""
    if ip.startswith(("192.168.", "10.", "172.16.")):
        return "internal"
    return "external"


MAX_URL_LENGTH = 2048


def is_valid_url(url: str) -> bool:
    """Return True if url is a well-formed HTTP/HTTPS URL."""
    url = clean_url(url)
    if len(url) > MAX_URL_LENGTH:
        return False
    return bool(URL_VALIDATION.match(url))


def is_valid_timestamp(timestamp: str):
    """Return True if timestamp is well-formatted"""
    match = TIMESTAMP_VALIDATION.match(timestamp)
    if not match:
        return False

    # Extract numeric components
    try:
        datetime.strptime(
            f"{match.group('day')}/{match.group('month')}/{match.group('year')} "
            f"{match.group('hour')}:{match.group('minute')}:{match.group('second')}",
            "%d/%b/%Y %H:%M:%S",
        )
        return True
    except ValueError:
        return False


ALLOWED_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"}


def is_valid_method(method: str) -> bool:
    return method in ALLOWED_METHODS
