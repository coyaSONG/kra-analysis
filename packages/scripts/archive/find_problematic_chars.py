#!/usr/bin/env python3
"""
문제가 되는 특수문자 찾기
"""

import subprocess
import time


def test_special_chars():
    """특수문자별 테스트"""

    # v3.0 프롬프트에 있는 특수문자들
    special_chars = [
        ("괄호", "()"),
        ("대괄호", "[]"),
        ("중괄호", "{}"),
        ("백분율", "%"),
        ("별표", "*"),
        ("플러스", "+"),
        ("마이너스", "-"),
        ("화살표", "→"),
        ("위화살표", "↑"),
        ("콜론", ":"),
        ("세미콜론", ";"),
        (
            "따옴표",
            """),
        ("작은따옴표", """,
        ),
        ("백틱", "`"),
        ("물결", "~"),
        ("앰퍼샌드", "&"),
        ("달러", "$"),
        ("샵", "#"),
        ("백슬래시", "\\"),
        ("슬래시", "/"),
        ("물음표", "?"),
        ("느낌표", "!"),
        ("앳", "@"),
        ("캐럿", "^"),
        ("언더바", "_"),
        ("등호", "="),
        ("파이프", "|"),
        ("꺾쇠", "<>"),
    ]

    print("=== 특수문자 테스트 ===\n")

    for name, char in special_chars:
        prompt = f"테스트 {char} 포함. JSON: {{'test': 1}}"

        try:
            cmd = ["claude", "-p", prompt]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if "Execution error" in result.stdout:
                print(f"❌ {name} '{char}': Execution error")
            elif result.returncode != 0:
                print(f"❌ {name} '{char}': Return code {result.returncode}")
            else:
                print(f"✅ {name} '{char}': OK")

        except subprocess.TimeoutExpired:
            print(f"⏱️  {name} '{char}': Timeout")
        except Exception as e:
            print(f"❌ {name} '{char}': {type(e).__name__}")

        time.sleep(0.5)


def test_combinations():
    """조합 테스트"""
    print("\n\n=== 조합 테스트 ===\n")

    # v3.0에 실제로 있는 패턴들
    patterns = [
        "시장 평가(배당률): 40%",
        "**굵은글씨**: 내용",
        "### 제목",
        "- 리스트 항목",
        "1. 번호 리스트",
        "(↑15%)",
        "40% (↑15%)",
        "**시장 평가(배당률)**: 40% (↑15%)",
    ]

    for pattern in patterns:
        prompt = f"{pattern} JSON: {{'test': 1}}"

        try:
            cmd = ["claude", "-p", prompt]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if "Execution error" in result.stdout:
                print(f"❌ '{pattern[:30]}...': Execution error")
            else:
                print(f"✅ '{pattern[:30]}...': OK")

        except Exception as e:
            print(f"❌ '{pattern[:30]}...': {type(e).__name__}")

        time.sleep(0.5)


def main():
    test_special_chars()
    test_combinations()


if __name__ == "__main__":
    main()
