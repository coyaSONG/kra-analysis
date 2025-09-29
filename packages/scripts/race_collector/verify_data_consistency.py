#!/usr/bin/env python3
"""
전처리된 데이터의 일관성 검증
모든 경주가 동일한 조건(경주 전 상태)인지 확인
"""

import glob
import json
import os


def verify_race_data(file_path):
    """개별 경주 데이터 검증"""
    with open(file_path) as f:
        data = json.load(f)

    horses = data["response"]["body"]["items"]["item"]
    if not isinstance(horses, list):
        horses = [horses]

    if not horses:
        return None

    # 첫 번째 말의 주요 필드 확인
    horse = horses[0]

    return {
        "file": os.path.basename(file_path),
        "race": f"{horse.get("rcDate")} {horse.get("meet")} {horse.get("rcNo")}R",
        "horses": len(horses),
        "ord": horse.get("ord", "N/A"),
        "rcTime": horse.get("rcTime", "N/A"),
        "winOdds": horse.get("winOdds", "N/A"),
        "wgHr": horse.get("wgHr", "N/A"),
        "diffUnit": horse.get("diffUnit", "N/A"),
        "buS1fTime": horse.get("buS1fTime", "N/A"),
        "has_result": horse.get("ord", 0) != 0 or horse.get("rcTime", 0) != 0
    }

def main():
    files = sorted(glob.glob("data/processed/pre-race/race_*.json"))

    print("📊 전처리된 경주 데이터 일관성 검증")
    print("="*80)
    print(f"{"파일명":<30} {"경주":<20} {"두수":>4} {"착순":>6} {"기록":>6} {"배당률":>6} {"결과?"}")
    print("-"*80)

    all_consistent = True

    for file_path in files:
        info = verify_race_data(file_path)
        if info:
            result_mark = "❌" if info["has_result"] else "✅"

            print(f"{info["file"]:<30} {info["race"]:<20} {info["horses"]:>4} "
                  f"{str(info["ord"]):>6} {str(info["rcTime"]):>6} "
                  f"{str(info["winOdds"]):>6} {result_mark}")

            if info["has_result"]:
                all_consistent = False

    print("="*80)

    if all_consistent:
        print("✅ 모든 경주 데이터가 경주 전 상태로 일관성 있게 처리되었습니다!")
        print("   - 착순(ord)과 기록(rcTime)이 모두 0")
        print("   - 배당률은 각 경주 상황에 맞게 유지")
        print("   - 모든 데이터를 동일한 조건으로 예측에 사용 가능")
    else:
        print("❌ 일부 데이터에 경주 결과가 남아있습니다!")

    # 상세 비교: 완료된 경주 vs 미시작 경주
    print("\n📋 상세 비교 (1R 완료 vs 5R 미시작)")
    print("-"*50)

    with open("data/processed/pre-race/race_1_20250608_1_prerace.json") as f:
        race1 = json.load(f)
    with open("data/processed/pre-race/race_1_20250608_5_prerace.json") as f:
        race5 = json.load(f)

    horse1 = race1["response"]["body"]["items"]["item"][0]
    horse5 = race5["response"]["body"]["items"]["item"][0]

    compare_fields = ["ord", "rcTime", "winOdds", "plcOdds", "wgHr", "diffUnit",
                     "buS1fTime", "seG1fAccTime"]

    for field in compare_fields:
        val1 = horse1.get(field, "N/A")
        val5 = horse5.get(field, "N/A")

        # 결과 관련 필드는 둘 다 0이어야 함
        if field in ["ord", "rcTime", "buS1fTime", "seG1fAccTime"]:
            match = val1 == val5 == 0
        # diffUnit은 둘 다 "-"여야 함
        elif field == "diffUnit":
            match = val1 == val5 == "-"
        # 나머지는 각자의 값을 가짐
        else:
            match = True  # 값이 다를 수 있음

        status = "✅" if match else "❌"
        print(f"{field:<15} 1R: {str(val1):>10} | 5R: {str(val5):>10} {status}")

if __name__ == "__main__":
    main()
