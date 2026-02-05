"""Vercel serverless entry point for SAINSIP."""

# Vercel looks for an `app` variable in this file.
# Import the FastAPI application instance from our package.
from sainsip.app import app  # noqa: F401
