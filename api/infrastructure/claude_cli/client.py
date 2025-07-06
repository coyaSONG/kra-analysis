import asyncio
import subprocess
import json
import tempfile
import os
from typing import Dict, Any, Optional
import structlog
from config import settings


logger = structlog.get_logger()


class ClaudeCodeCLIClient:
    def __init__(self):
        self.claude_code_path = settings.claude_code_path
        self.use_prompt_mode = settings.claude_prompt_mode
        self.timeout = settings.claude_timeout
    
    async def run_prompt(self, prompt_content: str, input_data: Optional[str] = None) -> str:
        """
        Claude Code CLI를 사용하여 프롬프트를 실행합니다.
        
        Args:
            prompt_content: 실행할 프롬프트 내용
            input_data: 프롬프트에 전달할 입력 데이터
        
        Returns:
            Claude의 응답 텍스트
        """
        try:
            # 임시 프롬프트 파일 생성
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.md',
                delete=False,
                encoding='utf-8'
            ) as f:
                f.write(prompt_content)
                prompt_file = f.name
            
            # Claude Code 명령어 구성
            cmd = [self.claude_code_path]
            
            if self.use_prompt_mode:
                cmd.append("-p")
            
            cmd.append(prompt_file)
            
            # 입력 데이터가 있으면 stdin으로 전달
            input_bytes = input_data.encode('utf-8') if input_data else None
            
            # 프로세스 실행
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE if input_bytes else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            # 결과 대기
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=input_bytes),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise TimeoutError(f"Claude Code CLI timed out after {self.timeout} seconds")
            
            # 임시 파일 삭제
            os.unlink(prompt_file)
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
                raise RuntimeError(f"Claude Code CLI failed: {error_msg}")
            
            return stdout.decode('utf-8')
            
        except Exception as e:
            logger.error("Failed to run Claude Code CLI", error=str(e))
            raise
    
    async def predict_race(self, prompt_path: str, race_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        경주 예측을 수행합니다.
        
        Args:
            prompt_path: 프롬프트 파일 경로
            race_data: 경주 데이터
        
        Returns:
            예측 결과 (prediction, confidence, reasoning)
        """
        try:
            # 프롬프트 파일 읽기
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt_content = f.read()
            
            # 경주 데이터를 JSON으로 변환
            race_json = json.dumps(race_data, ensure_ascii=False, indent=2)
            
            # 프롬프트에 데이터 추가
            full_prompt = f"{prompt_content}\n\n<race_data>\n{race_json}\n</race_data>"
            
            # Claude 실행
            response = await self.run_prompt(full_prompt)
            
            # 응답 파싱 (응답 형식에 따라 조정 필요)
            # 임시로 하드코딩된 값 반환
            return {
                "prediction": [2, 5, 8],
                "confidence": 0.75,
                "reasoning": response[:500]  # 처음 500자만 사용
            }
            
        except Exception as e:
            logger.error("Failed to predict race", error=str(e))
            raise
    
    async def improve_prompt(
        self,
        base_prompt: str,
        performance_data: Dict[str, Any],
        insights: Dict[str, Any]
    ) -> str:
        """
        프롬프트를 개선합니다.
        
        Args:
            base_prompt: 기본 프롬프트
            performance_data: 성능 데이터
            insights: 분석된 인사이트
        
        Returns:
            개선된 프롬프트
        """
        try:
            # 개선 요청 프롬프트 구성
            improvement_prompt = f"""
당신은 경마 예측 프롬프트를 개선하는 전문가입니다.

현재 프롬프트:
{base_prompt}

성능 데이터:
{json.dumps(performance_data, ensure_ascii=False, indent=2)}

분석된 인사이트:
{json.dumps(insights, ensure_ascii=False, indent=2)}

위 정보를 바탕으로 프롬프트를 개선해주세요. 
개선된 프롬프트만 출력하고 다른 설명은 하지 마세요.
"""
            
            # Claude 실행
            improved_prompt = await self.run_prompt(improvement_prompt)
            
            return improved_prompt.strip()
            
        except Exception as e:
            logger.error("Failed to improve prompt", error=str(e))
            raise