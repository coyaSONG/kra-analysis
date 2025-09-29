#!/usr/bin/env python3
"""
경주 데이터 전처리 스크립트
- 경주 결과가 포함된 데이터를 경주 전 상태로 변환
- 예측에 영향을 줄 수 있는 모든 사후 정보 제거
"""

import copy
import json
from typing import Any

# 경주 후에만 알 수 있는 필드들 (제거 대상)
POST_RACE_FIELDS = [
    # 결과 관련
    "ord",  # 착순
    "ordBigo",  # 착순 비고
    "rcTime",  # 경주 기록
    "diffUnit",  # 착차
    # 구간 기록 (모든 경마장)
    "g1fTime",
    "g2fTime",
    "g3fTime",
    "g4fTime",
    "s1fTime",
    "s2fTime",
    "s3fTime",
    "s4fTime",
    "buS1fTime",
    "buS1fAccTime",
    "buS1fOrd",
    "bu_1fGTime",
    "bu_2fGTime",
    "bu_3fGTime",
    "bu_4fGTime",
    "bu_4_2fTime",
    "bu_6_4fTime",
    "buG1fTime",
    "buG1fAccTime",
    "buG1fOrd",
    "buG2fTime",
    "buG2fAccTime",
    "buG2fOrd",
    "buG3fTime",
    "buG3fAccTime",
    "buG3fOrd",
    # 서울 구간 기록
    "seS1fTime",
    "seS1fAccTime",
    "seS1fOrd",
    "se_1fGTime",
    "se_2fGTime",
    "se_3fGTime",
    "se_4fGTime",
    "se_4_2fTime",
    "se_6_4fTime",
    "seG1fTime",
    "seG1fAccTime",
    "seG1fOrd",
    "seG2fTime",
    "seG2fAccTime",
    "seG2fOrd",
    "seG3fTime",
    "seG3fAccTime",
    "seG3fOrd",
    # 제주 구간 기록
    "jeS1fTime",
    "jeS1fAccTime",
    "jeS1fOrd",
    "je_1fGTime",
    "je_2fGTime",
    "je_3fGTime",
    "je_4fGTime",
    "je_4_2fTime",
    "je_6_4fTime",
    "jeG1fTime",
    "jeG1fAccTime",
    "jeG1fOrd",
    "jeG2fTime",
    "jeG2fAccTime",
    "jeG2fOrd",
    "jeG3fTime",
    "jeG3fAccTime",
    "jeG3fOrd",
    # 실제 마체중은 경주 전에도 공개되므로 유지
    # "wgHr",  # 마체중(+변화량)은 경주 전에도 공개됨
]

# 배당률이 0인 경우 제거해야 할 필드들
SCRATCH_FIELDS = [
    "winOdds",  # 단승 배당률
    "plcOdds",  # 복승 배당률
]


def clean_race_data(race_data: dict[str, Any]) -> dict[str, Any]:
    """
    경주 데이터에서 사후 정보를 제거하여 경주 전 상태로 변환

    Args:
        race_data: API214_1에서 받은 원본 경주 데이터

    Returns:
        경주 전 상태로 정제된 데이터
    """
    # 깊은 복사로 원본 데이터 보존
    cleaned_data = copy.deepcopy(race_data)

    if "response" in cleaned_data and "body" in cleaned_data["response"]:
        items = cleaned_data["response"]["body"].get("items", {})
        if items and "item" in items:
            horses = items["item"]
            if not isinstance(horses, list):
                horses = [horses]

            # 각 말의 데이터 정제
            cleaned_horses = []
            for horse in horses:
                # 기권/제외 말 필터링 (winOdds가 명확히 0인 경우)
                # 배당률이 없거나 빈 문자열인 경우는 아직 확정되지 않은 것으로 처리
                win_odds = horse.get("winOdds")
                if win_odds == 0:  # 명확히 0인 경우만 기권/제외
                    print(
                        f"⚠️  기권/제외: {horse.get("hrName")} (출주번호: {horse.get("chulNo")})"
                    )
                    continue

                # 사후 정보 필드 제거
                for field in POST_RACE_FIELDS:
                    if field in horse:
                        del horse[field]

                # 배당률이 없는 경우 (아직 배당률 미확정)
                if "winOdds" not in horse or horse.get("winOdds") == "":
                    horse["winOdds"] = None
                    horse["plcOdds"] = None

                cleaned_horses.append(horse)

            # 정제된 말 리스트로 교체
            if isinstance(items["item"], list):
                items["item"] = cleaned_horses
            else:
                # 단일 항목인 경우
                items["item"] = cleaned_horses[0] if cleaned_horses else None

            # 출전 두수 업데이트
            cleaned_data["response"]["body"]["totalCount"] = len(cleaned_horses)

    return cleaned_data


