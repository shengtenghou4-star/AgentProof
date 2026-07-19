"""Trace format adapters."""

from .otel import convert_otlp_json

__all__ = ["convert_otlp_json"]
