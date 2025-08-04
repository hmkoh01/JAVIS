import os
import json
import logging
from typing import Dict, Any, List
from datetime import datetime

def setup_logging(log_level: str = "INFO"):
    """로깅 설정을 초기화합니다."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('javis_mas.log'),
            logging.StreamHandler()
        ]
    )

def load_config(config_path: str) -> Dict[str, Any]:
    """설정 파일을 로드합니다."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}

def save_config(config: Dict[str, Any], config_path: str):
    """설정을 파일에 저장합니다."""
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"설정 저장 중 오류: {e}")

def create_directories(directories: List[str]):
    """필요한 디렉토리들을 생성합니다."""
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def format_timestamp(timestamp: datetime) -> str:
    """타임스탬프를 포맷팅합니다."""
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")

def sanitize_filename(filename: str) -> str:
    """파일명을 안전하게 만듭니다."""
    import re
    # 특수문자 제거 및 공백을 언더스코어로 변경
    sanitized = re.sub(r'[^\w\s-]', '', filename)
    sanitized = re.sub(r'[-\s]+', '_', sanitized)
    return sanitized.strip('_')

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """텍스트를 청크로 분할합니다."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # 문장 경계에서 분할
        if end < len(text):
            # 마지막 마침표나 줄바꿈을 찾아서 분할
            last_period = text.rfind('.', start, end)
            last_newline = text.rfind('\n', start, end)
            split_point = max(last_period, last_newline)
            
            if split_point > start:
                end = split_point + 1
        
        chunks.append(text[start:end])
        start = end - overlap
        
        if start >= len(text):
            break
    
    return chunks

def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """텍스트에서 키워드를 추출합니다."""
    import re
    from collections import Counter
    
    # 한글, 영문, 숫자만 포함하는 단어 추출
    words = re.findall(r'[가-힣a-zA-Z0-9]+', text.lower())
    
    # 불용어 제거 (간단한 구현)
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    words = [word for word in words if word not in stop_words and len(word) > 1]
    
    # 빈도수 기반 키워드 추출
    word_counts = Counter(words)
    return [word for word, count in word_counts.most_common(max_keywords)]

def validate_email(email: str) -> bool:
    """이메일 주소의 유효성을 검사합니다."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def generate_session_id() -> str:
    """세션 ID를 생성합니다."""
    import uuid
    return str(uuid.uuid4())

def calculate_similarity(text1: str, text2: str) -> float:
    """두 텍스트 간의 유사도를 계산합니다 (간단한 구현)."""
    from difflib import SequenceMatcher
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

def safe_json_dumps(obj: Any) -> str:
    """안전한 JSON 직렬화를 수행합니다."""
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        return str(obj) 