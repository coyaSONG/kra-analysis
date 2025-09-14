#!/usr/bin/env python3
"""
성공한 경주와 실패한 경주 데이터 비교 분석
"""

import json
from pathlib import Path


def analyze_race_data(race_id, status):
    """경주 데이터 분석"""
    race_files = list(Path("data/raw/results/2025").glob(f"*/{race_id}.json"))
    if not race_files:
        print(f"{race_id}: 파일 없음")
        return None

    with open(race_files[0], encoding='utf-8') as f:
        data = json.load(f)

    analysis = {
        "race_id": race_id,
        "status": status,
        "horses_count": len(data["horses"]),
        "special_cases": []
    }

    # 특수 케이스 확인
    for horse in data["horses"]:
        # 1. 특수문자 포함된 말 이름
        hr_name = horse["hr_name"]
        special_chars = ['(', ')', '[', ']', '{', '}', '"', "'", '\\', '/', '|', '&', '$', '#', '%', '!', '?', '*', '+', '=', '<', '>', '^', '~', '`']
        if any(char in hr_name for char in special_chars):
            analysis["special_cases"].append(f"특수문자 이름: {horse['chul_no']}번 {hr_name}")

        # 2. 매우 긴 이름
        if len(hr_name) > 15:
            analysis["special_cases"].append(f"긴 이름: {horse['chul_no']}번 {hr_name} (길이: {len(hr_name)})")

        # 3. 영어/숫자 포함
        if any(char.isascii() and not char.isspace() for char in hr_name):
            analysis["special_cases"].append(f"영어/숫자: {horse['chul_no']}번 {hr_name}")

        # 4. 기수/조교사 이름 특수문자
        jk_name = horse["jockey"]["jk_name"]
        tr_name = horse["trainer"]["tr_name"]
        if any(char in jk_name for char in special_chars):
            analysis["special_cases"].append(f"기수 특수문자: {jk_name}")
        if any(char in tr_name for char in special_chars):
            analysis["special_cases"].append(f"조교사 특수문자: {tr_name}")

        # 5. 체중 형식 이상
        weight = horse.get("weight", "")
        if weight and not weight[-1].isdigit() and weight[-1] != ')':
            analysis["special_cases"].append(f"체중 형식: {horse['chul_no']}번 {weight}")

        # 6. 배당률 특이값
        win_odds = horse.get("win_odds", 999)
        if win_odds == 0 or win_odds > 100:
            analysis["special_cases"].append(f"배당률 특이: {horse['chul_no']}번 {win_odds}")

        # 7. 누락된 필드
        required_fields = ["hr_name", "jockey", "trainer", "chul_no"]
        for field in required_fields:
            if field not in horse:
                analysis["special_cases"].append(f"필드 누락: {horse.get('chul_no', '?')}번 {field} 없음")

    return analysis


def main():
    # 테스트 케이스들
    test_cases = [
        # 성공 케이스
        ("race_1_20250511_3", "성공-완전적중"),
        ("race_1_20250511_5", "성공-1마리"),
        ("race_1_20250531_8", "성공-2마리"),
        ("race_3_20250504_6", "성공-2마리"),

        # 실패 케이스
        ("race_1_20250524_7", "실패-파싱오류"),
        ("race_1_20250517_10", "실패-Execution"),
        ("race_1_20250531_3", "실패-Execution"),
        ("race_3_20250606_6", "실패-파싱오류"),
        ("race_1_20250503_3", "실패-파싱오류"),
    ]

    print("=== 성공/실패 경주 데이터 비교 분석 ===\n")

    results = []
    for race_id, status in test_cases:
        analysis = analyze_race_data(race_id, status)
        if analysis:
            results.append(analysis)
            print(f"\n{race_id} ({status})")
            print(f"말 수: {analysis['horses_count']}")
            if analysis['special_cases']:
                print("특수 케이스:")
                for case in analysis['special_cases'][:5]:  # 최대 5개만
                    print(f"  - {case}")
            else:
                print("특수 케이스: 없음")

    # 패턴 분석
    print("\n\n=== 패턴 분석 ===")

    success_cases = [r for r in results if "성공" in r["status"]]
    fail_cases = [r for r in results if "실패" in r["status"]]

    print("\n성공 케이스 특징:")
    success_special_count = sum(len(r["special_cases"]) for r in success_cases)
    print(f"- 평균 특수 케이스: {success_special_count/len(success_cases):.1f}개")

    print("\n실패 케이스 특징:")
    fail_special_count = sum(len(r["special_cases"]) for r in fail_cases)
    print(f"- 평균 특수 케이스: {fail_special_count/len(fail_cases):.1f}개")

    # 실패 케이스의 공통 패턴 찾기
    fail_patterns = {}
    for result in fail_cases:
        for case in result["special_cases"]:
            pattern_type = case.split(":")[0]
            fail_patterns[pattern_type] = fail_patterns.get(pattern_type, 0) + 1

    print("\n실패 케이스의 특수 패턴 빈도:")
    for pattern, count in sorted(fail_patterns.items(), key=lambda x: x[1], reverse=True):
        print(f"- {pattern}: {count}회")


if __name__ == "__main__":
    main()
