"""
데이터 검증 테스트

Python API가 수집한 데이터의 정확성을 검증합니다.
"""

import asyncio
import json
from typing import Dict, Any, List
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 환경변수는 .env 파일에서 로드됨

from infrastructure.kra_api.client import KRAApiClient


class DataValidator:
    def __init__(self):
        self.api_client = KRAApiClient()
        self.validation_results = []
    
    def validate_race_data(self, race_data: Dict[str, Any]) -> Dict[str, Any]:
        """경주 데이터의 유효성을 검증합니다."""
        errors = []
        warnings = []
        
        # 필수 필드 검증
        required_fields = ["date", "meet", "race_no", "horses"]
        for field in required_fields:
            if field not in race_data or race_data[field] is None:
                errors.append(f"필수 필드 누락: {field}")
        
        # 날짜 형식 검증
        if "date" in race_data:
            date_str = race_data["date"]
            if not (len(date_str) == 8 and date_str.isdigit()):
                errors.append(f"잘못된 날짜 형식: {date_str} (YYYYMMDD 형식이어야 함)")
        
        # 경마장 코드 검증
        if "meet" in race_data:
            meet = race_data["meet"]
            if meet not in [1, 2, 3]:
                errors.append(f"잘못된 경마장 코드: {meet} (1:서울, 2:제주, 3:부산경남)")
        
        # 말 정보 검증
        horses = race_data.get("horses", [])
        if not horses:
            errors.append("말 정보가 없습니다")
        else:
            for idx, horse in enumerate(horses):
                horse_errors = self.validate_horse_data(horse, idx + 1)
                errors.extend(horse_errors)
        
        # 경고 사항 검증
        if len(horses) < 5:
            warnings.append(f"말 수가 적습니다: {len(horses)}마리")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "horse_count": len(horses)
        }
    
    def validate_horse_data(self, horse: Dict[str, Any], position: int) -> List[str]:
        """개별 말 데이터를 검증합니다."""
        errors = []
        prefix = f"말 #{position}"
        
        # 필수 필드
        required_fields = ["chul_no", "horse_no", "horse_name"]
        for field in required_fields:
            if field not in horse or not horse[field]:
                errors.append(f"{prefix}: 필수 필드 누락 - {field}")
        
        # 출전번호 검증
        if "chul_no" in horse:
            chul_no = horse["chul_no"]
            if not isinstance(chul_no, (int, str)) or int(chul_no) < 1 or int(chul_no) > 20:
                errors.append(f"{prefix}: 잘못된 출전번호 - {chul_no}")
        
        # 배당률 검증
        if "win_odds" in horse:
            win_odds = horse["win_odds"]
            if win_odds == 0:
                errors.append(f"{prefix}: 배당률이 0입니다 (기권/제외마 가능성)")
            elif win_odds < 0:
                errors.append(f"{prefix}: 음수 배당률 - {win_odds}")
        
        # 체중 검증
        if "weight" in horse and horse["weight"]:
            try:
                weight = float(str(horse["weight"]).replace("kg", ""))
                if weight < 300 or weight > 700:
                    errors.append(f"{prefix}: 비정상적인 체중 - {weight}kg")
            except:
                pass
        
        return errors
    
    async def test_multiple_races(self, date: str, meet: int, race_count: int = 5):
        """여러 경주의 데이터를 검증합니다."""
        print(f"\n{'='*60}")
        print(f"다중 경주 데이터 검증 테스트")
        print(f"날짜: {date}, 경마장: {meet}, 경주 수: {race_count}")
        print(f"{'='*60}\n")
        
        all_valid = True
        total_horses = 0
        
        for race_no in range(1, race_count + 1):
            print(f"\n[경주 {race_no}]")
            
            try:
                # 데이터 수집
                race_data = await self.api_client.get_race_detail(date, meet, race_no)
                
                if not race_data:
                    print(f"❌ 데이터 수집 실패")
                    all_valid = False
                    continue
                
                # 데이터 검증
                validation = self.validate_race_data(race_data)
                total_horses += validation["horse_count"]
                
                if validation["valid"]:
                    print(f"✅ 유효한 데이터 (말 {validation['horse_count']}마리)")
                else:
                    print(f"❌ 유효하지 않은 데이터")
                    all_valid = False
                    for error in validation["errors"]:
                        print(f"   - {error}")
                
                if validation["warnings"]:
                    for warning in validation["warnings"]:
                        print(f"   ⚠️  {warning}")
                
                # API 호출 제한 방지
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"❌ 오류 발생: {e}")
                all_valid = False
        
        print(f"\n{'='*60}")
        print(f"검증 결과 요약")
        print(f"{'='*60}")
        print(f"전체 결과: {'✅ 모두 유효' if all_valid else '❌ 일부 오류 발생'}")
        print(f"총 말 수: {total_horses}마리")
    
    async def test_api_consistency(self, date: str, meet: int, race_no: int):
        """동일한 API를 여러 번 호출하여 일관성을 검증합니다."""
        print(f"\n{'='*60}")
        print(f"API 일관성 테스트")
        print(f"날짜: {date}, 경마장: {meet}, 경주: {race_no}")
        print(f"{'='*60}\n")
        
        results = []
        
        print("동일한 경주를 3번 조회합니다...")
        for i in range(3):
            print(f"\n[시도 {i+1}]")
            data = await self.api_client.get_race_detail(date, meet, race_no)
            
            if data:
                horse_count = len(data.get("horses", []))
                print(f"✅ 성공 - 말 {horse_count}마리")
                results.append({
                    "success": True,
                    "horse_count": horse_count,
                    "race_name": data.get("race_name"),
                    "distance": data.get("distance")
                })
            else:
                print(f"❌ 실패")
                results.append({"success": False})
            
            await asyncio.sleep(1)
        
        # 일관성 검증
        print(f"\n[일관성 검증]")
        if all(r["success"] for r in results):
            horse_counts = [r["horse_count"] for r in results]
            race_names = [r["race_name"] for r in results]
            distances = [r["distance"] for r in results]
            
            if len(set(horse_counts)) == 1:
                print(f"✅ 말 수 일치: {horse_counts[0]}마리")
            else:
                print(f"❌ 말 수 불일치: {horse_counts}")
            
            if len(set(race_names)) == 1:
                print(f"✅ 경주명 일치: {race_names[0]}")
            else:
                print(f"❌ 경주명 불일치")
            
            if len(set(distances)) == 1:
                print(f"✅ 거리 일치: {distances[0]}m")
            else:
                print(f"❌ 거리 불일치")
        else:
            print("❌ 일부 요청이 실패하여 일관성을 검증할 수 없습니다")
    
    async def test_special_cases(self):
        """특수한 경우를 테스트합니다."""
        print(f"\n{'='*60}")
        print(f"특수 케이스 테스트")
        print(f"{'='*60}\n")
        
        # 1. 존재하지 않는 날짜
        print("[1. 미래 날짜 테스트]")
        future_date = "20251231"
        data = await self.api_client.get_race_detail(future_date, 1, 1)
        if data is None:
            print("✅ 정상 - 미래 날짜는 데이터가 없음")
        else:
            print("❌ 오류 - 미래 날짜에 데이터가 있음")
        
        # 2. 잘못된 경마장 코드
        print("\n[2. 잘못된 경마장 코드]")
        try:
            data = await self.api_client.get_race_detail("20250106", 99, 1)
            if data is None:
                print("✅ 정상 - 잘못된 경마장 코드 처리")
            else:
                print("❌ 오류 - 잘못된 경마장에 데이터가 있음")
        except Exception as e:
            print(f"✅ 정상 - 예외 발생: {type(e).__name__}")
        
        # 3. 큰 경주 번호
        print("\n[3. 큰 경주 번호 테스트]")
        data = await self.api_client.get_race_detail("20250106", 1, 99)
        if data is None:
            print("✅ 정상 - 존재하지 않는 경주 번호")
        else:
            print("❌ 오류 - 99번 경주에 데이터가 있음")


async def main():
    """메인 테스트 실행 함수"""
    validator = DataValidator()
    
    print("Python API 데이터 검증 테스트")
    print("="*60)
    
    # 테스트 설정
    test_date = "20241229"  # 테스트할 날짜 (Node.js에서 확인된 날짜)
    test_meet = 1  # 서울
    
    try:
        # 1. 다중 경주 검증
        await validator.test_multiple_races(test_date, test_meet, 3)
        
        # 2. API 일관성 테스트
        await validator.test_api_consistency(test_date, test_meet, 1)
        
        # 3. 특수 케이스 테스트
        await validator.test_special_cases()
        
        print("\n\n모든 테스트 완료!")
        
    except Exception as e:
        print(f"\n테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())