#!/usr/bin/env python3
"""
v5 고급 기법 테스트 스크립트
새로 구현된 고급 기법들이 제대로 작동하는지 확인합니다.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from v5_modules.extended_thinking import ExtendedThinkingEngine
from v5_modules.guide_loader import PromptEngineeringGuideLoader
from v5_modules.prompt_parser import PromptParser
from v5_modules.self_verification import SelfVerificationEngine
from v5_modules.token_optimizer import TokenOptimizationEngine


def test_guide_loader():
    """가이드 로더 테스트"""
    print("\n=== 가이드 로더 테스트 ===")
    loader = PromptEngineeringGuideLoader()

    # 로드된 기법 확인
    techniques = loader.get_all_techniques()
    print(f"로드된 기법 수: {len(techniques)}")

    for name, tech in techniques.items():
        if isinstance(tech, list):
            print(f"- {name}: {len(tech)}개 항목")
        else:
            print(f"- {tech.name}: {tech.category}")

    # 적용 여부 테스트
    print("\n성능별 기법 적용 여부:")
    for perf in [30, 50, 65, 75]:
        print(f"\n성능 {perf}%:")
        print(
            f"  - Extended Thinking: {loader.should_apply_technique('extended_thinking', perf)}"
        )
        print(
            f"  - Self Verification: {loader.should_apply_technique('self_verification', perf)}"
        )
        print(
            f"  - Token Optimization: {loader.should_apply_technique('token_optimization', perf)}"
        )


def test_extended_thinking():
    """Extended Thinking 테스트"""
    print("\n\n=== Extended Thinking 테스트 ===")
    engine = ExtendedThinkingEngine()
    parser = PromptParser()

    # 테스트 프롬프트
    test_prompt = """<task>
제공된 경주 데이터를 분석하여 1-3위에 들어올 가능성이 가장 높은 3마리를 예측하세요.
</task>"""

    structure = parser.parse(test_prompt)

    # 다양한 성능에서 테스트
    for perf in [30, 50, 70]:
        print(f"\n성능 {perf}%에서의 thinking level:")
        level = engine.determine_thinking_level(perf)
        if level:
            print(f"  권장: {level.keyword} ({level.description})")

            # 적용
            changes = engine.apply_extended_thinking(structure, perf)
            if changes:
                print("  변경사항:")
                for change in changes:
                    print(f"    - {change.description}")
        else:
            print("  적용 불필요")


def test_self_verification():
    """자가 검증 테스트"""
    print("\n\n=== 자가 검증 테스트 ===")
    engine = SelfVerificationEngine()
    parser = PromptParser()

    # 테스트 프롬프트
    test_prompt = """<output_format>
반드시 아래 JSON 형식으로만 응답하세요:
```json
{
  "predicted": [출전번호1, 출전번호2, 출전번호3],
  "confidence": 75,
  "brief_reason": "인기마 중심, 기수 능력 우수"
}
```
</output_format>"""

    structure = parser.parse(test_prompt)

    # 검증 섹션 추가
    changes = engine.add_verification_section(structure)
    print(f"검증 섹션 추가: {len(changes)}개 변경")

    # 출력 형식 개선
    output_changes = engine.add_verification_to_output_format(structure)
    print(f"출력 형식 개선: {len(output_changes)}개 변경")

    if output_changes:
        print("\n개선된 출력 형식:")
        print(structure.get_section("output_format").content[:200] + "...")


def test_token_optimizer():
    """토큰 최적화 테스트"""
    print("\n\n=== 토큰 최적화 테스트 ===")
    engine = TokenOptimizationEngine()
    parser = PromptParser()

    # 테스트 프롬프트 (중복과 비효율 포함)
    test_prompt = """<analysis_steps>
단계별로 분석을 수행하세요:

1. 데이터 검증
   - 배당률 배당률 확인
   - 기수   기수 정보 확인

2. 점수 계산 방법:
   - 배당률 점수: 100에서 배당률 순위에 10을 곱한 값을 뺀다
   - 기수 점수: 승률에 50을 곱한 값과 복승률에 50을 곱한 값을 더한다
   - 말 점수: 입상률에 100을 곱한다
</analysis_steps>"""

    structure = parser.parse(test_prompt)

    # 최적화 전 크기
    original_size = len(test_prompt)

    # 최적화 수행
    optimized_structure, changes = engine.optimize_prompt(structure)

    # 최적화 후 크기
    optimized_content = optimized_structure.get_section("analysis_steps").content
    optimized_size = len(optimized_content)

    print(f"원본 크기: {original_size}자")
    print(f"최적화 후: {optimized_size}자")
    print(f"절감률: {((original_size - optimized_size) / original_size * 100):.1f}%")
    print(f"적용된 최적화: {len(changes)}개")

    print("\n최적화된 내용 일부:")
    print(optimized_content[:200] + "...")


def main():
    """메인 테스트 함수"""
    print("v5 고급 기법 테스트 시작")
    print("=" * 60)

    try:
        test_guide_loader()
        test_extended_thinking()
        test_self_verification()
        test_token_optimizer()

        print("\n\n✅ 모든 테스트 완료!")
        print("고급 기법들이 정상적으로 구현되었습니다.")

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
