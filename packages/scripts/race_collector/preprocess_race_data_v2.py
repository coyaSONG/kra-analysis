#!/usr/bin/env python3
"""
경주 데이터 전처리 스크립트 v2
- 실제 경주 전 데이터 형식과 완전히 일치하도록 수정
- 필드는 제거하지 않고 값만 초기화
"""

import copy
import json
from typing import Any


def clean_race_data_v2(race_data: dict[str, Any]) -> dict[str, Any]:
    """
    경주 데이터를 경주 전 상태로 변환 (v2)
    - 필드를 제거하지 않고 값만 초기화
    - 실제 경주 전 데이터와 동일한 형식 유지

    Args:
        race_data: API214_1에서 받은 원본 경주 데이터

    Returns:
        경주 전 상태로 정제된 데이터
    """
    # 깊은 복사로 원본 데이터 보존
    cleaned_data = copy.deepcopy(race_data)

    if 'response' in cleaned_data and 'body' in cleaned_data['response']:
        items = cleaned_data['response']['body'].get('items', {})
        if items and 'item' in items:
            horses = items['item']
            if not isinstance(horses, list):
                horses = [horses]

            # 각 말의 데이터 정제
            cleaned_horses = []
            for horse in horses:
                # 기권/제외 말 필터링 (winOdds가 명확히 0인 경우)
                win_odds = horse.get('winOdds')
                if win_odds == 0:
                    print(f"⚠️  기권/제외: {horse.get('hrName')} (출주번호: {horse.get('chulNo')})")
                    continue

                # 경주 후에만 확정되는 필드들을 0 또는 기본값으로 초기화
                # 착순 관련
                if 'ord' in horse and horse['ord'] != 0:
                    horse['ord'] = 0
                if 'ordBigo' in horse and horse['ordBigo'] != '-':
                    horse['ordBigo'] = '-'

                # 경주 기록
                if 'rcTime' in horse and horse['rcTime'] != 0:
                    horse['rcTime'] = 0

                # 착차
                if 'diffUnit' in horse and horse['diffUnit'] != '-':
                    horse['diffUnit'] = '-'

                # 모든 구간 기록을 0으로 초기화
                # 부산경남 구간
                for field in ['buS1fTime', 'buS1fAccTime', 'buS1fOrd',
                             'bu_1fGTime', 'bu_2fGTime', 'bu_3fGTime', 'bu_4fGTime',
                             'bu_4_2fTime', 'bu_6_4fTime',
                             'buG1fTime', 'buG1fAccTime', 'buG1fOrd',
                             'buG2fTime', 'buG2fAccTime', 'buG2fOrd',
                             'buG3fTime', 'buG3fAccTime', 'buG3fOrd',
                             'buG4fTime', 'buG4fAccTime', 'buG4fOrd',
                             'buG6fTime', 'buG6fAccTime', 'buG6fOrd',
                             'buG8fTime', 'buG8fAccTime', 'buG8fOrd',
                             'bu_10_8fTime', 'bu_8_6fTime']:
                    if field in horse and horse[field] != 0:
                        horse[field] = 0

                # 서울 구간
                for field in ['seS1fTime', 'seS1fAccTime', 'seS1fOrd',
                             'se_1fGTime', 'se_2fGTime', 'se_3fGTime', 'se_4fGTime',
                             'se_4_2fTime', 'se_6_4fTime',
                             'seG1fTime', 'seG1fAccTime', 'seG1fOrd',
                             'seG2fTime', 'seG2fAccTime', 'seG2fOrd',
                             'seG3fTime', 'seG3fAccTime', 'seG3fOrd',
                             'seG4fTime', 'seG4fAccTime', 'seG4fOrd',
                             'seG6fTime', 'seG6fAccTime', 'seG6fOrd',
                             'seG8fTime', 'seG8fAccTime', 'seG8fOrd',
                             'se_10_8fTime', 'se_8_6fTime']:
                    if field in horse and horse[field] != 0:
                        horse[field] = 0

                # 제주 구간
                for field in ['jeS1fTime', 'jeS1fAccTime', 'jeS1fOrd',
                             'je_1fGTime', 'je_2fGTime', 'je_3fGTime', 'je_4fGTime',
                             'je_4_2fTime', 'je_6_4fTime',
                             'jeG1fTime', 'jeG1fAccTime', 'jeG1fOrd',
                             'jeG2fTime', 'jeG2fAccTime', 'jeG2fOrd',
                             'jeG3fTime', 'jeG3fAccTime', 'jeG3fOrd']:
                    if field in horse and horse[field] != 0:
                        horse[field] = 0

                # 기타 구간 기록
                for field in ['g1fTime', 'g2fTime', 'g3fTime', 'g4fTime',
                             's1fTime', 's2fTime', 's3fTime', 's4fTime']:
                    if field in horse and horse[field] != 0:
                        horse[field] = 0

                # 배당률이 없는 경우 (아직 배당률 미확정) - 이 경우는 그대로 유지
                # winOdds와 plcOdds는 건드리지 않음

                cleaned_horses.append(horse)

            # 정제된 말 리스트로 교체
            if isinstance(items['item'], list):
                items['item'] = cleaned_horses
            else:
                # 단일 항목인 경우
                items['item'] = cleaned_horses[0] if cleaned_horses else None

            # 출전 두수 업데이트
            cleaned_data['response']['body']['totalCount'] = len(cleaned_horses)

    return cleaned_data


