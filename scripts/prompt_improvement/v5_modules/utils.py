"""
유틸리티 함수 모음

v5 재귀 개선 시스템에서 공통으로 사용되는 
유틸리티 함수들을 제공합니다.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
import hashlib
import logging


# 로거 설정
def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """로거 설정"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if not logger.handlers:
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        
        # 포맷터
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
    
    return logger


# 기본 로거
logger = setup_logger('v5_system')


# 파일 입출력 헬퍼
def read_json_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """JSON 파일 읽기"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"파일을 찾을 수 없습니다: {file_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"JSON 파싱 오류: {file_path} - {e}")
        return {}


def write_json_file(data: Dict[str, Any], file_path: Union[str, Path]) -> bool:
    """JSON 파일 쓰기"""
    try:
        # 디렉토리 생성
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"파일 쓰기 오류: {file_path} - {e}")
        return False


def read_text_file(file_path: Union[str, Path]) -> str:
    """텍스트 파일 읽기"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"파일을 찾을 수 없습니다: {file_path}")
        return ""
    except Exception as e:
        logger.error(f"파일 읽기 오류: {file_path} - {e}")
        return ""


def write_text_file(content: str, file_path: Union[str, Path]) -> bool:
    """텍스트 파일 쓰기"""
    try:
        # 디렉토리 생성
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"파일 쓰기 오류: {file_path} - {e}")
        return False


# 데이터 검증
def validate_race_data(race_data: Dict[str, Any]) -> bool:
    """경주 데이터 유효성 검증"""
    required_fields = ['entries', 'race_date', 'race_no']
    
    # 필수 필드 확인
    for field in required_fields:
        if field not in race_data:
            logger.warning(f"필수 필드 누락: {field}")
            return False
    
    # entries 검증
    entries = race_data.get('entries', [])
    if not entries:
        logger.warning("출주마 정보가 없습니다")
        return False
    
    # 각 출주마 검증
    for entry in entries:
        if 'horse_no' not in entry:
            logger.warning("말 번호가 없는 출주마 정보")
            return False
        
        # win_odds가 0인 경우는 기권/제외
        if entry.get('win_odds', 0) < 0:
            logger.warning(f"잘못된 배당률: 말번호 {entry['horse_no']}")
            return False
    
    return True


def validate_prediction_result(result: Dict[str, Any]) -> bool:
    """예측 결과 유효성 검증"""
    required_fields = ['predicted']
    
    for field in required_fields:
        if field not in result:
            logger.warning(f"예측 결과 필수 필드 누락: {field}")
            return False
    
    # predicted는 3개의 말 번호여야 함
    predicted = result.get('predicted', [])
    if not isinstance(predicted, list) or len(predicted) != 3:
        logger.warning(f"잘못된 예측 형식: {predicted}")
        return False
    
    # 중복 확인
    if len(set(predicted)) != len(predicted):
        logger.warning(f"중복된 예측: {predicted}")
        return False
    
    return True


