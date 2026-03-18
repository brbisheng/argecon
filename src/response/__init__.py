"""Response templating and assembly."""

from .response_builder import build_structured_response
from .templates import RESPONSE_TEMPLATES

__all__ = ["RESPONSE_TEMPLATES", "build_structured_response"]
