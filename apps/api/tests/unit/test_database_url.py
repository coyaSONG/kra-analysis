from utils.database_url import is_supabase_pooler_url


def test_recognizes_supabase_pooler_hosts():
    assert is_supabase_pooler_url(
        "postgresql+asyncpg://user:pass@aws-0-ap-northeast-2.pooler.supabase.com/db"
    )
    assert is_supabase_pooler_url("postgresql://user@pooler.supabase.com/db")


def test_rejects_pooler_text_outside_hostname():
    assert not is_supabase_pooler_url(
        "postgresql://pooler.supabase.com@attacker.example/db"
    )
    assert not is_supabase_pooler_url("postgresql://db.example/pooler.supabase.com")
    assert not is_supabase_pooler_url(
        "postgresql://pooler.supabase.com.attacker.example/db"
    )


def test_handles_invalid_or_case_variant_urls():
    assert is_supabase_pooler_url("POSTGRESQL://user@AWS-0.POOLER.SUPABASE.COM./db")
    assert not is_supabase_pooler_url("not-a-database-url")
