"""Runtime health checks for the application."""

from .environment_check import run_health_check

__all__ = ["run_health_check"]
