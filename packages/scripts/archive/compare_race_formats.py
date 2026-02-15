#!/usr/bin/env python3
"""
경주 전/후 데이터 형식 비교 스크립트
"""

import json


def compare_race_data(file1, file2, label1="File 1", label2="File 2"):
    """두 경주 파일의 데이터 형식 비교"""

    with open(file1) as f:
        data1 = json.load(f)

    with open(file2) as f:
        data2 = json.load(f)

    # 첫 번째 말 데이터 추출
    horse1 = data1["response"]["body"]["items"]["item"]
    if isinstance(horse1, list):
        horse1 = horse1[0] if horse1 else {}

    horse2 = data2["response"]["body"]["items"]["item"]
    if isinstance(horse2, list):
        horse2 = horse2[0] if horse2 else {}

    print(f"\n{'=' * 60}")
    print("경주 데이터 형식 비교")
    print(f"{'=' * 60}")

    # 기본 정보
    print("\n📋 기본 정보")
    print(
        f"{label1}: {horse1.get('rcDate', 'N/A')} {horse1.get('meet', 'N/A')} {horse1.get('rcNo', 'N/A')}R"
    )
    print(
        f"{label2}: {horse2.get('rcDate', 'N/A')} {horse2.get('meet', 'N/A')} {horse2.get('rcNo', 'N/A')}R"
    )

    # 주요 필드 값 비교
    print("\n📊 주요 필드 값 비교")
    key_fields = ["winOdds", "plcOdds", "wgHr", "ord", "rcTime", "diffUnit"]

    print(f"{'필드명':<15} {label1:<20} {label2:<20}")
    print("-" * 55)

    for field in key_fields:
        val1 = horse1.get(field, "(없음)")
        val2 = horse2.get(field, "(없음)")

        # None 처리
        if val1 is None:
            val1 = "null"
        if val2 is None:
            val2 = "null"

        # 0 값 특별 표시
        if val1 == 0:
            val1 = "0 (미확정)"
        if val2 == 0:
            val2 = "0 (미확정)"

        print(f"{field:<15} {str(val1):<20} {str(val2):<20}")

    # 필드 존재 여부 비교
    print("\n🔍 필드 차이 분석")

    fields1 = set(horse1.keys())
    fields2 = set(horse2.keys())

    only_in_1 = fields1 - fields2
    only_in_2 = fields2 - fields1

    if only_in_1:
        print(f"\n{label1}에만 있는 필드:")
        for field in sorted(only_in_1):
            print(f"  - {field}: {horse1[field]}")

    if only_in_2:
        print(f"\n{label2}에만 있는 필드:")
        for field in sorted(only_in_2):
            print(f"  - {field}: {horse2[field]}")

    # 구간 기록 필드 확인
    print("\n⏱️ 구간 기록 필드 존재 여부")
    section_fields = ["buS1fTime", "bu_1fGTime", "seS1fTime", "se_1fGTime"]

    for field in section_fields:
        has1 = field in horse1
        has2 = field in horse2
        val1 = horse1.get(field, "-") if has1 else "없음"
        val2 = horse2.get(field, "-") if has2 else "없음"
        print(f"{field:<15} {val1:<20} {val2:<20}")

    # 배당률 0인 말들 확인
    print("\n💰 배당률 상태")

    def count_zero_odds(data):
        items = data["response"]["body"]["items"]["item"]
        if not isinstance(items, list):
            items = [items]
        return sum(1 for h in items if h.get("winOdds") == 0)

    zero1 = count_zero_odds(data1)
    zero2 = count_zero_odds(data2)

    total1 = (
        len(data1["response"]["body"]["items"]["item"])
        if isinstance(data1["response"]["body"]["items"]["item"], list)
        else 1
    )
    total2 = (
        len(data2["response"]["body"]["items"]["item"])
        if isinstance(data2["response"]["body"]["items"]["item"], list)
        else 1
    )

    print(f"{label1}: {zero1}/{total1} 말이 배당률 0")
    print(f"{label2}: {zero2}/{total2} 말이 배당률 0")


if __name__ == "__main__":
    # 실제 경주 전 데이터 vs 전처리된 경주 후 데이터
    print("\n1️⃣ 실제 경주 전(5R) vs 전처리된 경주 후(1R)")
    compare_race_data(
        "data/race_1_20250608_5.json",
        "data/processed/pre-race/race_1_20250608_1_prerace.json",
        "경주 전 (5R 원본)",
        "전처리된 (1R)",
    )

    # 경주 완료 원본 vs 전처리된 데이터
    print("\n\n2️⃣ 경주 완료 원본(1R) vs 전처리된(1R)")
    compare_race_data(
        "data/race_1_20250608_1.json",
        "data/processed/pre-race/race_1_20250608_1_prerace.json",
        "경주 후 원본 (1R)",
        "전처리된 (1R)",
    )
