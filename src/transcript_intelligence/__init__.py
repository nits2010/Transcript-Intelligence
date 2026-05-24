"""Transcript Intelligence — AegisCloud meeting analytics pipeline."""

from .ingest import classify_call_type, load_all_meetings

__all__ = ["load_all_meetings", "classify_call_type"]
__version__ = "0.1.0"
