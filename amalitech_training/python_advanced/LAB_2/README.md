# Log File Analyzer

## Overview

A professional web server access log analyzer that parses Apache/Nginx format logs, extracts structured information using advanced regex patterns, and generates comprehensive analytics reports. This project demonstrates best practices in Python including functional programming, decorators, generators, and itertools utilities.

## Features

### Core Functionality
- **Log Parsing**: Extract data from Apache and Nginx server logs
- **Structured Data Extraction**: Convert raw log lines into organized dictionaries
- **Analytics Reports**: Generate insights about server traffic patterns
- **Large File Processing**: Handle massive log files efficiently using generators
- **Performance Optimization**: Built-in timing, caching, and batch processing

## Implementation Details

### 1. Regular Expression Patterns

Extract structured information from log entries using compiled regex patterns:

```python
# Named groups for clarity
IP Pattern:        (?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})
Timestamp Pattern: (?P<timestamp>\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})
Method Pattern:    (?P<method>GET|POST|PUT|DELETE|HEAD)
Status Pattern:    (?P<status>\d{3})
URL Pattern:       (?P<url>[\S]+)
```

**Key Operations:**
- Compile regex patterns for common log formats
- Extract IP addresses, timestamps, HTTP methods, status codes, URLs
- Use named groups (`?P<name>`) for clarity and maintainability
- Implement validation patterns for email, URL, and IP addresses
- Use `re.sub()` for data cleaning and normalization

### 2. Functional Programming

Process and transform log data using functional techniques:

**`map()`** - Transform log lines to structured dictionaries
```python
log_dicts = map(parse_log_line, raw_logs)
```

**`filter()`** - Select specific entries by status code, time range, or other criteria
```python
errors = filter(lambda log: log['status'] >= 400, logs)
success = filter(lambda log: log['status'] < 400, logs)
```

**`reduce()`** - Aggregate data (counts, sums, statistics)
```python
from functools import reduce
total_bytes = reduce(lambda acc, log: acc + log['bytes'], logs, 0)
```

**Chaining Operations** - Build readable data processing pipelines
```python
# Example pipeline: filter → transform → aggregate
pipeline = filter(is_error, logs) | map(extract_url) | reduce(count_errors)
```

### 3. Generators & Iterators

Efficiently process large files without loading everything into memory:

**Generator Function** - Read and yield log lines one at a time
```python
def read_log_file(filepath):
    with open(filepath, 'r') as f:
        for line in f:
            yield line.strip()
```

**Custom Iterators** - Batch log entries for group processing
```python
def batch_logs(logs, batch_size):
    batch = []
    for log in logs:
        batch.append(log)
        if len(batch) == batch_size:
            yield batch
            batch = []
    if batch:
        yield batch
```

**itertools.groupby()** - Group logs by status code, hour, or IP
```python
from itertools import groupby
grouped = groupby(sorted_logs, key=lambda log: log['status'])
```

**itertools.islice()** - Implement pagination
```python
from itertools import islice
page = islice(logs, offset, offset + limit)
```

### 4. Decorators

### @timer Decorator
Measure function execution time for performance monitoring:
```python
@timer
def analyze_logs(log_file):
    # Function execution time is automatically tracked
    pass
```

### @cache Decorator
Use `functools.lru_cache` to cache expensive operations:
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_status_code_count(status):
    # Results are cached for repeated calls
    pass
```

### @log_call Decorator
Trace function calls for debugging and monitoring:
```python
@log_call
def parse_log_line(line):
    # Function call is logged with arguments and return value
    pass
```

### Decorator Chaining
Combine multiple decorators for comprehensive functionality:
```python
@timer
@log_call
@cache
def expensive_analysis(logs):
    pass
```

### 5. itertools & functools Utilities

**`itertools.chain()`** - Combine multiple log files into one stream
```python
from itertools import chain
all_logs = chain(read_log_file('access.log'), read_log_file('old_access.log'))
```

**`itertools.takewhile()`** - Filter logs within a time range
```python
from itertools import takewhile
recent_logs = takewhile(lambda log: log['timestamp'] > cutoff_time, logs)
```

**`functools.partial()`** - Create specialized filter functions
```python
from functools import partial
filter_status_4xx = partial(filter_by_status, min_status=400, max_status=499)
```

## Project Structure

```
LAB_2/
├── regex_patterns.py          # Compiled regex patterns and validation
├── log_parser.py              # Log parsing and transformation functions
├── generators.py              # Generator and iterator implementations
├── decorators.py              # Timer, cache, and logging decorators
├── analytics.py               # Report generation and aggregations
├── main.py                    # Main application entry point
└── test_lab2.py               # Comprehensive test suite
```

## Usage

### Basic Log Analysis

```python
from log_parser import parse_log_file
from analytics import generate_report

# Generate analysis report
report = generate_report('apache_access.log')
print(report)
```

### Advanced Filtering

```python
from log_parser import parse_log_file
from functools import reduce

# Find all 4xx and 5xx errors
logs = parse_log_file('access.log')
errors = filter(lambda log: log['status'] >= 400, logs)
error_count = reduce(lambda acc, _: acc + 1, errors, 0)
print(f"Total errors: {error_count}")
```

### Batch Processing Large Files

```python
from generators import batch_logs
from log_parser import read_log_file

# Process logs in batches of 1000
for batch in batch_logs(read_log_file('huge.log'), batch_size=1000):
    process_batch(batch)
```

### Performance Monitoring

```python
from analytics import analyze_logs
from decorators import timer

# Function automatically times itself
# Output: analyze_logs executed in 2.345 seconds
result = analyze_logs('access.log')
```

## Lessons Learned

This project demonstrates:

1. **Memory Efficiency**: Generators process gigabytes of data without memory issues
2. **Code Readability**: Functional pipelines express intent clearly
3. **Performance**: Decorators optimize without changing core logic
4. **Maintainability**: Named regex groups make pattern updates easy
5. **Reusability**: Partial functions and decorators create flexible components

## Learning Outcomes

- Master regex with named groups and validation patterns
- Apply functional programming patterns in Python
- Build memory-efficient generators for large datasets
- Create reusable decorators for cross-cutting concerns
- Leverage itertools for advanced data manipulation
- Design composable data processing pipelines

## Testing

Run the test suite to verify all functionality:

```bash
pytest test_log_analyzer.py -v
```

## Requirements

- Python 3.8+
- Standard library modules: `re`, `functools`, `itertools`

## Author Notes

This implementation prioritizes:
- **Clean Code**: Simple, readable solutions over clever complexity
- **Performance**: Generators and caching for real-world-scale data
- **Documentation**: Clear patterns and examples for learning
- **Testability**: Functional designs that are easy to test
