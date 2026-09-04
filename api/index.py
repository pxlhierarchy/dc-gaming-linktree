"""Vercel serverless entrypoint.

Vercel's Python runtime looks for a module-level WSGI callable named `app`
inside files under api/, so this re-exports the Flask app from the project
root. The root is not on sys.path by default when the function is invoked,
hence the explicit insert.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402  (must follow the sys.path insert)

__all__ = ['app']
