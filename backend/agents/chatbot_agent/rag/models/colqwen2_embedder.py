import os
import yaml
from typing import List, Union
import numpy as np
import torch
from PIL import Image
import logging

# 필요한 라이브러리 임포트
try:
    from transformers.utils.import_utils import is_flash_attn_2_available
    from colpali_engine.models import ColQwen2, ColQwen2Processor
    COLPALI_AVAILABLE = True
except ImportError:
    COLPALI_AVAILABLE = False
    # colpali-engine이 없을 경우를 대비한 가짜 클래스 정의
    class ColQwen2: pass
    class ColQwen2Processor: pass
    def is_flash_attn_2_available(): return False


logger = logging.getLogger(__name__)

class ColQwen2Embedder:
    """ColQwen2 기반 멀티모달 임베더 (colpali-engine 사용)"""
    
    def __init__(self, model_name: str = "vidore/colqwen2-v1.0", device: str = "cuda", config_path: str = "configs.yaml"):
        if not COLPALI_AVAILABLE:
            raise ImportError("ColQwen2Embedder를 사용하려면 'colpali-engine'을 설치해야 합니다. pip install git+https://github.com/illuin-tech/colpali")

        self.device = device if torch.cuda.is_available() else "cpu"
        self.config = self._load_config(config_path)
        self.dim = self.config.get('embedding', {}).get('dim', 128)
        self.batch_size = self.config.get('embedding', {}).get('batch_size', 32)
        
        self.model_name = model_name
        self.model = None
        self.processor = None
        self._load_model()
    
    def _load_config(self, config_path: str) -> dict:
        """설정 파일 로드"""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            return {}
        except Exception as e:
            logger.error(f"설정 로드 오류: {e}")
            return {}

    def _load_model(self):
        """ColQwen2 모델과 프로세서를 로드"""
        try:
            logger.info(f"'{self.model_name}' 모델 로딩 중...")
            
            # 성능 최적화를 위한 설정
            attn_implementation = "flash_attention_2" if is_flash_attn_2_available() else "sdpa"

            self.processor = ColQwen2Processor.from_pretrained(self.model_name)
            self.model = ColQwen2.from_pretrained(
                self.model_name,
                torch_dtype=torch.bfloat16,
                device_map=self.device,
                attn_implementation=attn_implementation,
            ).eval()
            
            logger.info("✅ ColQwen2 모델 및 프로세서 로드 완료")

        except Exception as e:
            logger.error(f"ColQwen2 모델 로드 오류: {e}")
            logger.warning("모델이 로드되지 않았습니다. 더미 임베딩이 반환됩니다.")
            self.model = None
            self.processor = None
            
    def encode_text(self, texts: List[str]) -> np.ndarray:
        """텍스트 목록을 인코딩하여 각 텍스트에 대한 '하나의' 평균 임베딩 벡터 목록을 반환"""
        if self.model is None or self.processor is None:
            logger.error("모델이 로드되지 않았습니다. ColQwen2 모델을 먼저 로드해주세요.")
            raise RuntimeError("ColQwen2 모델이 로드되지 않았습니다.")

        all_avg_embeddings = []
        try:
            for i in range(0, len(texts), self.batch_size):
                batch_texts = texts[i:i + self.batch_size]
                processed_inputs = self.processor.process_queries(batch_texts).to(self.device)

                with torch.no_grad():
                    # multi-vector embeddings (batch_size, num_tokens, dim)
                    multi_vector_embeddings = self.model(**processed_inputs)

                # 배치 내 각 항목에 대해 평균 벡터 계산
                # (batch_size, dim)
                avg_embeddings = torch.mean(multi_vector_embeddings, dim=1)
                all_avg_embeddings.append(avg_embeddings.cpu().float().numpy())

            if not all_avg_embeddings:
                return np.zeros((0, self.dim), dtype=np.float32)

            return np.vstack(all_avg_embeddings)

        except Exception as e:
            logger.error(f"텍스트 인코딩 오류: {e}")
            raise RuntimeError(f"텍스트 인코딩 실패: {e}")
    
    def encode_images(self, images: List[Union[Image.Image, np.ndarray]]) -> np.ndarray:
        """이미지 목록을 인코딩하여 각 이미지에 대한 '하나의' 평균 임베딩 벡터 목록을 반환"""
        if self.model is None or self.processor is None:
            logger.error("모델이 로드되지 않았습니다. ColQwen2 모델을 먼저 로드해주세요.")
            raise RuntimeError("ColQwen2 모델이 로드되지 않았습니다.")

        pil_images = [Image.fromarray(img) if isinstance(img, np.ndarray) else img for img in images]

        all_avg_embeddings = []
        try:
            for i in range(0, len(pil_images), self.batch_size):
                batch_images = pil_images[i:i + self.batch_size]
                processed_inputs = self.processor.process_images(batch_images).to(self.device)

                with torch.no_grad():
                    multi_vector_embeddings = self.model(**processed_inputs)

                avg_embeddings = torch.mean(multi_vector_embeddings, dim=1)
                all_avg_embeddings.append(avg_embeddings.cpu().float().numpy())

            if not all_avg_embeddings:
                return np.zeros((0, self.dim), dtype=np.float32)

            return np.vstack(all_avg_embeddings)

        except Exception as e:
            logger.error(f"이미지 인코딩 오류: {e}")
            raise RuntimeError(f"이미지 인코딩 실패: {e}")
    
    def encode_query(self, query: str) -> np.ndarray:
        multi_vector_embeddings = self.encode_text([query])
        logger.debug(f"multi_vector_embeddings shape: {multi_vector_embeddings.shape}")
        if multi_vector_embeddings.ndim == 3 and multi_vector_embeddings.shape[0] == 1:
            avg_embedding = np.mean(multi_vector_embeddings[0], axis=0)
            logger.debug(f"avg_embedding shape: {avg_embedding.shape}")
            return avg_embedding

        # 예외적인 경우, 원래 결과 반환
        return multi_vector_embeddings
    
    def get_embedding_dim(self) -> int:
        """임베딩 차원 반환"""
        return self.dim
    
    def encode_text_batch(self, texts: List[str], batch_size: int = None) -> np.ndarray:
        """텍스트 목록을 배치로 인코딩 (성능 최적화)"""
        if batch_size is None:
            batch_size = self.batch_size
        
        if self.model is None or self.processor is None:
            logger.error("모델이 로드되지 않았습니다. ColQwen2 모델을 먼저 로드해주세요.")
            raise RuntimeError("ColQwen2 모델이 로드되지 않았습니다.")

        all_avg_embeddings = []
        try:
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                processed_inputs = self.processor.process_queries(batch_texts).to(self.device)

                with torch.no_grad():
                    # multi-vector embeddings (batch_size, num_tokens, dim)
                    multi_vector_embeddings = self.model(**processed_inputs)

                # 배치 내 각 항목에 대해 평균 벡터 계산
                # (batch_size, dim)
                avg_embeddings = torch.mean(multi_vector_embeddings, dim=1)
                all_avg_embeddings.append(avg_embeddings.cpu().float().numpy())

            if not all_avg_embeddings:
                return np.zeros((0, self.dim), dtype=np.float32)

            return np.vstack(all_avg_embeddings)

        except Exception as e:
            logger.error(f"텍스트 배치 인코딩 오류: {e}")
            raise RuntimeError(f"텍스트 배치 인코딩 실패: {e}")
    
    def encode_image_batch(self, images: List[Image.Image], batch_size: int = None) -> np.ndarray:
        """이미지 목록을 배치로 인코딩 (성능 최적화)"""
        if batch_size is None:
            batch_size = self.batch_size
        
        if self.model is None or self.processor is None:
            logger.error("모델이 로드되지 않았습니다. ColQwen2 모델을 먼저 로드해주세요.")
            raise RuntimeError("ColQwen2 모델이 로드되지 않았습니다.")

        all_avg_embeddings = []
        try:
            for i in range(0, len(images), batch_size):
                batch_images = images[i:i + batch_size]
                processed_inputs = self.processor.process_images(batch_images).to(self.device)

                with torch.no_grad():
                    multi_vector_embeddings = self.model(**processed_inputs)

                avg_embeddings = torch.mean(multi_vector_embeddings, dim=1)
                all_avg_embeddings.append(avg_embeddings.cpu().float().numpy())

            if not all_avg_embeddings:
                return np.zeros((0, self.dim), dtype=np.float32)

            return np.vstack(all_avg_embeddings)

        except Exception as e:
            logger.error(f"이미지 배치 인코딩 오류: {e}")
            raise RuntimeError(f"이미지 배치 인코딩 실패: {e}")
    
    def encode_image_patches(self, image: Union[Image.Image, np.ndarray]) -> np.ndarray:
        """단일 이미지를 패치 단위로 인코딩하여 여러 임베딩 벡터를 반환"""
        if self.model is None or self.processor is None:
            logger.error("모델이 로드되지 않았습니다. ColQwen2 모델을 먼저 로드해주세요.")
            raise RuntimeError("ColQwen2 모델이 로드되지 않았습니다.")

        try:
            # PIL Image로 변환
            if isinstance(image, np.ndarray):
                pil_image = Image.fromarray(image)
            else:
                pil_image = image

            # 이미지를 패치로 분할 (예: 2x2 = 4개 패치)
            width, height = pil_image.size
            patch_size = min(width, height) // 2  # 간단한 패치 크기 계산
            
            patches = []
            for i in range(0, height, patch_size):
                for j in range(0, width, patch_size):
                    # 패치 추출
                    patch = pil_image.crop((j, i, min(j + patch_size, width), min(i + patch_size, height)))
                    patches.append(patch)
            
            if not patches:
                # 패치가 없으면 전체 이미지를 하나의 패치로 처리
                patches = [pil_image]

            # 패치들을 인코딩
            processed_inputs = self.processor.process_images(patches).to(self.device)

            with torch.no_grad():
                # multi-vector embeddings (num_patches, num_tokens, dim)
                multi_vector_embeddings = self.model(**processed_inputs)

            # 각 패치에 대해 평균 벡터 계산
            # (num_patches, dim)
            avg_embeddings = torch.mean(multi_vector_embeddings, dim=1)
            
            return avg_embeddings.cpu().float().numpy()

        except Exception as e:
            logger.error(f"이미지 패치 인코딩 오류: {e}")
            raise RuntimeError(f"이미지 패치 인코딩 실패: {e}")