#!/usr/bin/env python3
"""KRA Autoresearch — 고정 평가 하네스

이 파일은 수정 금지. train.py만 에이전트가 수정합니다.
"""

import ast

# ============================================================
# Import Guard
# ============================================================

FORBIDDEN_MODULES = {
    "db_client",
    "os",
    "pathlib",
    "subprocess",
    "shutil",
    "urllib",
    "requests",
    "httpx",
    "supabase",
}


def check_train_imports(filepath: str) -> list[str]:
    """train.py의 import문을 AST로 검사, 금지 모듈 사용 시 반환"""
    with open(filepath) as f:
        tree = ast.parse(f.read())
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name.split(".")[0]
                if mod in FORBIDDEN_MODULES:
                    violations.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mod = node.module.split(".")[0]
            if mod in FORBIDDEN_MODULES:
                violations.append(node.module)
    return violations
