"""Application-level exceptions."""

from __future__ import annotations


class HelperBotError(Exception):
    """Base error for the application."""


class ConfigurationError(HelperBotError):
    """Invalid or missing configuration."""


class IngestError(HelperBotError):
    """Failed to ingest a user payload."""


class QueryError(HelperBotError):
    """Failed to answer a user question."""
