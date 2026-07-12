"""Helpers for making decisions from parsed database URLs."""

from urllib.parse import urlsplit


def is_supabase_pooler_url(database_url: str) -> bool:
    """Return whether the URL targets Supabase's pooler domain.

    Parse the hostname instead of searching the entire URL so credentials, paths,
    and query parameters cannot spoof the pooler classification.
    """
    hostname = urlsplit(database_url).hostname
    if hostname is None:
        return False
    hostname = hostname.rstrip(".").lower()
    return hostname == "pooler.supabase.com" or hostname.endswith(
        ".pooler.supabase.com"
    )
