"""Schemas module for TinyTravel API.
Re-exports executable models from api.models for backward compatibility.
"""
try:
    from .models import *
except ImportError:
    from models import *
