"""
Compatibility shim for legacy test imports.
"""

from tests.platform.fakes import MockKRAAPIService, MockRedisClient

__all__ = ["MockKRAAPIService", "MockRedisClient"]
