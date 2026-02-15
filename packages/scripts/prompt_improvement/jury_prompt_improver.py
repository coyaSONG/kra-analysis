"""
LLM Jury 기반 프롬프트 개선 시스템

3개 모델(Claude, Codex, Gemini)이 독립적으로 프롬프트 수정안을 제안하고,
2/3 이상 합의된 수정만 적용하는 합의 기반 프롬프트 개선기입니다.
"""

from __future__ import annotations

import logging
import sys
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# 모듈 경로 설정
sys.path.insert(0, str(Path(__file__).parent))  # prompt_improvement (v5_modules 접근)
sys.path.insert(0, str(Path(__file__).parent.parent))  # scripts (shared 접근)

from shared.llm_client import LLMClient
from shared.llm_jury import LLMJury
from v5_modules.common_types import Change
from v5_modules.prompt_parser import PromptStructure

logger = logging.getLogger("jury_prompt_improver")


@dataclass
class PromptModification:
    """개별 프롬프트 수정 제안"""

    section: str  # 대상 섹션 태그
    action: str  # "modify", "add", "remove"
    description: str  # 변경 설명
    content: str  # 새 콘텐츠
    reasoning: str  # 수정 근거
    priority: int = 5  # 우선순위 (1=최고, 10=최저)
    source_model: str = ""  # 제안한 모델


