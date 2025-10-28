"""
Structured Logging Configuration

Features:
- JSON structured logs for production
- Human-readable console logs for development
- Rotating file handlers
- Error tracking and summarization
- Request ID tracking
- Performance metrics

Usage:
    from logging_config import setup_logging, get_logger

    # Setup at application start
    setup_logging(log_level='INFO', log_file='logs/app.log')

    # Get logger in modules
    logger = get_logger(__name__)
    logger.info("Processing transaction", extra={'request_id': '123', 'user_id': '456'})
"""

import logging
import logging.config
import logging.handlers
import json
import time
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from collections import Counter


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON

        Args:
            record: Log record

        Returns:
            JSON string
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }

        # Add extra fields from logger.info(..., extra={...})
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms
        if hasattr(record, 'transaction_id'):
            log_data['transaction_id'] = record.transaction_id

        return json.dumps(log_data)


class HumanReadableFormatter(logging.Formatter):
    """Human-readable formatter for console output"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record in human-readable format"""
        # Color codes for terminal (optional)
        colors = {
            'DEBUG': '\033[36m',     # Cyan
            'INFO': '\033[32m',      # Green
            'WARNING': '\033[33m',   # Yellow
            'ERROR': '\033[31m',     # Red
            'CRITICAL': '\033[35m',  # Magenta
            'RESET': '\033[0m'
        }

        # Get color for level (if terminal supports it)
        level_color = colors.get(record.levelname, '')
        reset_color = colors['RESET']

        # Format: [LEVEL] module:function - message
        base_format = f"{level_color}[{record.levelname}]{reset_color} {record.module}:{record.funcName} - {record.getMessage()}"

        # Add exception info if present
        if record.exc_info:
            exc_text = '\n'.join(traceback.format_exception(*record.exc_info))
            base_format += f"\n{exc_text}"

        return base_format


def setup_logging(log_level: str = 'INFO',
                 log_file: str = 'logs/app.log',
                 json_logs: bool = False,
                 max_bytes: int = 10485760,  # 10MB
                 backup_count: int = 5):
    """
    Configure application logging

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        json_logs: If True, use JSON format for file logs
        max_bytes: Max log file size before rotation (default 10MB)
        backup_count: Number of backup files to keep (default 5)
    """
    # Create logs directory if it doesn't exist
    log_dir = Path(log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                '()': JSONFormatter
            },
            'human': {
                '()': HumanReadableFormatter
            },
            'simple': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'human',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': log_level,
                'formatter': 'json' if json_logs else 'simple',
                'filename': log_file,
                'maxBytes': max_bytes,
                'backupCount': backup_count,
                'encoding': 'utf-8'
            }
        },
        'root': {
            'level': log_level,
            'handlers': ['console', 'file']
        }
    }

    logging.config.dictConfig(config)

    # Log initialization
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized: level={log_level}, file={log_file}, json={json_logs}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance

    Args:
        name: Logger name (usually __name__ from calling module)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class ErrorSummary:
    """Track and summarize errors for monitoring and debugging"""

    def __init__(self):
        self.errors = []

    def log_error(self, error_type: str, message: str, context: Optional[Dict] = None):
        """
        Log error with context

        Args:
            error_type: Type of error (e.g., 'ParseError', 'ValidationError')
            message: Error message
            context: Additional context (transaction_id, file_name, etc.)
        """
        self.errors.append({
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'type': error_type,
            'message': message,
            'context': context or {}
        })

    def get_summary(self) -> Dict:
        """
        Get error summary

        Returns:
            Dictionary with error statistics
        """
        if not self.errors:
            return {
                'total_errors': 0,
                'error_types': {},
                'recent_errors': []
            }

        error_types = Counter(e['type'] for e in self.errors)

        return {
            'total_errors': len(self.errors),
            'error_types': dict(error_types),
            'recent_errors': self.errors[-10:]  # Last 10 errors
        }

    def clear(self):
        """Clear error history"""
        self.errors = []


class PerformanceLogger:
    """Log performance metrics for operations"""

    def __init__(self, logger: logging.Logger, operation_name: str):
        """
        Initialize performance logger

        Args:
            logger: Logger instance
            operation_name: Name of operation being timed
        """
        self.logger = logger
        self.operation_name = operation_name
        self.start_time = None

    def __enter__(self):
        """Start timing"""
        self.start_time = time.time()
        self.logger.debug(f"Started: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and log duration"""
        duration_ms = (time.time() - self.start_time) * 1000
        if exc_type is None:
            self.logger.info(f"Completed: {self.operation_name}",
                           extra={'duration_ms': round(duration_ms, 2)})
        else:
            self.logger.error(f"Failed: {self.operation_name}",
                            extra={'duration_ms': round(duration_ms, 2)},
                            exc_info=(exc_type, exc_val, exc_tb))


def read_error_logs(log_file: str = 'logs/app.log', last_n: int = 100) -> list:
    """
    Read error logs from file

    Args:
        log_file: Path to log file
        last_n: Number of recent errors to return

    Returns:
        List of error log entries
    """
    log_path = Path(log_file)
    if not log_path.exists():
        return []

    errors = []

    try:
        with open(log_path, 'r') as f:
            for line in f:
                try:
                    log_entry = json.loads(line)
                    if log_entry.get('level') in ['ERROR', 'CRITICAL']:
                        errors.append(log_entry)
                except json.JSONDecodeError:
                    # Not a JSON log line, skip
                    continue
    except Exception as e:
        logging.error(f"Failed to read error logs: {e}")

    return errors[-last_n:]


# Usage Examples
if __name__ == "__main__":
    # Example 1: Basic setup
    setup_logging(log_level='INFO', log_file='logs/test.log')

    logger = get_logger(__name__)
    logger.info("Application started")
    logger.debug("Debug message (won't show unless level=DEBUG)")
    logger.warning("This is a warning")

    # Example 2: Structured logging with extra fields
    logger.info("Processing transaction",
               extra={
                   'request_id': 'req_12345',
                   'transaction_id': 'txn_67890',
                   'user_id': 'user_999'
               })

    # Example 3: Performance logging
    with PerformanceLogger(logger, "data_processing"):
        time.sleep(0.1)  # Simulate work
        logger.info("Processed 100 records")

    # Example 4: Error tracking
    error_tracker = ErrorSummary()
    error_tracker.log_error('ParseError', 'Failed to parse PDF', {'file': 'statement.pdf'})
    error_tracker.log_error('ValidationError', 'Invalid amount', {'txn_id': '123'})

    summary = error_tracker.get_summary()
    print(f"Error Summary: {summary}")

    # Example 5: Exception logging
    try:
        result = 1 / 0
    except Exception as e:
        logger.error("Division error", exc_info=True)