def process_race_file(input_path: str, output_path: str) -> None:
    """
    경주 파일을 읽어서 전처리 후 저장

    Args:
        input_path: 원본 경주 데이터 파일 경로
        output_path: 전처리된 데이터 저장 경로
    """
    print(f"\n📄 처리 중: {input_path}")

    try:
        # 원본 데이터 읽기
        with open(input_path, encoding="utf-8") as f:
            raw_data = json.load(f)

        # 데이터 정제
        cleaned_data = clean_race_data(raw_data)

        # 정제된 데이터 저장
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

        # 통계 출력
        original_count = raw_data["response"]["body"].get("totalCount", 0)
        cleaned_count = cleaned_data["response"]["body"].get("totalCount", 0)

        print(f"✅ 전처리 완료: {original_count}두 → {cleaned_count}두")
        if original_count > cleaned_count:
            print(f"   ({original_count - cleaned_count}두 제외: 기권/제외)")

    except Exception as e:
        print(f"❌ 처리 실패: {e}")


def compare_before_after(original_path: str, cleaned_path: str) -> None:
    """
    원본과 전처리된 데이터 비교

    Args:
        original_path: 원본 데이터 경로
        cleaned_path: 전처리된 데이터 경로
    """
    with open(original_path, encoding="utf-8") as f:
        original = json.load(f)

    with open(cleaned_path, encoding="utf-8") as f:
        cleaned = json.load(f)

    print("\n📊 전처리 전후 비교")
    print("=" * 60)

    # 첫 번째 말 데이터로 비교
    if original["response"]["body"]["items"] and cleaned["response"]["body"]["items"]:
        orig_items = original["response"]["body"]["items"].get("item")
        clean_items = cleaned["response"]["body"]["items"].get("item")

        if not orig_items or not clean_items:
            print("데이터가 없습니다.")
            return

        orig_horse = orig_items[0] if isinstance(orig_items, list) else orig_items
        clean_horse = clean_items[0] if isinstance(clean_items, list) else clean_items

        print(f"말 이름: {orig_horse.get("hrName")}")
        print(f"출주번호: {orig_horse.get("chulNo")}")
        print("\n제거된 필드:")

        removed_fields = []
        for field in POST_RACE_FIELDS:
            if field in orig_horse and field not in clean_horse:
                removed_fields.append(f"  - {field}: {orig_horse[field]}")

        if removed_fields:
            for field in removed_fields[:10]:  # 처음 10개만 표시
                print(field)
            if len(removed_fields) > 10:
                print(f"  ... 외 {len(removed_fields) - 10}개 필드")
        else:
            print("  (제거된 필드 없음 - 경주 전 데이터)")


if __name__ == "__main__":
    import os
    import sys

    if len(sys.argv) < 2:
        print("사용법: python preprocess_race_data.py <input_file> [output_file]")
        print("예시: python preprocess_race_data.py data/race_1_20250608_1.json")
        sys.exit(1)

    input_file = sys.argv[1]

    # 출력 파일명 생성
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        # 기본값: 같은 디렉토리에 _prerace 접미사 추가
        base_name = os.path.basename(input_file).replace(".json", "")
        dir_name = os.path.dirname(input_file)
        output_file = os.path.join(
            dir_name, "processed", "pre-race", f"{base_name}_prerace.json"
        )

    # 출력 디렉토리 생성
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # 전처리 실행
    process_race_file(input_file, output_file)

    # 전후 비교
    if os.path.exists(output_file):
        compare_before_after(input_file, output_file)
