from enum import IntEnum


class ExitCode(IntEnum):
    OK = 0
    RUNTIME = 1
    USAGE = 2
    CONFIG = 3
    INPUT = 4
    AUTH = 5
    API = 6
    DEPENDENCY = 7


class VoiceDashboardError(RuntimeError):
    """Base error type for user-facing CLI failures."""


class ConfigError(VoiceDashboardError):
    """Raised when the local configuration file is invalid."""


class InputSourceError(VoiceDashboardError):
    """Raised when the requested input source cannot be read."""


class TTSBatchError(VoiceDashboardError):
    """Raised when the TTS batch job cannot continue."""


class ApiError(TTSBatchError):
    """Raised for API-facing request or response failures."""


class RetryableApiError(ApiError):
    """Raised for API failures that are safe to retry."""


class AuthenticationError(ApiError):
    """Raised when authentication is missing or rejected."""


class DependencyError(TTSBatchError):
    """Raised when an external command or dependency is unavailable."""


def exit_code_for_error(error: BaseException) -> int:
    if isinstance(error, ConfigError):
        return ExitCode.CONFIG
    if isinstance(error, InputSourceError):
        return ExitCode.INPUT
    if isinstance(error, AuthenticationError):
        return ExitCode.AUTH
    if isinstance(error, ApiError):
        return ExitCode.API
    if isinstance(error, DependencyError):
        return ExitCode.DEPENDENCY
    if isinstance(error, TTSBatchError):
        return ExitCode.RUNTIME
    return ExitCode.RUNTIME