class JuryPromptImprover:
    """LLM Jury 합의 기반 프롬프트 개선기

    1. 실패 사례 분석 + 현재 프롬프트 구조로 분석 프롬프트 구성
    2. LLMJury.deliberate()로 3개 모델에 수정안 요청
    3. (section, action) 쌍 기준 그룹화 → 2개 이상 모델 합의 수정만 승인
    4. 승인된 수정을 PromptStructure에 적용
    5. Fallback: 모델 응답 부족 시 DynamicReconstructor 사용
    """

    # 수정안 요청 프롬프트 템플릿
    ANALYSIS_PROMPT_TEMPLATE = """당신은 경마 예측 프롬프트 최적화 전문가입니다.

현재 프롬프트의 구조와 실패 사례를 분석하여 구체적인 수정안을 JSON 형식으로 제안하세요.

## 현재 프롬프트 섹션 목록
{section_list}

## 성능 지표
- 성공률: {success_rate:.1f}%
- 평균 적중: {avg_correct:.2f}마리
- 평가 경주 수: {total_races}개

## 실패 사례 분석
{failure_analysis}

## 요구사항
- 각 수정안은 특정 섹션(section)에 대한 구체적인 변경입니다.
- action: "modify" (기존 섹션 수정), "add" (새 섹션 추가), "remove" (섹션 제거)
- 수정 근거를 명확히 설명하세요.
- 우선순위(1=최고~10=최저)를 지정하세요.

다음 JSON 형식으로 응답하세요:
```json
{{
  "modifications": [
    {{
      "section": "analysis_steps",
      "action": "modify",
      "description": "거리 적성 분석 단계 강화",
      "content": "새로운 분석 단계 내용...",
      "reasoning": "실패 사례에서 거리 적성 미반영이 주요 원인",
      "priority": 3
    }}
  ]
}}
```"""

    def __init__(
        self,
        jury: LLMJury,
        fallback_reconstructor: Any | None = None,
        min_consensus: int = 2,
    ):
        """
        Args:
            jury: LLMJury 인스턴스
            fallback_reconstructor: 합의 실패 시 사용할 DynamicReconstructor (선택)
            min_consensus: 최소 합의 모델 수 (기본: 2)
        """
        self.jury = jury
        self.fallback = fallback_reconstructor
        self.min_consensus = min_consensus

    def improve_prompt(
        self,
        current_structure: PromptStructure,
        detailed_results: list[dict],
        metrics: dict[str, Any],
        new_version: str,
        insight_analysis: Any | None = None,
    ) -> tuple[PromptStructure, list[Change]]:
        """프롬프트 개선 실행.

        Args:
            current_structure: 현재 프롬프트 구조
            detailed_results: 평가 상세 결과 목록
            metrics: 성능 지표 dict
            new_version: 새 버전 문자열
            insight_analysis: InsightAnalysis 인스턴스 (fallback용)

        Returns:
            (새 PromptStructure, 적용된 Change 목록)
        """
        # 1. 분석 프롬프트 구성
        analysis_prompt = self._build_analysis_prompt(
            current_structure, detailed_results, metrics
        )

        # 2. Jury 심의
        verdict = self.jury.deliberate(analysis_prompt, timeout=3000)

        # 3. 응답에서 수정안 파싱
        all_modifications: list[PromptModification] = []
        for resp in verdict.successful_responses:
            if not resp.text:
                continue

            mods = self._parse_modifications(resp.text, resp.model_name)
            all_modifications.extend(mods)

        logger.info(
            f"[Jury] 수집된 수정안: {len(all_modifications)}개 "
            f"(from {len(verdict.successful_responses)} models)"
        )

        # 4. 합의 기반 필터링
        approved = self._vote_on_modifications(all_modifications)

        logger.info(f"[Jury] 합의된 수정안: {len(approved)}개")

        # 5. 합의된 수정이 없으면 fallback
        if not approved and self.fallback and insight_analysis:
            logger.info("[Jury] 합의 실패 → DynamicReconstructor fallback")
            return self.fallback.reconstruct_prompt(
                current_structure, insight_analysis, new_version, metrics
            )

        # 6. 승인된 수정을 PromptStructure에 적용
        new_structure = deepcopy(current_structure)
        new_structure.version = new_version
        changes: list[Change] = []

        for mod in approved:
            change = self._apply_modification(new_structure, mod)
            if change:
                changes.append(change)

        return new_structure, changes

    def _build_analysis_prompt(
        self,
        structure: PromptStructure,
        detailed_results: list[dict],
        metrics: dict[str, Any],
    ) -> str:
        """분석 프롬프트 구성"""
        # 섹션 목록
        section_list = []
        for tag, section in sorted(
            structure.sections.items(), key=lambda x: x[1].order
        ):
            preview = section.content[:100].replace("\n", " ")
            section_list.append(f"- <{tag}>: {preview}...")

        section_list_str = "\n".join(section_list) if section_list else "(섹션 없음)"

        # 실패 사례 분석
        failures = [
            r
            for r in detailed_results
            if r.get("prediction") is not None
            and r.get("reward", {}).get("correct_count", 0) == 0
        ]

        failure_lines = []
        for f in failures[:10]:  # 최대 10개
            pred = f.get("predicted", [])
            actual = f.get("actual", [])
            confidence = f.get("confidence", 0)
            reasoning = f.get("reasoning", "")[:100]
            failure_lines.append(
                f"  - 예측: {pred}, 실제: {actual}, 신뢰도: {confidence}, 근거: {reasoning}"
            )

        failure_analysis = (
            "\n".join(failure_lines) if failure_lines else "(실패 사례 없음)"
        )

        return self.ANALYSIS_PROMPT_TEMPLATE.format(
            section_list=section_list_str,
            success_rate=metrics.get("success_rate", 0),
            avg_correct=metrics.get("avg_correct", 0),
            total_races=metrics.get("total_races", 0),
            failure_analysis=failure_analysis,
        )

    def _parse_modifications(
        self, text: str, model_name: str
    ) -> list[PromptModification]:
        """모델 응답에서 수정안 파싱"""
        parsed = LLMClient.parse_json(text)
        if not parsed:
            return []

        modifications = []
        raw_mods = parsed.get("modifications", [])
        if not isinstance(raw_mods, list):
            return []

        for raw in raw_mods:
            if not isinstance(raw, dict):
                continue

            section = raw.get("section", "")
            action = raw.get("action", "modify")
            if not section or action not in ("modify", "add", "remove"):
                continue

            mod = PromptModification(
                section=section,
                action=action,
                description=raw.get("description", ""),
                content=raw.get("content", ""),
                reasoning=raw.get("reasoning", ""),
                priority=int(raw.get("priority", 5)),
                source_model=model_name,
            )
            modifications.append(mod)

        return modifications

    def _vote_on_modifications(
        self, all_mods: list[PromptModification]
    ) -> list[PromptModification]:
        """(section, action) 쌍 기준 그룹화 → min_consensus 이상 합의 수정만 승인.

        동일 (section, action)을 제안한 모델이 min_consensus 이상이면 승인.
        승인된 수정 중 가장 높은 우선순위(낮은 숫자)의 수정안을 대표로 선택.
        """
        # (section, action) → [PromptModification]
        groups: dict[tuple[str, str], list[PromptModification]] = defaultdict(list)
        for mod in all_mods:
            key = (mod.section, mod.action)
            groups[key].append(mod)

        approved: list[PromptModification] = []
        for _key, mods in groups.items():
            # 서로 다른 모델에서 온 수정안만 카운트
            unique_models = {m.source_model for m in mods}
            if len(unique_models) >= self.min_consensus:
                # 가장 높은 우선순위(낮은 숫자)의 수정안을 대표로 선택
                best = min(mods, key=lambda m: m.priority)
                approved.append(best)

        # 우선순위 순 정렬
        approved.sort(key=lambda m: m.priority)
        return approved

    def _apply_modification(
        self, structure: PromptStructure, mod: PromptModification
    ) -> Change | None:
        """단일 수정안을 PromptStructure에 적용"""
        if mod.action == "modify":
            existing = structure.get_section(mod.section)
            old_value = existing.content if existing else None
            structure.update_section(mod.section, mod.content)
            return Change(
                change_type="modify",
                target_section=mod.section,
                description=f"[Jury:{mod.source_model}] {mod.description}",
                old_value=old_value,
                new_value=mod.content,
            )

        elif mod.action == "add":
            structure.add_section(mod.section, mod.content)
            return Change(
                change_type="add",
                target_section=mod.section,
                description=f"[Jury:{mod.source_model}] {mod.description}",
                new_value=mod.content,
            )

        elif mod.action == "remove":
            existing = structure.get_section(mod.section)
            old_value = existing.content if existing else None
            removed = structure.remove_section(mod.section)
            if removed:
                return Change(
                    change_type="remove",
                    target_section=mod.section,
                    description=f"[Jury:{mod.source_model}] {mod.description}",
                    old_value=old_value,
                )

        return None
