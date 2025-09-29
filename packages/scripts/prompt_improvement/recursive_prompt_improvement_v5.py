#!/usr/bin/env python3
"""
재귀 프롬프트 개선 시스템 v5

v4의 문제점을 해결하여 실제로 프롬프트 내용을 개선하는
진정한 재귀 개선 시스템입니다.

주요 개선사항:
1. 프롬프트 파싱 및 구조화
2. 심층 인사이트 분석
3. 동적 프롬프트 재구성
4. 체계적인 예시 관리
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# v5 모듈 임포트
sys.path.append(str(Path(__file__).parent))
from v5_modules import (
    DynamicReconstructor,
    ExamplesManager,
    InsightAnalyzer,
    PromptParser,
)
from v5_modules.utils import (
    calculate_success_metrics,
    ensure_directory,
    format_duration,
    get_data_dir,
    get_prompts_dir,
    increment_version,
    read_json_file,
    read_text_file,
    setup_logger,
    write_text_file,
)


class RecursivePromptImprovementV5:
    """재귀 프롬프트 개선 시스템 v5"""

    def __init__(self,
                 initial_prompt_path: Path,
                 target_date: str = "all",
                 max_iterations: int = 5,
                 parallel_count: int = 5,
                 race_limit: str = None):

        self.initial_prompt_path = initial_prompt_path
        self.target_date = target_date
        self.max_iterations = max_iterations
        self.parallel_count = parallel_count
        self.race_limit = race_limit

        # 작업 디렉토리 설정
        self.working_dir = get_data_dir() / f"recursive_improvement_v5/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        ensure_directory(self.working_dir)

        # 로거 설정
        self.logger = setup_logger("v5_main")

        # 모듈 초기화
        self.prompt_parser = PromptParser()
        self.insight_analyzer = InsightAnalyzer()
        self.reconstructor = DynamicReconstructor()
        self.examples_manager = ExamplesManager()

        # 상태 관리
        self.iteration_history = []
        self.best_performance = 0.0
        self.best_prompt_path = None

    def run(self) -> dict[str, Any]:
        """재귀 개선 프로세스 실행"""
        self.logger.info("=" * 80)
        self.logger.info("재귀 프롬프트 개선 시스템 v5 시작")
        self.logger.info(f"초기 프롬프트: {self.initial_prompt_path}")
        self.logger.info(f"대상 날짜: {self.target_date}")
        self.logger.info(f"최대 반복: {self.max_iterations}회")
        self.logger.info("=" * 80)

        # 초기 프롬프트 읽기 및 파싱
        current_prompt_path = self.initial_prompt_path
        current_prompt_content = read_text_file(current_prompt_path)
        current_structure = self.prompt_parser.parse(current_prompt_content)

        # 초기 버전 설정
        if not current_structure.version:
            current_structure.version = "v1.0"

        start_time = time.time()

        for iteration in range(1, self.max_iterations + 1):
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"반복 {iteration}/{self.max_iterations} 시작")
            self.logger.info(f"현재 프롬프트: {current_structure.version}")

            iteration_start = time.time()

            # 1. 프롬프트 평가
            self.logger.info("\n[1단계] 프롬프트 평가 중...")
            evaluation_results = self._evaluate_prompt(current_prompt_path)

            if not evaluation_results:
                self.logger.error("평가 실패 - 중단")
                break

            # 성능 계산
            metrics = calculate_success_metrics(evaluation_results["detailed_results"])
            current_performance = metrics["success_rate"]

            self.logger.info("평가 완료:")
            self.logger.info(f"  - 성공률: {current_performance:.1f}%")
            self.logger.info(f"  - 평균 적중: {metrics['avg_correct']:.2f}마리")
            self.logger.info(f"  - 평가 경주 수: {metrics['total_races']}개")

            # 이력 저장
            iteration_data = {
                "iteration": iteration,
                "version": current_structure.version,
                "performance": current_performance,
                "metrics": metrics,
                "prompt_path": str(current_prompt_path)
            }
            self.iteration_history.append(iteration_data)

            # 최고 성능 업데이트
            if current_performance > self.best_performance:
                self.best_performance = current_performance
                self.best_prompt_path = current_prompt_path
                self.logger.info(f"🎯 새로운 최고 성능: {current_performance:.1f}%")

            # 목표 달성 확인
            if current_performance >= 70.0:
                self.logger.info("🎉 목표 성능(70%) 달성!")
                break

            # 마지막 반복이면 개선 없이 종료
            if iteration == self.max_iterations:
                self.logger.info("최대 반복 횟수 도달")
                break

            # 2. 인사이트 분석
            self.logger.info("\n[2단계] 인사이트 분석 중...")

            # 예시 추가 (최대 20개)
            added_count = self.examples_manager.add_examples_from_evaluation(
                evaluation_results["detailed_results"],
                limit=20
            )
            self.logger.info(f"  - 예시 풀에 {added_count}개 추가")

            # 인사이트 분석
            insight_analysis = self.insight_analyzer.analyze(
                evaluation_results["detailed_results"]
            )

            # 분석 보고서 저장
            analysis_report = self.insight_analyzer.generate_report(insight_analysis)
            analysis_path = self.working_dir / f"analysis_iteration_{iteration}.md"
            write_text_file(analysis_report, analysis_path)

            self.logger.info(f"  - 주요 발견사항: {len(insight_analysis.summary.get("key_findings", []))}개")
            self.logger.info(f"  - 권고사항: {len(insight_analysis.recommendations)}개")

            # 3. 프롬프트 개선
            self.logger.info("\n[3단계] 프롬프트 개선 중...")

            # 새 버전 번호 생성
            new_version = increment_version(current_structure.version)

            # 프롬프트 재구성
            new_structure, changes = self.reconstructor.reconstruct_prompt(
                current_structure,
                insight_analysis,
                new_version,
                metrics
            )

            # 고급 기법 적용 상태 로깅
            advanced_status = self.reconstructor.get_advanced_techniques_status(current_performance)
            applied_techniques = [tech for tech, applied in advanced_status.items() if applied]
            if applied_techniques:
                self.logger.info(f"  - 적용된 고급 기법: {", ".join(applied_techniques)}")

            # 예시 업데이트
            used_example_ids = self.examples_manager.update_examples_section(
                new_structure,
                strategy="balanced"
            )

            # 성능 추적
            self.examples_manager.track_usage_performance(
                used_example_ids,
                current_performance
            )

            self.logger.info(f"  - 적용된 변경사항: {len(changes)}개")
            for change in changes[:5]:  # 상위 5개 표시
                self.logger.info(f"    • {change.description}")

            # 특별히 고급 기법 관련 변경사항 강조
            advanced_changes = [c for c in changes if any(
                tech in c.description.lower() for tech in ["thinking", "검증", "토큰", "최적화"]
            )]
            if advanced_changes:
                self.logger.info("  - 고급 기법 변경사항:")
                for change in advanced_changes[:3]:
                    self.logger.info(f"    ★ {change.description}")

            # 검증
            validation_issues = self.reconstructor.validate_changes(new_structure)
            if validation_issues:
                self.logger.warning(f"검증 문제 발견: {validation_issues}")

            # 4. 새 프롬프트 저장
            new_prompt_content = new_structure.to_prompt()
            new_prompt_filename = f"prompt_{new_version}.md"
            new_prompt_path = self.working_dir / new_prompt_filename
            write_text_file(new_prompt_content, new_prompt_path)

            # prompts 폴더에도 복사
            official_path = get_prompts_dir() / f"prediction-template-{new_version}.md"
            write_text_file(new_prompt_content, official_path)

            self.logger.info("\n개선된 프롬프트 저장:")
            self.logger.info(f"  - 작업 경로: {new_prompt_path}")
            self.logger.info(f"  - 공식 경로: {official_path}")

            # 다음 반복 준비
            current_prompt_path = new_prompt_path
            current_structure = new_structure

            # 반복 시간 로그
            iteration_time = time.time() - iteration_start
            self.logger.info(f"\n반복 {iteration} 완료 (소요시간: {format_duration(iteration_time)})")

            # 저성과 예시 정리
            if iteration % 3 == 0:  # 3회마다
                removed = self.examples_manager.cleanup_low_performers()
                if removed > 0:
                    self.logger.info(f"저성과 예시 {removed}개 제거")

        # 5. 최종 결과 정리
        total_time = time.time() - start_time

        self.logger.info("\n" + "="*80)
        self.logger.info("재귀 개선 프로세스 완료")
        self.logger.info(f"총 소요시간: {format_duration(total_time)}")
        self.logger.info(f"최고 성능: {self.best_performance:.1f}% ({self.best_prompt_path})")

        # 최종 보고서 생성
        final_report = self._generate_final_report()
        report_path = self.working_dir / "final_report.md"
        write_text_file(final_report, report_path)

        # 결과 반환
        return {
            "success": True,
            "best_performance": self.best_performance,
            "best_prompt_path": str(self.best_prompt_path),
            "iterations": len(self.iteration_history),
            "working_dir": str(self.working_dir),
            "report_path": str(report_path)
        }

    def _evaluate_prompt(self, prompt_path: Path) -> dict[str, Any] | None:
        """프롬프트 평가 실행"""
        try:
            # 버전 추출
            prompt_content = read_text_file(prompt_path)
            structure = self.prompt_parser.parse(prompt_content)
            version = structure.version or "unknown"

            # evaluate_prompt_v3.py 실행
            # 사용자가 지정한 경주 수 또는 자동 설정
            if self.race_limit:
                if self.race_limit.lower() == "all":
                    # 전체 경주 사용 (사실상 무제한)
                    race_count = "999999"
                else:
                    # 숫자로 지정된 경우
                    race_count = self.race_limit
            else:
                # 테스트 모드에서는 경주 수를 줄임
                # 일반 모드에서는 더 많은 경주를 평가
                if self.max_iterations <= 2:
                    race_count = "5"  # 빠른 테스트
                elif self.max_iterations <= 5:
                    race_count = "50"  # 중간 규모 평가
                else:
                    race_count = "100"  # 대규모 평가

            cmd = [
                "python3",
                str(Path(__file__).parent.parent / "evaluation" / "evaluate_prompt_v3.py"),
                version,
                str(prompt_path),
                race_count,  # 평가할 경주 수
                str(self.parallel_count)
            ]

            if self.target_date != "all":
                # 특정 날짜만 평가하도록 수정 필요
                pass

            self.logger.info(f"평가 명령: {" ".join(cmd)}")
            if race_count == "999999":
                self.logger.info("평가할 경주 수: 전체 (제한 없음)")
            else:
                self.logger.info(f"평가할 경주 수: {race_count}개")

            # 실행
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(Path(__file__).parent.parent.parent)
            )

            if result.returncode != 0:
                self.logger.error(f"평가 실패: {result.stderr}")
                return None

            # 잠시 대기 (파일 생성 시간)
            time.sleep(2)

            # 결과 파일 찾기
            eval_dir = get_data_dir() / "prompt_evaluation"
            # v2.3 형식도 지원
            eval_files = list(eval_dir.glob(f"evaluation_{version}_*.json"))

            self.logger.info(f"평가 디렉토리: {eval_dir}")
            self.logger.info(f"검색 패턴: evaluation_{version}_*.json")
            self.logger.info(f"찾은 파일 수: {len(eval_files)}")

            if not eval_files:
                self.logger.error(f"평가 결과 파일을 찾을 수 없습니다: evaluation_{version}_*.json")
                # 디렉토리 내용 확인
                all_files = list(eval_dir.glob("evaluation_*.json"))
                self.logger.info(f"디렉토리의 모든 평가 파일: {len(all_files)}개")
                if all_files:
                    self.logger.info(f"최근 파일 예시: {all_files[-1].name}")
                return None

            # 가장 최근 파일 읽기
            latest_file = max(eval_files, key=lambda p: p.stat().st_mtime)
            return read_json_file(latest_file)

        except Exception as e:
            self.logger.error(f"평가 중 오류: {e}")
            return None

    def _generate_final_report(self) -> str:
        """최종 보고서 생성"""
        report = []

        report.append("# 재귀 프롬프트 개선 v5 최종 보고서\n")
        report.append(f"생성일시: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n")

        # 요약
        report.append("## 요약")
        report.append(f"- 초기 프롬프트: {self.initial_prompt_path}")
        report.append(f"- 총 반복 횟수: {len(self.iteration_history)}")
        report.append(f"- 최고 성능: {self.best_performance:.1f}%")
        report.append(f"- 최고 성능 프롬프트: {self.best_prompt_path}")

        # 성능 추이
        report.append("\n## 성능 추이")
        report.append("| 반복 | 버전 | 성공률 | 평균 적중 |")
        report.append("|------|------|--------|-----------|")

        for item in self.iteration_history:
            report.append(
                f"| {item["iteration"]} | {item["version"]} | "
                f"{item["performance"]:.1f}% | "
                f"{item["metrics"]["avg_correct"]:.2f}마리 |"
            )

        # 개선 내역
        report.append("\n## 주요 개선 내역")

        # 변경 이력 가져오기
        change_report = self.reconstructor.generate_change_report()
        report.append(change_report)

        # 예시 통계
        report.append("\n## 예시 관리 통계")
        stats = self.examples_manager.get_statistics()
        report.append(f"- 총 예시 수: {stats["total_examples"]}")
        report.append(f"- 성공 예시: {stats["success_examples"]}")
        report.append(f"- 실패 예시: {stats["failure_examples"]}")
        report.append(f"- 평균 성과: {stats["avg_performance"]:.1f}%")

        # 결론
        report.append("\n## 결론")

        if self.best_performance >= 70.0:
            report.append("✅ **목표 달성**: 70% 이상의 성공률을 달성했습니다!")
        else:
            improvement = self.best_performance - self.iteration_history[0]["performance"]
            report.append(f"📈 **개선 성과**: {improvement:+.1f}% 향상")
            report.append(f"   (초기: {self.iteration_history[0]["performance"]:.1f}% → 최종: {self.best_performance:.1f}%)")

        # v4와의 차이점
        report.append("\n## v4 대비 개선사항")
        report.append("1. **실제 프롬프트 개선**: 단순 예시 변경이 아닌 구조적 개선")
        report.append("2. **인사이트 기반**: 데이터 분석에 기반한 구체적 개선")
        report.append("3. **체계적 예시 관리**: 성과 추적 및 최적 선택")
        report.append("4. **투명한 변경 추적**: 모든 변경사항 기록 및 검증")
        report.append("5. **고급 기법 통합**: Extended Thinking, 강화된 검증, 토큰 최적화")

        # 고급 기법 사용 내역
        report.append("\n## 고급 기법 적용 내역")
        report.append("### 프롬프트 엔지니어링 가이드 기반 개선")

        # 각 반복에서 적용된 기법 추적
        techniques_used = set()
        for item in self.iteration_history:
            perf = item["performance"]
            status = self.reconstructor.get_advanced_techniques_status(perf)
            for tech, applied in status.items():
                if applied:
                    techniques_used.add(tech)

        if "extended_thinking" in techniques_used:
            report.append("- **Extended Thinking Mode**: 저성과 구간에서 ultrathink 키워드 적용")
        if "self_verification" in techniques_used:
            report.append("- **강화된 자가 검증**: 다단계 검증 프로세스 및 오류 복구 가이드 추가")
        if "token_optimization" in techniques_used:
            report.append("- **토큰 최적화**: 중복 제거, 표 형식 도입, 약어 사용으로 효율성 향상")

        return "\n".join(report)


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="재귀 프롬프트 개선 시스템 v5",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 기본 실행 (base-prompt-v1.0.md, 모든 날짜, 5회 반복)
  python3 recursive_prompt_improvement_v5.py

  # 특정 프롬프트로 시작
  python3 recursive_prompt_improvement_v5.py prompts/prediction-template-v2.1.md

  # 10회 반복, 병렬 처리 10개
  python3 recursive_prompt_improvement_v5.py -i 10 -p 10

  # 200개 경주로 평가
  python3 recursive_prompt_improvement_v5.py -r 200

  # 전체 경주 사용
  python3 recursive_prompt_improvement_v5.py -r all

  # 전체 옵션 사용
  python3 recursive_prompt_improvement_v5.py -i 5 -p 15 -r 150
        """
    )

    parser.add_argument(
        "prompt_path",
        nargs="?",
        default="prompts/base-prompt-v1.0.md",
        help="초기 프롬프트 파일 경로 (기본값: prompts/base-prompt-v1.0.md)"
    )

    parser.add_argument(
        "target_date",
        nargs="?",
        default="all",
        help="평가 대상 날짜 (YYYYMMDD 또는 all, 기본값: all)"
    )

    parser.add_argument(
        "-i", "--iterations",
        type=int,
        default=5,
        help="최대 반복 횟수 (기본값: 5)"
    )

    parser.add_argument(
        "-p", "--parallel",
        type=int,
        default=5,
        help="병렬 처리 수 (기본값: 5)"
    )

    parser.add_argument(
        "-r", "--races",
        type=str,
        default=None,
        help="평가할 경주 수 (기본값: 자동 - 반복수에 따라 5/50/100, 'all': 전체 경주)"
    )

    args = parser.parse_args()

    # 경로 검증
    prompt_path = Path(args.prompt_path)
    if not prompt_path.exists():
        print(f"오류: 프롬프트 파일을 찾을 수 없습니다: {prompt_path}")
        sys.exit(1)

    # v5 시스템 실행
    system = RecursivePromptImprovementV5(
        initial_prompt_path=prompt_path,
        target_date=args.target_date,
        max_iterations=args.iterations,
        parallel_count=args.parallel,
        race_limit=args.races
    )

    try:
        result = system.run()

        if result["success"]:
            print("\n✅ 재귀 개선 완료!")
            print(f"   최고 성능: {result["best_performance"]:.1f}%")
            print(f"   최고 성능 프롬프트: {result["best_prompt_path"]}")
            print(f"   보고서: {result["report_path"]}")
        else:
            print("\n❌ 재귀 개선 실패")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
        sys.exit(130)
    except Exception as e:
        print(f"\n오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
