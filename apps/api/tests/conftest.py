"""
pytest configuration and fixtures for KRA API v2 tests.
"""

from tests.platform.fixtures import (  # noqa: F401
    anyio_backend,
    api_app,
    auth_headers_factory,
    authenticated_client,
    clean_db,
    client,
    controlled_task_runner,
    db_api_key_factory,
    db_session,
    env_api_key_headers,
    inline_task_runner,
    mock_kra_api_response,
    redis_client,
    sample_race_data,
    test_db_engine,
    test_settings,
)
