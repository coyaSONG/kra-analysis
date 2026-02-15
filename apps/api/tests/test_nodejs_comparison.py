"""
Node.js 스크립트와 Python API 비교 테스트

이 테스트는 Node.js 스크립트가 수집한 데이터와
Python API가 수집한 데이터를 비교하여 일치성을 검증합니다.
"""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import httpx

# API 경로를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 환경변수는 .env 파일에서 로드됨
from infrastructure.kra_api.client import KRAApiClient


class NodeJsPythonComparison:
    def __init__(self):
        self.nodejs_scripts_path = Path("../scripts/race_collector")
        self.data_path = Path("../data")
        self.api_client = KRAApiClient()
        self.api_base_url = "http://localhost:8000/api/v1"

    async def run_nodejs_script(
        self, script_name: str, args: list[str]
    ) -> dict[str, Any]:
        """Node.js 스크립트를 실행하고 결과를 반환합니다."""
        try:
            script_path = self.nodejs_scripts_path / script_name
            cmd = ["node", str(script_path)] + args

            print(f"실행 중: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, cwd="..")

            if result.returncode != 0:
                print(f"Node.js 스크립트 오류: {result.stderr}")
                return {"error": result.stderr}

            print(f"Node.js 출력: {result.stdout}")
            return {"success": True, "output": result.stdout}

        except Exception as e:
            print(f"Node.js 스크립트 실행 실패: {e}")
            return {"error": str(e)}

    def load_nodejs_race_data(
        self, date: str, meet: int, race_no: int, file_type: str = "prerace"
    ) -> dict[str, Any] | None:
        """Node.js가 생성한 파일에서 데이터를 읽습니다."""
        try:
            # Node.js 파일 경로 구성
            year = date[:4]
            month = date[4:6]
            meet_folders = {"1": "seoul", "2": "jeju", "3": "busan"}
            meet_folder = meet_folders.get(str(meet), f"meet_{meet}")

            file_path = (
                self.data_path
                / "races"
                / year
                / month
                / date
                / meet_folder
                / f"race_{meet}_{date}_{race_no}_{file_type}.json"
            )

            if not file_path.exists():
                print(f"Node.js 파일을 찾을 수 없음: {file_path}")
                return None

            with open(file_path, encoding="utf-8") as f:
                return json.load(f)

        except Exception as e:
            print(f"Node.js 파일 읽기 실패: {e}")
            return None

    async def test_race_detail_collection(
        self, date: str = "20250106", meet: int = 1, race_no: int = 1
    ):
        """경주 상세 데이터 수집을 비교 테스트합니다."""
        print(f"\n{'=' * 60}")
        print("경주 상세 데이터 수집 테스트")
        print(f"날짜: {date}, 경마장: {meet}, 경주: {race_no}")
        print(f"{'=' * 60}\n")

        # 1. Node.js로 데이터 수집
        print("1. Node.js 스크립트 실행...")
        await self.run_nodejs_script("collect_and_preprocess.js", [date, str(meet)])

        # 2. Node.js 파일 읽기
        print("\n2. Node.js 결과 파일 읽기...")
        nodejs_data = self.load_nodejs_race_data(date, meet, race_no)

        if not nodejs_data:
            print("Node.js 데이터를 찾을 수 없습니다.")
            return

        # 3. Python API로 데이터 수집
        print("\n3. Python API로 데이터 수집...")
        python_data = await self.api_client.get_race_detail(date, meet, race_no)

        if not python_data:
            print("Python API 데이터를 가져올 수 없습니다.")
            return

        # 4. 데이터 비교
        print("\n4. 데이터 비교 분석...")
        self.compare_race_data(nodejs_data, python_data)

    def compare_race_data(
        self, nodejs_data: dict[str, Any], python_data: dict[str, Any]
    ):
        """Node.js와 Python 데이터를 비교합니다."""
        print("\n[기본 정보 비교]")

        # 경주 정보 비교
        fields_to_compare = [
            "date",
            "meet",
            "race_no",
            "race_name",
            "distance",
            "track_condition",
            "weather",
        ]

        for field in fields_to_compare:
            nodejs_val = nodejs_data.get(field)
            python_val = python_data.get(field)
            match = "✅" if nodejs_val == python_val else "❌"
            print(f"{field}: {match}")
            if nodejs_val != python_val:
                print(f"  Node.js: {nodejs_val}")
                print(f"  Python: {python_val}")

        # 말 정보 비교
        print("\n[말 정보 비교]")
        nodejs_horses = nodejs_data.get("horses", [])
        python_horses = python_data.get("horses", [])

        print(f"말 수: Node.js={len(nodejs_horses)}, Python={len(python_horses)}")

        if len(nodejs_horses) == len(python_horses):
            print("✅ 말 수 일치")

            # 첫 번째 말 상세 비교
            if nodejs_horses and python_horses:
                print("\n[첫 번째 말 상세 비교]")
                horse_fields = [
                    "chul_no",
                    "horse_no",
                    "horse_name",
                    "jockey_name",
                    "trainer_name",
                    "win_odds",
                ]

                for field in horse_fields:
                    nodejs_val = nodejs_horses[0].get(field)
                    python_val = python_horses[0].get(field)
                    match = "✅" if nodejs_val == python_val else "❌"
                    print(f"{field}: {match}")
                    if nodejs_val != python_val:
                        print(f"  Node.js: {nodejs_val}")
                        print(f"  Python: {python_val}")
        else:
            print("❌ 말 수 불일치")

    async def test_api_endpoints(self):
        """FastAPI 엔드포인트를 테스트합니다."""
        print(f"\n{'=' * 60}")
        print("FastAPI 엔드포인트 테스트")
        print(f"{'=' * 60}\n")

        async with httpx.AsyncClient() as client:
            # 1. 헬스체크
            print("1. 헬스체크...")
            response = await client.get(
                f"{self.api_base_url.replace('/api/v1', '')}/health"
            )
            print(f"상태: {response.status_code}")
            print(f"응답: {response.json()}")

            # 2. 경주 수집 요청
            print("\n2. 경주 수집 요청...")
            collect_data = {"date": "20250106", "meet": 1, "race_no": 1}
            response = await client.post(
                f"{self.api_base_url}/races/collect", json=collect_data
            )
            print(f"상태: {response.status_code}")
            result = response.json()
            print(f"응답: {result}")

            if response.status_code == 200:
                job_id = result.get("job_id")

                # 3. 수집 상태 확인
                await asyncio.sleep(3)  # 수집 대기
                print("\n3. 수집 상태 확인...")
                response = await client.get(
                    f"{self.api_base_url}/races/{job_id}/status"
                )
                print(f"상태: {response.status_code}")
                print(f"응답: {response.json()}")

    async def test_enrichment_comparison(
        self, date: str = "20250106", meet: int = 1, race_no: int = 1
    ):
        """데이터 보강(enrichment) 비교 테스트입니다."""
        print(f"\n{'=' * 60}")
        print("데이터 보강(Enrichment) 비교 테스트")
        print(f"날짜: {date}, 경마장: {meet}, 경주: {race_no}")
        print(f"{'=' * 60}\n")

        # 1. Node.js enrichment 실행
        print("1. Node.js enrichment 실행...")
        await self.run_nodejs_script("enrich_race_data.js", [date, str(meet)])

        # 2. Node.js enriched 파일 읽기
        print("\n2. Node.js enriched 결과 읽기...")
        nodejs_enriched = self.load_nodejs_race_data(date, meet, race_no, "enriched")

        if nodejs_enriched:
            horses = nodejs_enriched.get("horses", [])
            if horses:
                first_horse = horses[0]
                print("\nNode.js enriched 데이터 예시 (첫 번째 말):")
                print(f"- 말 이름: {first_horse.get('horse_name')}")
                print(f"- 말 상세 정보 포함: {'horse_detail' in first_horse}")
                print(f"- 기수 상세 정보 포함: {'jockey_detail' in first_horse}")
                print(f"- 조교사 상세 정보 포함: {'trainer_detail' in first_horse}")


async def main():
    """메인 테스트 실행 함수"""
    tester = NodeJsPythonComparison()

    print("KRA API Node.js vs Python 비교 테스트")
    print("=" * 60)

    # 테스트할 경주 정보
    test_date = "20250106"  # 오늘 날짜 또는 원하는 날짜
    test_meet = 1  # 서울
    test_race_no = 1

    try:
        # 1. 경주 상세 데이터 수집 비교
        await tester.test_race_detail_collection(test_date, test_meet, test_race_no)

        # 2. API 엔드포인트 테스트 (서버가 실행 중인 경우)
        print("\n\nAPI 서버 테스트를 실행하시겠습니까? (서버가 실행 중이어야 함)")
        print("실행하려면 Enter, 건너뛰려면 'n' 입력: ", end="")
        user_input = input().strip().lower()

        if user_input != "n":
            await tester.test_api_endpoints()

        # 3. Enrichment 비교 테스트
        print("\n\nEnrichment 비교 테스트를 실행하시겠습니까? (시간이 걸립니다)")
        print("실행하려면 Enter, 건너뛰려면 'n' 입력: ", end="")
        user_input = input().strip().lower()

        if user_input != "n":
            await tester.test_enrichment_comparison(test_date, test_meet, test_race_no)

        print("\n\n테스트 완료!")

    except Exception as e:
        print(f"\n테스트 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
