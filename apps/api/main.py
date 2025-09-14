"""
DEPRECATED: Use `main_v2.py` as the application entrypoint.

이 파일은 하위 호환을 위해 남겨둔 포워더입니다.
직접 사용할 경우 `main_v2:app`을 참조하세요.
"""

import warnings

# Forward import for backward compatibility (keep imports at top)
from main_v2 import app  # noqa: F401

warnings.warn(
    "apps/api/main.py 는 더 이상 사용되지 않습니다. main_v2.py를 사용하세요.",
    DeprecationWarning,
    stacklevel=2,
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main_v2:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