# 버전 관리
def generate_version_string(base_version: str) -> str:
    """버전 문자열 생성 (예: v2.1_20250622_123456)"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{base_version}_{timestamp}"


def parse_version_string(version: str) -> Dict[str, str]:
    """버전 문자열 파싱"""
    parts = version.split('_')
    
    result = {
        'base': parts[0] if parts else '',
        'date': parts[1] if len(parts) > 1 else '',
        'time': parts[2] if len(parts) > 2 else '',
        'full': version
    }
    
    # 버전 번호 추출 (예: v2.1 -> 2.1)
    if result['base'].startswith('v'):
        result['number'] = result['base'][1:]
    else:
        result['number'] = result['base']
    
    return result


def increment_version(version: str) -> str:
    """버전 증가 (예: v2.1 -> v2.2)"""
    # 버전 번호 추출
    if version.startswith('v'):
        version_num = version[1:]
    else:
        version_num = version
    
    # 소수점으로 분리
    parts = version_num.split('.')
    if len(parts) >= 2:
        major = parts[0]
        minor = int(parts[1]) + 1
        return f"v{major}.{minor}"
    else:
        # 단순 버전
        try:
            num = int(version_num) + 1
            return f"v{num}"
        except ValueError:
            return "v1.0"


# 성능 계산
def calculate_success_metrics(evaluation_results: List[Dict[str, Any]]) -> Dict[str, float]:
    """평가 결과에서 성능 지표 계산"""
    if not evaluation_results:
        return {
            'success_rate': 0.0,
            'avg_correct': 0.0,
            'total_races': 0
        }
    
    total_races = 0
    successful_races = 0
    total_correct = 0
    
    for result in evaluation_results:
        if result.get('actual') and result.get('predicted'):
            total_races += 1
            
            correct_count = result.get('reward', {}).get('correct_count', 0)
            total_correct += correct_count
            
            if correct_count == 3:
                successful_races += 1
    
    return {
        'success_rate': (successful_races / total_races * 100) if total_races > 0 else 0,
        'avg_correct': total_correct / total_races if total_races > 0 else 0,
        'total_races': total_races
    }


# 데이터 필터링
def filter_valid_entries(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """유효한 출주마만 필터링 (win_odds > 0)"""
    return [
        entry for entry in entries
        if entry.get('win_odds', 0) > 0
    ]


def get_odds_rankings(entries: List[Dict[str, Any]]) -> Dict[int, int]:
    """배당률 기준 순위 계산"""
    # 유효한 출주마만 필터링
    valid_entries = filter_valid_entries(entries)
    
    # 배당률 기준 정렬 (낮은 배당률 = 인기마)
    sorted_entries = sorted(valid_entries, key=lambda x: x['win_odds'])
    
    # 말 번호별 순위
    rankings = {}
    for i, entry in enumerate(sorted_entries):
        rankings[entry['horse_no']] = i + 1
    
    return rankings


# 파일 경로 관리
def get_project_root() -> Path:
    """프로젝트 루트 경로 반환"""
    # 현재 파일 기준으로 상위 디렉토리 탐색
    current = Path(__file__).resolve()
    
    # scripts/prompt_improvement/v5_modules/utils.py
    # -> 3단계 상위가 프로젝트 루트
    return current.parent.parent.parent


def get_data_dir() -> Path:
    """데이터 디렉토리 경로 반환"""
    return get_project_root() / "data"


def get_prompts_dir() -> Path:
    """프롬프트 디렉토리 경로 반환"""
    return get_project_root() / "prompts"


def ensure_directory(directory: Union[str, Path]) -> Path:
    """디렉토리 존재 확인 및 생성"""
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


# 해시 및 ID 생성
def generate_id(prefix: str = "") -> str:
    """고유 ID 생성"""
    timestamp = datetime.now().isoformat()
    hash_input = f"{prefix}{timestamp}".encode('utf-8')
    hash_value = hashlib.md5(hash_input).hexdigest()[:8]
    
    if prefix:
        return f"{prefix}_{hash_value}"
    return hash_value


def calculate_file_hash(file_path: Union[str, Path]) -> str:
    """파일 해시 계산"""
    hash_md5 = hashlib.md5()
    
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.error(f"파일 해시 계산 오류: {file_path} - {e}")
        return ""


# 시간 관련
def format_duration(seconds: float) -> str:
    """시간 간격을 읽기 쉬운 형식으로 변환"""
    if seconds < 60:
        return f"{seconds:.1f}초"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}분"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}시간"


def get_timestamp() -> str:
    """현재 타임스탬프 반환"""
    return datetime.now().strftime('%Y%m%d_%H%M%S')


# 에러 처리
class V5SystemError(Exception):
    """v5 시스템 전용 예외"""
    pass


def safe_execute(func, *args, default=None, **kwargs):
    """안전한 함수 실행 (예외 처리 포함)"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"함수 실행 오류: {func.__name__} - {e}")
        return default


# 데이터 변환
def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """중첩된 딕셔너리를 평탄화"""
    items = []
    
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    
    return dict(items)


def unflatten_dict(d: Dict[str, Any], sep: str = '.') -> Dict[str, Any]:
    """평탄화된 딕셔너리를 중첩 구조로 복원"""
    result = {}
    
    for key, value in d.items():
        parts = key.split(sep)
        current = result
        
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        current[parts[-1]] = value
    
    return result


# 테스트용 함수
if __name__ == "__main__":
    # 로거 테스트
    logger.info("유틸리티 모듈 테스트")
    
    # 버전 관리 테스트
    version = "v2.1"
    print(f"현재 버전: {version}")
    print(f"다음 버전: {increment_version(version)}")
    print(f"버전 문자열: {generate_version_string(version)}")
    
    # 경로 테스트
    print(f"프로젝트 루트: {get_project_root()}")
    print(f"데이터 디렉토리: {get_data_dir()}")
    
    # ID 생성 테스트
    print(f"생성된 ID: {generate_id('test')}")
    
    # 시간 포맷 테스트
    print(f"30초: {format_duration(30)}")
    print(f"150초: {format_duration(150)}")
    print(f"7200초: {format_duration(7200)}")