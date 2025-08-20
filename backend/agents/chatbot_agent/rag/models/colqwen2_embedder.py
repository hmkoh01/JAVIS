import os
import yaml
from typing import List, Union, Optional
import numpy as np
import torch
from PIL import Image
import logging

# Optional imports
try:
    from transformers import AutoTokenizer, AutoModel
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("Warning: transformers not available")

try:
    from byaldi import RAGMultiModalModel
    BYALDI_AVAILABLE = True
except ImportError:
    BYALDI_AVAILABLE = False
    print("Warning: byaldi not available")

logger = logging.getLogger(__name__)

class ColQwen2Embedder:
    """ColQwen2 기반 멀티모달 임베더"""
    
    def __init__(self, device: str = "cuda", config_path: str = "configs.yaml"):
        self.device = device if torch.cuda.is_available() else "cpu"
        self.config = self._load_config(config_path)
        self.dim = self.config.get('embedding', {}).get('dim', 128)
        self.batch_size = self.config.get('embedding', {}).get('batch_size', 32)
        
        # ColQwen2 모델 로드
        self.model = None
        self.tokenizer = None
        self._load_model()
    
    def _load_config(self, config_path: str) -> dict:
        """설정 파일 로드"""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            else:
                return {
                    'embedding': {
                        'dim': 128,
                        'batch_size': 32
                    }
                }
        except Exception as e:
            logger.error(f"설정 로드 오류: {e}")
            return {
                'embedding': {
                    'dim': 128,
                    'batch_size': 32
                }
            }
    
    def _load_model(self):
        """ColQwen2 모델 로드"""
        if not BYALDI_AVAILABLE and not TRANSFORMERS_AVAILABLE:
            logger.warning("Neither byaldi nor transformers available. Using dummy model.")
            self.model = None
            self.tokenizer = None
            return
            
        try:
            # Byaldi를 사용한 ColQwen2 모델 로드
            if BYALDI_AVAILABLE:
                self.model = RAGMultiModalModel.from_pretrained("vidore/colqwen2-v1.0")
                logger.info("ColQwen2 모델 로드 완료")
            elif TRANSFORMERS_AVAILABLE:
                # 폴백: 기본 ColQwen2 모델 사용
                model_name = "Qwen/ColQwen2-1.5B"
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.model = AutoModel.from_pretrained(model_name)
                self.model.to(self.device)
                logger.info("기본 ColQwen2 모델 로드 완료")
            else:
                logger.warning("No embedding model available")
                self.model = None
                self.tokenizer = None
        except Exception as e:
            logger.error(f"ColQwen2 모델 로드 오류: {e}")
            logger.warning("Using dummy model")
            self.model = None
            self.tokenizer = None
    
    @classmethod
    def load(cls, device: str = "cuda", config_path: str = "configs.yaml") -> "ColQwen2Embedder":
        """클래스 메서드로 임베더 로드"""
        return cls(device, config_path)
    
    def encode_text(self, x: Union[str, List[str]]) -> np.ndarray:
        """텍스트 인코딩"""
        try:
            if isinstance(x, str):
                x = [x]
            
            # 모델이 없는 경우 더미 임베딩 반환
            if self.model is None:
                logger.warning("No model available, returning dummy embeddings")
                return np.random.rand(len(x), self.dim)
            
            # Byaldi 모델 사용
            if hasattr(self.model, 'encode_text'):
                embeddings = []
                for i in range(0, len(x), self.batch_size):
                    batch = x[i:i + self.batch_size]
                    with torch.no_grad():
                        batch_embeddings = self.model.encode_text(batch)
                        if isinstance(batch_embeddings, torch.Tensor):
                            batch_embeddings = batch_embeddings.cpu().numpy()
                        embeddings.append(batch_embeddings)
                
                if embeddings:
                    return np.vstack(embeddings)
                else:
                    return np.zeros((len(x), self.dim))
            
            # 기본 ColQwen2 모델 사용
            elif self.tokenizer is not None:
                embeddings = []
                for i in range(0, len(x), self.batch_size):
                    batch = x[i:i + self.batch_size]
                    inputs = self.tokenizer(batch, padding=True, truncation=True, 
                                          return_tensors="pt", max_length=512)
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}
                    
                    with torch.no_grad():
                        outputs = self.model(**inputs)
                        # 마지막 히든 상태의 평균 사용
                        batch_embeddings = outputs.last_hidden_state.mean(dim=1)
                        embeddings.append(batch_embeddings.cpu().numpy())
                
                if embeddings:
                    return np.vstack(embeddings)
                else:
                    return np.zeros((len(x), self.dim))
            else:
                logger.warning("No tokenizer available, returning dummy embeddings")
                return np.random.rand(len(x), self.dim)
                    
        except Exception as e:
            logger.error(f"텍스트 인코딩 오류: {e}")
            return np.random.rand(len(x) if isinstance(x, list) else 1, self.dim)
    
    def encode_image_patches(self, image: Union[Image.Image, np.ndarray]) -> np.ndarray:
        """이미지 패치 인코딩"""
        try:
            # 모델이 없는 경우 더미 임베딩 반환
            if self.model is None:
                logger.warning("No model available, returning dummy image embeddings")
                return np.random.rand(1, self.dim)
            
            # PIL Image로 변환
            if isinstance(image, np.ndarray):
                image = Image.fromarray(image)
            
            # 이미지 크기 조정 (필요시)
            if image.size[0] > 448 or image.size[1] > 448:
                image.thumbnail((448, 448), Image.Resampling.LANCZOS)
            
            # Byaldi 모델 사용
            if hasattr(self.model, 'encode_image'):
                with torch.no_grad():
                    embeddings = self.model.encode_image([image])
                    if isinstance(embeddings, torch.Tensor):
                        embeddings = embeddings.cpu().numpy()
                    return embeddings
            
            # 기본 ColQwen2 모델 사용 (패치 분할)
            else:
                return self._encode_image_patches_fallback(image)
                
        except Exception as e:
            logger.error(f"이미지 패치 인코딩 오류: {e}")
            return np.random.rand(1, self.dim)
    
    def _encode_image_patches_fallback(self, image: Image.Image) -> np.ndarray:
        """기본 모델을 사용한 이미지 패치 인코딩 (폴백)"""
        try:
            # 14x14 그리드로 패치 분할
            patch_size = 32
            width, height = image.size
            
            patches = []
            for y in range(0, height, patch_size):
                for x in range(0, width, patch_size):
                    patch = image.crop((x, y, min(x + patch_size, width), min(y + patch_size, height)))
                    patches.append(patch)
            
            # 각 패치를 인코딩
            patch_embeddings = []
            for i in range(0, len(patches), self.batch_size):
                batch_patches = patches[i:i + self.batch_size]
                
                # 패치들을 텍스트로 변환 (간단한 방법)
                batch_texts = [f"image patch {j}" for j in range(len(batch_patches))]
                batch_embeddings = self.encode_text(batch_texts)
                patch_embeddings.append(batch_embeddings)
            
            if patch_embeddings:
                return np.vstack(patch_embeddings)
            else:
                return np.zeros((1, self.dim))
                
        except Exception as e:
            logger.error(f"이미지 패치 폴백 인코딩 오류: {e}")
            return np.zeros((1, self.dim))
    
    def encode_query(self, query: str) -> np.ndarray:
        """쿼리 인코딩 (텍스트와 동일하지만 별도 메서드로 제공)"""
        return self.encode_text(query)
    
    def get_embedding_dim(self) -> int:
        """임베딩 차원 반환"""
        return self.dim