def process_race_file_v2(input_path: str, output_path: str) -> None:
    """
    경주 파일을 읽어서 전처리 후 저장 (v2)

    Args:
        input_path: 원본 경주 데이터 파일 경로
        output_path: 전처리된 데이터 저장 경로
    """
    print(f"\n📄 처리 중: {input_path}")

    try:
        # 원본 데이터 읽기
        with open(input_path, encoding='utf-8') as f:
            raw_data = json.load(f)

        # 데이터 정제
        cleaned_data = clean_race_data_v2(raw_data)

        # 정제된 데이터 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

        # 통계 출력
        original_count = raw_data['response']['body'].get('totalCount', 0)
        cleaned_count = cleaned_data['response']['body'].get('totalCount', 0)

        print(f"✅ 전처리 완료: {original_count}두 → {cleaned_count}두")
        if original_count > cleaned_count:
            print(f"   ({original_count - cleaned_count}두 제외: 기권/제외)")

    except Exception as e:
        print(f"❌ 처리 실패: {e}")


def validate_prerace_format(cleaned_path: str, actual_prerace_path: str) -> None:
    """
    전처리된 데이터와 실제 경주 전 데이터 형식 검증

    Args:
        cleaned_path: 전처리된 데이터 경로
        actual_prerace_path: 실제 경주 전 데이터 경로
    """
    with open(cleaned_path) as f:
        cleaned = json.load(f)

    with open(actual_prerace_path) as f:
        actual = json.load(f)

    print("\n🔍 형식 검증")
    print("="*50)

    # 첫 번째 말로 비교
    if cleaned['response']['body']['items'] and actual['response']['body']['items']:
        cleaned_horse = cleaned['response']['body']['items']['item']
        actual_horse = actual['response']['body']['items']['item']

        if isinstance(cleaned_horse, list):
            cleaned_horse = cleaned_horse[0]
        if isinstance(actual_horse, list):
            actual_horse = actual_horse[0]

        # 주요 필드 비교
        key_fields = ['ord', 'rcTime', 'winOdds', 'plcOdds', 'wgHr', 'diffUnit',
                     'buS1fTime', 'seG1fAccTime']

        all_match = True
        for field in key_fields:
            cleaned_val = cleaned_horse.get(field, '없음')
            actual_val = actual_horse.get(field, '없음')

            match = cleaned_val == actual_val
            status = "✅" if match else "❌"

            if not match:
                all_match = False
                print(f"{status} {field}: 전처리={cleaned_val}, 실제={actual_val}")

        if all_match:
            print("✅ 모든 주요 필드가 일치합니다!")

        # 필드 개수 비교
        print(f"\n필드 개수: 전처리={len(cleaned_horse.keys())}, 실제={len(actual_horse.keys())}")


if __name__ == "__main__":
    import os
    import sys

    if len(sys.argv) < 2:
        print("사용법: python preprocess_race_data_v2.py <input_file> [output_file]")
        sys.exit(1)

    input_file = sys.argv[1]

    # 출력 파일명 생성
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        # 기본값: 같은 디렉토리에 _prerace 접미사 추가
        base_name = os.path.basename(input_file).replace('.json', '')
        dir_name = os.path.dirname(input_file)
        output_file = os.path.join(dir_name, 'processed', 'pre-race', f"{base_name}_prerace_v2.json")

    # 출력 디렉토리 생성
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # 전처리 실행
    process_race_file_v2(input_file, output_file)

    # 형식 검증 (5R과 비교)
    if os.path.exists("data/race_1_20250608_5.json"):
        print("\n실제 경주 전 데이터(5R)와 형식 비교:")
        validate_prerace_format(output_file, "data/race_1_20250608_5.json")
