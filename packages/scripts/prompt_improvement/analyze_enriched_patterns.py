#!/usr/bin/env python3
"""
Enriched 데이터 패턴 분석 도구
- 배당률 순위와 실제 순위의 상관관계
- 기수/말 성적과 실제 순위의 상관관계
- 성공/실패 말들의 특성 분석
"""

import glob
import json
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path


class EnrichedDataAnalyzer:
    def __init__(self):
        self.stats = {
            "total_races": 0,
            "total_horses": 0,
            "valid_horses": 0,
            "odds_rank_distribution": defaultdict(lambda: {"total": 0, "top3": 0}),
            "jockey_win_rate_bins": defaultdict(lambda: {"total": 0, "top3": 0}),
            "horse_place_rate_bins": defaultdict(lambda: {"total": 0, "top3": 0}),
            "weight_change_impact": defaultdict(list),
            "data_availability": defaultdict(int),
            "success_patterns": [],
            "failure_patterns": []
        }

    def load_race_with_result(self, enriched_file: str) -> tuple[dict | None, list[int] | None]:
        """enriched 파일과 대응하는 결과 로드"""
        try:
            # enriched 파일에서 정보 추출
            path_parts = Path(enriched_file).parts
            date = path_parts[-4]  # 20250601
            venue = path_parts[-2]  # seoul, busan, jeju
            filename = path_parts[-1]  # race_1_20250601_1_enriched.json

            # 경주 번호 추출
            race_no = filename.split("_")[3]

            # 결과 파일 경로
            venue_map = {"seoul": "서울", "busan": "부산경남", "jeju": "제주"}
            result_file = f"data/cache/results/top3_{date}_{venue_map.get(venue, venue)}_{race_no}.json"

            # enriched 데이터 로드
            with open(enriched_file, encoding="utf-8") as f:
                race_data = json.load(f)

            # 결과 로드
            result = []
            if Path(result_file).exists():
                with open(result_file, encoding="utf-8") as f:
                    result = json.load(f)

            return race_data, result

        except Exception as e:
            print(f"Error loading {enriched_file}: {e}")
            return None, None

    def analyze_horse(self, horse: dict, is_winner: bool, odds_rank: int):
        """개별 말 분석"""
        # 배당률 순위별 분포
        self.stats["odds_rank_distribution"][odds_rank]["total"] += 1
        if is_winner:
            self.stats["odds_rank_distribution"][odds_rank]["top3"] += 1

        # 기수 승률 분석
        if "jkDetail" in horse and horse["jkDetail"]:
            jk = horse["jkDetail"]
            if jk.get("rcCntT", 0) > 0:
                win_rate = (jk.get("ord1CntT", 0) / jk["rcCntT"]) * 100
                win_rate_bin = int(win_rate / 5) * 5  # 5% 단위로 그룹화

                self.stats["jockey_win_rate_bins"][win_rate_bin]["total"] += 1
                if is_winner:
                    self.stats["jockey_win_rate_bins"][win_rate_bin]["top3"] += 1

        # 말 입상률 분석
        if "hrDetail" in horse and horse["hrDetail"]:
            hr = horse["hrDetail"]
            if hr.get("rcCntT", 0) > 0:
                place_rate = ((hr.get("ord1CntT", 0) + hr.get("ord2CntT", 0) +
                              hr.get("ord3CntT", 0)) / hr["rcCntT"]) * 100
                place_rate_bin = int(place_rate / 10) * 10  # 10% 단위로 그룹화

                self.stats["horse_place_rate_bins"][place_rate_bin]["total"] += 1
                if is_winner:
                    self.stats["horse_place_rate_bins"][place_rate_bin]["top3"] += 1

        # 부담중량 변화 분석
        if "budam" in horse and "buga1" in horse:
            weight_change = horse["budam"] - horse.get("buga1", horse["budam"])
            if is_winner:
                self.stats["weight_change_impact"]["winner"].append(weight_change)
            else:
                self.stats["weight_change_impact"]["loser"].append(weight_change)

        # 데이터 가용성
        if "hrDetail" in horse:
            self.stats["data_availability"]["has_hr_detail"] += 1
        if "jkDetail" in horse:
            self.stats["data_availability"]["has_jk_detail"] += 1
        if "trDetail" in horse:
            self.stats["data_availability"]["has_tr_detail"] += 1

    def analyze_all_races(self):
        """모든 경주 분석"""
        # enriched 파일 찾기
        files = sorted(glob.glob("data/races/*/*/*/*/*_enriched.json"))

        print(f"총 {len(files)}개의 enriched 파일 발견")

        no_result_count = 0
        invalid_result_count = 0

        for file in files:
            race_data, result = self.load_race_with_result(file)

            if not race_data:
                continue

            if not result:
                no_result_count += 1
                continue

            if len(result) != 3:
                invalid_result_count += 1
                continue

            self.stats["total_races"] += 1

            # API 응답에서 말 데이터 추출
            if "response" in race_data and "body" in race_data["response"]:
                items = race_data["response"]["body"]["items"]["item"]
                horses = items if isinstance(items, list) else [items]

                # 기권/제외 제거
                valid_horses = [h for h in horses if h.get("winOdds", 0) > 0]

                self.stats["total_horses"] += len(horses)
                self.stats["valid_horses"] += len(valid_horses)

                # 배당률 순위 매기기
                valid_horses.sort(key=lambda x: x["winOdds"])
                odds_ranks = {h["chulNo"]: i+1 for i, h in enumerate(valid_horses)}

                # 각 말 분석
                for horse in valid_horses:
                    chul_no = horse["chulNo"]
                    is_winner = chul_no in result
                    odds_rank = odds_ranks.get(chul_no, 99)

                    self.analyze_horse(horse, is_winner, odds_rank)

                    # 성공/실패 패턴 수집
                    if is_winner and odds_rank <= 3:
                        self.stats["success_patterns"].append({
                            "type": "popular_horse_won",
                            "odds_rank": odds_rank,
                            "jockey_win_rate": self._get_jockey_win_rate(horse),
                            "horse_place_rate": self._get_horse_place_rate(horse)
                        })
                    elif is_winner and odds_rank > 5:
                        self.stats["success_patterns"].append({
                            "type": "underdog_won",
                            "odds_rank": odds_rank,
                            "jockey_win_rate": self._get_jockey_win_rate(horse),
                            "horse_place_rate": self._get_horse_place_rate(horse)
                        })

        print("\n디버깅 정보:")
        print(f"- 결과 파일 없음: {no_result_count}개")
        print(f"- 잘못된 결과 형식: {invalid_result_count}개")
        print(f"- 정상 분석: {self.stats["total_races"]}개")

    def _get_jockey_win_rate(self, horse: dict) -> float:
        """기수 승률 계산"""
        if "jkDetail" in horse and horse["jkDetail"]:
            jk = horse["jkDetail"]
            if jk.get("rcCntT", 0) > 0:
                return (jk.get("ord1CntT", 0) / jk["rcCntT"]) * 100
        return 0.0

    def _get_horse_place_rate(self, horse: dict) -> float:
        """말 입상률 계산"""
        if "hrDetail" in horse and horse["hrDetail"]:
            hr = horse["hrDetail"]
            if hr.get("rcCntT", 0) > 0:
                return ((hr.get("ord1CntT", 0) + hr.get("ord2CntT", 0) +
                        hr.get("ord3CntT", 0)) / hr["rcCntT"]) * 100
        return 0.0

    def print_analysis_results(self):
        """분석 결과 출력"""
        print(f"\n{"="*60}")
        print("📊 Enriched 데이터 패턴 분석 결과")
        print(f"{"="*60}")

        print("\n📈 기본 통계:")
        print(f"- 분석 경주 수: {self.stats["total_races"]}개")
        print(f"- 전체 말 수: {self.stats["total_horses"]}마리")
        print(f"- 유효 말 수: {self.stats["valid_horses"]}마리 (기권/제외 제외)")

        # 배당률 순위별 입상률
        print("\n🏇 배당률 순위별 실제 입상률:")
        print(f"{"순위":<6} {"출전":<8} {"입상":<8} {"입상률":<10} {"누적입상률":<12}")
        print("-" * 50)

        cumulative_top3 = 0
        cumulative_total = 0

        for rank in sorted(self.stats["odds_rank_distribution"].keys()):
            if rank <= 15:  # 상위 15위까지만 표시
                data = self.stats["odds_rank_distribution"][rank]
                total = data["total"]
                top3 = data["top3"]
                rate = (top3 / total * 100) if total > 0 else 0

                cumulative_top3 += top3
                cumulative_total += total
                cumulative_rate = (cumulative_top3 / cumulative_total * 100) if cumulative_total > 0 else 0

                print(f"{rank:<6} {total:<8} {top3:<8} {rate:<10.1f}% {cumulative_rate:<12.1f}%")

        # 기수 승률별 입상률
        print("\n🏆 기수 승률별 말의 입상률:")
        print(f"{"승률대":<10} {"출전":<8} {"입상":<8} {"입상률":<10}")
        print("-" * 40)

        for win_rate in sorted(self.stats["jockey_win_rate_bins"].keys()):
            data = self.stats["jockey_win_rate_bins"][win_rate]
            total = data["total"]
            top3 = data["top3"]
            rate = (top3 / total * 100) if total > 0 else 0

            print(f"{win_rate}-{win_rate+5}% {total:<8} {top3:<8} {rate:<10.1f}%")

        # 말 입상률별 입상률
        print("\n🐎 말 과거 입상률별 실제 입상률:")
        print(f"{"입상률대":<12} {"출전":<8} {"입상":<8} {"입상률":<10}")
        print("-" * 40)

        for place_rate in sorted(self.stats["horse_place_rate_bins"].keys()):
            data = self.stats["horse_place_rate_bins"][place_rate]
            total = data["total"]
            top3 = data["top3"]
            rate = (top3 / total * 100) if total > 0 else 0

            print(f"{place_rate}-{place_rate+10}% {total:<8} {top3:<8} {rate:<10.1f}%")

        # 부담중량 변화 영향
        print("\n⚖️ 부담중량 변화의 영향:")
        if self.stats["weight_change_impact"]["winner"]:
            winner_avg = statistics.mean(self.stats["weight_change_impact"]["winner"])
            loser_avg = statistics.mean(self.stats["weight_change_impact"]["loser"])
            print(f"- 입상마 평균 중량 변화: {winner_avg:+.1f}kg")
            print(f"- 미입상마 평균 중량 변화: {loser_avg:+.1f}kg")

        # 데이터 가용성
        print("\n📊 데이터 가용성:")
        total_valid = self.stats["valid_horses"]
        if total_valid > 0:
            print(f"- 말 상세정보 보유율: {self.stats["data_availability"]["has_hr_detail"]/total_valid*100:.1f}%")
            print(f"- 기수 상세정보 보유율: {self.stats["data_availability"]["has_jk_detail"]/total_valid*100:.1f}%")
            print(f"- 조교사 상세정보 보유율: {self.stats["data_availability"]["has_tr_detail"]/total_valid*100:.1f}%")

        # 핵심 인사이트
        print("\n💡 핵심 인사이트:")

        # 1-3위 배당률의 입상률 계산
        top3_odds_total = sum(self.stats["odds_rank_distribution"][i]["total"] for i in range(1, 4))
        top3_odds_winners = sum(self.stats["odds_rank_distribution"][i]["top3"] for i in range(1, 4))
        if top3_odds_total > 0:
            top3_rate = top3_odds_winners / top3_odds_total * 100
            print(f"1. 배당률 1-3위 말의 평균 입상률: {top3_rate:.1f}%")

        # 기수 승률 15% 이상의 영향
        high_jockey_total = sum(data["total"] for rate, data in self.stats["jockey_win_rate_bins"].items() if rate >= 15)
        high_jockey_winners = sum(data["top3"] for rate, data in self.stats["jockey_win_rate_bins"].items() if rate >= 15)
        if high_jockey_total > 0:
            high_jockey_rate = high_jockey_winners / high_jockey_total * 100
            print(f"2. 기수 승률 15% 이상 말의 입상률: {high_jockey_rate:.1f}%")

        # 말 입상률 30% 이상의 영향
        high_horse_total = sum(data["total"] for rate, data in self.stats["horse_place_rate_bins"].items() if rate >= 30)
        high_horse_winners = sum(data["top3"] for rate, data in self.stats["horse_place_rate_bins"].items() if rate >= 30)
        if high_horse_total > 0:
            high_horse_rate = high_horse_winners / high_horse_total * 100
            print(f"3. 말 과거 입상률 30% 이상의 실제 입상률: {high_horse_rate:.1f}%")

        print(f"\n{"="*60}")

    def save_analysis_report(self, filename: str = None):
        """분석 결과를 파일로 저장"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data/enriched_pattern_analysis_{timestamp}.json"

        report = {
            "analysis_date": datetime.now().isoformat(),
            "statistics": dict(self.stats),
            "insights": self._generate_insights()
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n📄 분석 보고서 저장: {filename}")

    def _generate_insights(self) -> dict:
        """인사이트 생성"""
        insights = {}

        # 배당률 순위별 누적 입상률
        cumulative_rates = {}
        cumulative_top3 = 0
        cumulative_total = 0

        for rank in sorted(self.stats["odds_rank_distribution"].keys()):
            if rank <= 10:
                data = self.stats["odds_rank_distribution"][rank]
                cumulative_top3 += data["top3"]
                cumulative_total += data["total"]
                if cumulative_total > 0:
                    cumulative_rates[f"top{rank}"] = cumulative_top3 / cumulative_total * 100

        insights["odds_cumulative_rates"] = cumulative_rates

        # 최적 기수 승률 구간
        if self.stats["jockey_win_rate_bins"]:
            best_jockey_rate = max(
                self.stats["jockey_win_rate_bins"].items(),
                key=lambda x: x[1]["top3"] / x[1]["total"] if x[1]["total"] > 10 else 0
            )
            insights["best_jockey_win_rate_range"] = f"{best_jockey_rate[0]}-{best_jockey_rate[0]+5}%"

        # 최적 말 입상률 구간
        if self.stats["horse_place_rate_bins"]:
            best_horse_rate = max(
                self.stats["horse_place_rate_bins"].items(),
                key=lambda x: x[1]["top3"] / x[1]["total"] if x[1]["total"] > 10 else 0
            )
            insights["best_horse_place_rate_range"] = f"{best_horse_rate[0]}-{best_horse_rate[0]+10}%"

        return insights


def main():
    print("Enriched 데이터 패턴 분석을 시작합니다...")

    analyzer = EnrichedDataAnalyzer()
    analyzer.analyze_all_races()
    analyzer.print_analysis_results()
    analyzer.save_analysis_report()


if __name__ == "__main__":
    main()
