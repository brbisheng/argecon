"""Format-specific parsers that convert raw files into document objects."""

from .docx_parser import parse_docx

__all__ = ["parse_docx"]
