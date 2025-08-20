import os
import yaml
import re
from typing import List, Dict, Any, Optional
import logging
import base64
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)

def compose_answer(question: str, evidences: List[Dict[str, Any]]) -> str:
    """근거를 바탕으로 응답 생성"""
    try:
        if not evidences:
            return "죄송합니다. 관련 정보를 찾을 수 없습니다."
        
        # 보안 패턴 로드
        security_patterns = _load_security_patterns()
        
        # 응답 구성
        answer_parts = []
        answer_parts.append(f"질문: {question}\n\n")
        answer_parts.append("찾은 정보:\n")
        
        for i, evidence in enumerate(evidences, 1):
            source = evidence.get('source', 'unknown')
            doc_id = evidence.get('doc_id', 'unknown')
            page = evidence.get('page')
            timestamp = evidence.get('timestamp')
            snippet = evidence.get('snippet', '')
            path = evidence.get('path', '')
            url = evidence.get('url', '')
            
            # 근거 라벨 생성
            evidence_label = f"[src:{source} doc:{doc_id}"
            if page is not None:
                evidence_label += f" page:{page}"
            if timestamp is not None:
                evidence_label += f" t:{timestamp}"
            evidence_label += "]"
            
            # 스니펫 또는 설명 생성
            if snippet:
                content = _redact_sensitive_info(snippet, security_patterns)
            elif path:
                content = f"파일: {os.path.basename(path)}"
            elif url:
                content = f"웹페이지: {url}"
            else:
                content = "관련 정보"
            
            answer_parts.append(f"{i}. {evidence_label} {content}\n")
        
        return "".join(answer_parts)
        
    except Exception as e:
        logger.error(f"응답 생성 오류: {e}")
        return "응답 생성 중 오류가 발생했습니다."

def _load_security_patterns() -> List[str]:
    """보안 패턴 로드"""
    try:
        config_path = "configs.yaml"
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config.get('security', {}).get('redact_patterns', [])
        else:
            # 기본 패턴
            return [
                r"(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",  # 이메일
                r"\b01[016789]-?\d{3,4}-?\d{4}\b",  # 전화번호
                r"\b\d{3}-\d{2}-\d{4}\b",  # 주민번호
                r"\b\d{4}-\d{4}-\d{4}-\d{4}\b"  # 신용카드
            ]
    except Exception as e:
        logger.error(f"보안 패턴 로드 오류: {e}")
        return []

def _redact_sensitive_info(text: str, patterns: List[str]) -> str:
    """민감 정보 마스킹"""
    try:
        redacted_text = text
        for pattern in patterns:
            redacted_text = re.sub(pattern, "[REDACTED]", redacted_text)
        return redacted_text
    except Exception as e:
        logger.error(f"민감 정보 마스킹 오류: {e}")
        return text

def call_vlm_for_answer(question: str, images: List[Image.Image], 
                       config_path: str = "configs.yaml") -> Optional[str]:
    """VLM을 사용한 멀티모달 응답 생성 (선택적)"""
    try:
        # VLM 설정 확인
        config = _load_vlm_config(config_path)
        if not config.get('enabled', False):
            return None
        
        # 이미지가 없으면 VLM 호출하지 않음
        if not images:
            return None
        
        # Qwen2-VL 모델 로드 및 호출
        return _call_qwen2_vl(question, images, config)
        
    except Exception as e:
        logger.error(f"VLM 호출 오류: {e}")
        return None

def _load_vlm_config(config_path: str) -> Dict[str, Any]:
    """VLM 설정 로드"""
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config.get('vlm', {})
        else:
            return {
                'enabled': False,
                'model_name': 'Qwen/Qwen2-VL-7B-Instruct',
                'quantization': True,
                'max_new_tokens': 500
            }
    except Exception as e:
        logger.error(f"VLM 설정 로드 오류: {e}")
        return {'enabled': False}

def _call_qwen2_vl(question: str, images: List[Image.Image], config: Dict[str, Any]) -> Optional[str]:
    """Qwen2-VL 모델 호출"""
    try:
        from transformers import Qwen2VLForConditionalGeneration, Qwen2VLProcessor, BitsAndBytesConfig
        from qwen_vl_utils import process_vision_info
        import torch
        
        # 모델 설정
        model_name = config.get('model_name', 'Qwen/Qwen2-VL-7B-Instruct')
        quantization = config.get('quantization', True)
        max_new_tokens = config.get('max_new_tokens', 500)
        
        # 양자화 설정
        if quantization:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16
            )
        else:
            bnb_config = None
        
        # 모델 로드
        model = Qwen2VLForConditionalGeneration.from_pretrained(
            model_name,
            device_map="auto",
            torch_dtype=torch.bfloat16,
            quantization_config=bnb_config
        )
        model.eval()
        
        # 프로세서 로드
        processor = Qwen2VLProcessor.from_pretrained(
            model_name,
            min_pixels=224 * 224,
            max_pixels=448 * 448
        )
        
        # 채팅 템플릿 구성
        chat_template = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": img} for img in images
                ] + [{"type": "text", "text": question}]
            }
        ]
        
        # 입력 처리
        text = processor.apply_chat_template(chat_template, tokenize=False, add_generation_prompt=True)
        image_inputs, _ = process_vision_info(chat_template)
        
        inputs = processor(
            text=[text],
            images=image_inputs,
            padding=True,
            return_tensors="pt"
        )
        inputs = inputs.to("cuda" if torch.cuda.is_available() else "cpu")
        
        # 생성
        with torch.no_grad():
            generated_ids = model.generate(**inputs, max_new_tokens=max_new_tokens)
        
        # 출력 디코딩
        generated_ids_trimmed = [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)]
        output_text = processor.batch_decode(
            generated_ids_trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False
        )
        
        return output_text[0] if output_text else None
        
    except ImportError:
        logger.warning("Qwen2-VL 모델을 사용할 수 없습니다. transformers 또는 qwen-vl-utils가 설치되지 않았습니다.")
        return None
    except Exception as e:
        logger.error(f"Qwen2-VL 호출 오류: {e}")
        return None

def images_to_base64(images: List[Image.Image]) -> List[str]:
    """이미지를 base64로 변환"""
    try:
        base64_images = []
        for img in images:
            buffer = BytesIO()
            img.save(buffer, format="JPEG")
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            base64_images.append(img_base64)
        return base64_images
    except Exception as e:
        logger.error(f"이미지 base64 변환 오류: {e}")
        return []
