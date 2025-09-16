#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# 현재 스크립트의 상위 디렉토리(backend)를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent.absolute()
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import time
import json
import sqlite3
import psutil
import platform
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import asyncio
import plistlib
import aiofiles
try:
    import winreg  # Windows only
except ImportError:
    winreg = None  # macOS/Linux에서는 None으로 설정
import subprocess
import numpy as np
import hashlib
try:
    from PIL import ImageGrab  # Windows/macOS with PIL support
except ImportError:
    ImageGrab = None  # Fallback for systems without PIL ImageGrab support

from config.settings import settings

# RAG 시스템 연동을 위한 import
from .repository import Repository
from .sqlite_meta import SQLiteMeta
from agents.chatbot_agent.rag.models.colqwen2_embedder import ColQwen2Embedder   

class FileCollector:
    """사용자 드라이브의 파일들을 수집하는 클래스"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.sqlite_meta = SQLiteMeta()
        
        # 수집할 파일 확장자 목록 (허용 리스트)
        self.supported_extensions = {
            'document': ['.txt', '.doc', '.docx', '.pdf', '.hwp', '.md'],
            'spreadsheet': ['.xls', '.xlsx', '.csv', '.ods'],
            'presentation': ['.ppt', '.pptx', '.odp'],
            'code': ['.py', '.js', '.html', '.css', '.java', '.cpp'],
        }
        
        # 💡 허용할 확장자 목록을 하나의 세트(set)로 통합 (효율적인 탐색을 위해)
        self.allowed_extensions = set()
        for extensions in self.supported_extensions.values():
            self.allowed_extensions.update(extensions)
            
        # 파일 해시 캐시 (중복 방지용)
        self.file_hash_cache = {}
        
    def get_file_category(self, file_path: str) -> str:
        """파일 확장자를 기반으로 카테고리를 결정합니다."""
        ext = Path(file_path).suffix.lower()
        
        for category, extensions in self.supported_extensions.items():
            if ext in extensions:
                return category
        return 'other'
    
    def should_skip_directory(self, dir_path: str) -> bool:
        """수집하지 않을 디렉토리를 판단합니다."""
        skip_patterns = [
            'Windows', 'Program Files', 'Program Files (x86)', 
            '$Recycle.Bin', 'System Volume Information', '.git',
            'node_modules', '__pycache__', '.vscode', '.idea',
            'AppData', 'Temp', 'tmp', 'ProgramData', 'Recovery',
            'Boot', 'EFI', 'MSOCache'
        ]
        
        path_parts = Path(dir_path).parts
        return any(part in skip_patterns for part in path_parts)
    
    # ❌ 기존의 복잡했던 should_skip_file 메서드는 삭제합니다.

    def calculate_file_hash(self, file_path: str) -> str:
        """파일의 해시값을 계산합니다."""
        try:
            if os.path.getsize(file_path) > 100 * 1024 * 1024:  # 100MB
                return f"large_file_{os.path.getsize(file_path)}"
            
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                chunk = f.read(1024 * 1024) # 1MB만 읽어 해시 계산
                hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            # print(f"파일 해시 계산 오류 {file_path}: {e}") # 로그 최소화
            return f"error_{int(time.time())}"
    
    def is_file_duplicate(self, file_path: str, file_hash: str) -> bool:
        """파일이 중복인지 확인합니다."""
        try:
            return self.sqlite_meta.is_file_hash_exists(file_hash)
        except Exception as e:
            print(f"중복 체크 오류 {file_path}: {e}")
            return False
    
    def is_file_modified(self, file_path: str, last_modified: datetime) -> bool:
        """파일이 수정되었는지 확인합니다."""
        try:
            stored_modified = self.sqlite_meta.get_file_last_modified(file_path)
            if stored_modified is None:
                return True
            return last_modified > stored_modified
        except Exception as e:
            print(f"파일 수정 체크 오류 {file_path}: {e}")
            return True
    
    def get_c_drive_folders(self) -> List[Dict[str, Any]]:
        print("get_c_drive_folders 메서드 시작")
        folders = []
        base_path = "C:\\Users\\choisunwoo\\Desktop"
        
        try:
            print(f"기준 경로: {base_path}")
            
            # 기준 경로가 존재하는지 확인
            if not os.path.exists(base_path):
                print(f"기준 경로가 존재하지 않습니다: {base_path}")
                return folders
            
            items = os.listdir(base_path)
            print(f"기준 경로 항목 개수: {len(items)}")
            
            for item in items:
                item_path = os.path.join(base_path, item)
                print(f"확인 중: {item_path}")
                
                if os.path.isdir(item_path):
                    print(f"  - 디렉토리임: {item}")
                    if not self.should_skip_directory(item_path):
                        print(f"  - 스킵하지 않음: {item}")
                        # 폴더 정보 수집
                        try:
                            stat = os.stat(item_path)
                            folder_info = {
                                'name': item,
                                'path': item_path,
                                'created_date': datetime.fromtimestamp(stat.st_ctime),
                                'modified_date': datetime.fromtimestamp(stat.st_mtime),
                                'size': self._get_folder_size(item_path)
                            }
                            folders.append(folder_info)
                            print(f"  - 추가됨: {item}")
                        except (PermissionError, OSError) as e:
                            # 접근 권한이 없는 폴더는 건너뛰기
                            print(f"  - 접근 권한 없음: {item} - {e}")
                            continue
                    else:
                        print(f"  - 스킵됨: {item}")
                else:
                    print(f"  - 파일임: {item}")
                        
        except Exception as e:
            print(f"폴더 목록 조회 오류: {e}")
            import traceback
            traceback.print_exc()
            
        # 이름순으로 정렬
        folders.sort(key=lambda x: x['name'].lower())
        print(f"최종 폴더 개수: {len(folders)}")
        return folders
    
    def _get_folder_size(self, folder_path: str) -> int:
        """폴더의 대략적인 크기를 계산합니다."""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(folder_path):
                for filename in filenames:
                    try:
                        filepath = os.path.join(dirpath, filename)
                        total_size += os.path.getsize(filepath)
                    except (OSError, FileNotFoundError):
                        continue
        except Exception:
            pass
        return total_size

    def _collect_files_from_selected_folders(self, selected_folders: List[str], incremental: bool = True, manager: Optional['DataCollectionManager'] = None) -> List[Dict[str, Any]]:
        """선택된 폴더들에서만 파일을 수집합니다."""
        collected_files = []
        total_folders = len(selected_folders)
        processed_folders = 0
        
        last_update_time = time.time()
        update_interval = 0.1
        
        for folder_path in selected_folders:
            if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
                print(f"폴더가 존재하지 않거나 접근할 수 없습니다: {folder_path}")
                continue
                
            try:
                if manager:
                    processed_folders += 1
                    progress = (processed_folders / total_folders) * 80.0
                    manager.progress = progress
                    manager.progress_message = f"📁 스캔 중: {folder_path}"
                
                for root, dirs, files in os.walk(folder_path):
                    # 스킵할 디렉토리 필터링
                    dirs[:] = [d for d in dirs if not self.should_skip_directory(os.path.join(root, d))]
                    
                    for file in files:
                        if manager:
                            current_time = time.time()
                            if current_time - last_update_time > update_interval:
                                folder_scan_message = manager.progress_message.split(' | ')[0]
                                manager.progress_message = f"{folder_scan_message} | 🔍 {file[:50]}"
                                last_update_time = current_time

                        try:
                            file_path = os.path.join(root, file)
                            
                            # 허용된 확장자인지 확인
                            file_ext = Path(file_path).suffix.lower()
                            if file_ext not in self.allowed_extensions:
                                continue
                            
                            stat = os.stat(file_path)
                            modified_date = datetime.fromtimestamp(stat.st_mtime)
                            
                            if incremental and not self.is_file_modified(file_path, modified_date):
                                continue
                            
                            file_hash = self.calculate_file_hash(file_path)
                            
                            if self.is_file_duplicate(file_path, file_hash):
                                continue
                            
                            file_info = {
                                'user_id': self.user_id,
                                'file_path': file_path,
                                'file_name': file,
                                'file_size': stat.st_size,
                                'file_type': file_ext,
                                'file_category': self.get_file_category(file_path),
                                'file_hash': file_hash,
                                'created_date': datetime.fromtimestamp(stat.st_ctime),
                                'modified_date': modified_date,
                                'accessed_date': datetime.fromtimestamp(stat.st_atime),
                                'discovered_at': datetime.utcnow()
                            }
                            
                            collected_files.append(file_info)
                            
                        except (PermissionError, OSError):
                            continue
                        except Exception as e:
                            print(f"파일 처리 중 오류 {file_path}: {e}")
                            continue
                            
            except Exception as e:
                print(f"폴더 스캔 오류 {folder_path}: {e}")
                continue
                
        return collected_files

    def collect_files_from_drive(self, drive_path: str = "C:\\", incremental: bool = True, manager: Optional['DataCollectionManager'] = None, selected_folders: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """지정된 드라이브에서 파일들을 수집합니다."""
        collected_files = []
        
        # 선택된 폴더가 있으면 해당 폴더들만 스캔
        if selected_folders:
            return self._collect_files_from_selected_folders(selected_folders, incremental, manager)
        
        # 기존 로직: 전체 드라이브 스캔
        top_level_dirs = []
        total_dirs = 1
        processed_dirs = 0
        if manager and not incremental:
            try:
                top_level_dirs = [d for d in os.listdir(drive_path) if os.path.isdir(os.path.join(drive_path, d)) and not self.should_skip_directory(d)]
                total_dirs = len(top_level_dirs)
            except Exception as e:
                print(f"최상위 디렉토리 목록 생성 오류: {e}")
                top_level_dirs = []
                total_dirs = 1

        last_update_time = time.time()
        update_interval = 0.1

        try:
            for root, dirs, files in os.walk(drive_path):
                if manager and not incremental and total_dirs > 0 and top_level_dirs:
                    try:
                        current_top_dir = root.split(os.sep)[1] if len(root.split(os.sep)) > 1 else ""
                        if current_top_dir and current_top_dir in top_level_dirs:
                            current_index = top_level_dirs.index(current_top_dir)
                            if current_index >= processed_dirs:
                                processed_dirs = current_index + 1
                                progress = (processed_dirs / total_dirs) * 80.0
                                manager.progress = progress
                                manager.progress_message = f"📁 스캔 중: {os.path.join(drive_path, current_top_dir)}"
                    except Exception:
                        pass

                dirs[:] = [d for d in dirs if not self.should_skip_directory(os.path.join(root, d))]
                
                for file in files:
                    if manager:
                        current_time = time.time()
                        if current_time - last_update_time > update_interval:
                            dir_scan_message = manager.progress_message.split(' | ')[0]
                            manager.progress_message = f"{dir_scan_message} | 🔍 {file[:50]}"
                            last_update_time = current_time

                    try:
                        file_path = os.path.join(root, file)
                        
                        # ✅ 허용된 확장자인지 먼저 확인하는 방식으로 변경
                        file_ext = Path(file_path).suffix.lower()
                        if file_ext not in self.allowed_extensions:
                            continue
                        
                        stat = os.stat(file_path)
                        modified_date = datetime.fromtimestamp(stat.st_mtime)
                        
                        if incremental and not self.is_file_modified(file_path, modified_date):
                            continue
                        
                        file_hash = self.calculate_file_hash(file_path)
                        
                        if self.is_file_duplicate(file_path, file_hash):
                            continue
                        
                        file_info = {
                            'user_id': self.user_id,
                            'file_path': file_path,
                            'file_name': file,
                            'file_size': stat.st_size,
                            'file_type': file_ext,
                            'file_category': self.get_file_category(file_path),
                            'file_hash': file_hash,
                            'created_date': datetime.fromtimestamp(stat.st_ctime),
                            'modified_date': modified_date,
                            'accessed_date': datetime.fromtimestamp(stat.st_atime),
                            'discovered_at': datetime.utcnow()
                        }
                        
                        collected_files.append(file_info)
                        
                    except (PermissionError, OSError):
                        continue
                    except Exception as e:
                        print(f"파일 처리 중 오류 {file_path}: {e}")
                        continue
                        
        except Exception as e:
            print(f"드라이브 스캔 오류: {e}")
            
        return collected_files

    # ... (FileCollector의 나머지 메서드들은 이전과 동일) ...
    def save_files_to_db(self, files: List[Dict[str, Any]]) -> int:
        """수집된 파일들을 데이터베이스에 배치 저장하고 RAG 시스템에 인덱싱합니다."""
        if not files:
            return 0
        
        saved_count = 0
        
        # RAG 시스템 초기화 (한 번만)
        repo = None
        embedder = None
        try:
            repo = Repository()
            embedder = ColQwen2Embedder()
            print("✅ RAG 시스템 초기화 완료")
        except Exception as e:
            print(f"⚠️ RAG 시스템 초기화 실패, SQLite만 저장: {e}")
        
        # 배치 처리를 위한 데이터 준비
        batch_size = 50  # 배치 크기 설정
        text_chunks_for_embedding = []
        image_files_for_embedding = []
        file_metadata_batch = []
        
        # 1단계: SQLite 배치 저장
        print(f"💾 {len(files)}개 파일을 SQLite에 배치 저장 중...")
        try:
            # 트랜잭션 시작
            self.sqlite_meta.conn.execute("BEGIN TRANSACTION")
            
            for file_info in files:
                try:
                    success = self.sqlite_meta.insert_collected_file(file_info)
                    if success:
                        saved_count += 1
                        file_metadata_batch.append(file_info)
                        
                        # RAG 인덱싱용 데이터 준비
                        if repo and embedder:
                            file_category = file_info['file_category']
                            if file_category in ['document', 'spreadsheet', 'presentation', 'code']:
                                text_chunks_for_embedding.append(file_info)
                            elif file_category == 'image':
                                image_files_for_embedding.append(file_info)
                                
                except Exception as e:
                    print(f"파일 저장 오류 {file_info['file_path']}: {e}")
                    continue
            
            # 트랜잭션 커밋
            self.sqlite_meta.conn.commit()
            print(f"✅ SQLite 배치 저장 완료: {saved_count}개 파일")
            
        except Exception as e:
            self.sqlite_meta.conn.rollback()
            print(f"❌ SQLite 배치 저장 실패: {e}")
            return 0
        
        # 2단계: RAG 시스템 배치 인덱싱
        if repo and embedder and (text_chunks_for_embedding or image_files_for_embedding):
            print(f"🔍 RAG 시스템 배치 인덱싱 시작...")
            
            # 텍스트 파일 배치 처리
            if text_chunks_for_embedding:
                self._batch_index_text_files(text_chunks_for_embedding, repo, embedder, batch_size)
            
            # 이미지 파일 배치 처리
            if image_files_for_embedding:
                self._batch_index_image_files(image_files_for_embedding, repo, embedder, batch_size)
            
            print("✅ RAG 시스템 배치 인덱싱 완료")
        
        return saved_count

    def _batch_index_text_files(self, text_files: List[Dict[str, Any]], repo: Repository, embedder: ColQwen2Embedder, batch_size: int):
        """텍스트 파일들을 배치로 인덱싱"""
        try:
            all_chunks = []
            all_metas = []
            all_doc_ids = []
            
            # 모든 텍스트 파일의 청크 수집
            for file_info in text_files:
                try:
                    file_path = file_info['file_path']
                    content = self._extract_text_content(file_path)
                    if not content:
                        continue
                    
                    chunks = self._chunk_text(content, chunk_size=1000)
                    doc_id = f"file_{hash(file_path)}"
                    
                    for i, chunk in enumerate(chunks):
                        all_chunks.append(chunk)
                        all_metas.append({
                            'page': i + 1,
                            'snippet': chunk[:200] + "..." if len(chunk) > 200 else chunk,
                            'path': file_path,
                            'doc_id': doc_id,
                            'chunk_id': i
                        })
                        all_doc_ids.append(doc_id)
                        
                except Exception as e:
                    print(f"텍스트 파일 처리 오류 {file_info['file_path']}: {e}")
                    continue
            
            if not all_chunks:
                return
            
            # 배치로 임베딩 생성
            print(f"🧠 {len(all_chunks)}개 텍스트 청크 임베딩 생성 중...")
            vectors = embedder.encode_text_batch(all_chunks, batch_size=batch_size)
            
            # 배치로 Qdrant에 인덱싱
            print(f"💾 {len(vectors)}개 벡터를 Qdrant에 배치 저장 중...")
            repo.index_text_chunks_batch(all_doc_ids, vectors, all_metas, batch_size)
            
        except Exception as e:
            print(f"텍스트 파일 배치 인덱싱 오류: {e}")

    def _batch_index_image_files(self, image_files: List[Dict[str, Any]], repo: Repository, embedder: ColQwen2Embedder, batch_size: int):
        """이미지 파일들을 배치로 인덱싱"""
        try:
            all_images = []
            all_metas = []
            all_doc_ids = []
            
            # 모든 이미지 파일 수집
            for file_info in image_files:
                try:
                    file_path = file_info['file_path']
                    from PIL import Image
                    
                    image = Image.open(file_path)
                    doc_id = f"file_{hash(file_path)}"
                    
                    all_images.append(image)
                    all_metas.append({
                        'bbox': [0, 0, image.width, image.height],
                        'path': file_path,
                        'image_size': f"{image.width}x{image.height}",
                        'doc_id': doc_id,
                        'patch_id': 0
                    })
                    all_doc_ids.append(doc_id)
                    
                except Exception as e:
                    print(f"이미지 파일 처리 오류 {file_info['file_path']}: {e}")
                    continue
            
            if not all_images:
                return
            
            # 배치로 임베딩 생성
            print(f"🖼️ {len(all_images)}개 이미지 임베딩 생성 중...")
            vectors = embedder.encode_image_batch(all_images, batch_size=batch_size)
            
            # 배치로 Qdrant에 인덱싱
            print(f"💾 {len(vectors)}개 벡터를 Qdrant에 배치 저장 중...")
            repo.index_image_patches_batch(all_doc_ids, vectors, all_metas, batch_size)
            
        except Exception as e:
            print(f"이미지 파일 배치 인덱싱 오류: {e}")

    def _index_file_for_rag(self, file_info: Dict[str, Any], repo: Repository, embedder: ColQwen2Embedder):
        """파일을 RAG 시스템에 인덱싱"""
        try:
            file_path = file_info['file_path']
            file_category = file_info['file_category']
            
            # 1. SQLite 메타데이터에 저장
            doc_id = f"file_{hash(file_path)}"
            repo.sqlite.upsert_file(
                doc_id=doc_id,
                path=file_path,
                mime=self._get_mime_type(file_path),
                size=file_info['file_size'],
                created_at=int(file_info['created_date'].timestamp()),
                updated_at=int(file_info['modified_date'].timestamp()),
                accessed_at=int(file_info['accessed_date'].timestamp()),
                category=file_category,
                preview=self._get_file_preview(file_path)
            )
            
            # 2. 파일 타입에 따른 벡터화 및 인덱싱
            if file_category in ['document', 'spreadsheet', 'presentation', 'code']:
                # 텍스트 파일 처리
                self._index_text_file(file_path, doc_id, repo, embedder)
            elif file_category == 'image':
                # 이미지 파일 처리
                self._index_image_file(file_path, doc_id, repo, embedder)
                
        except Exception as e:
            print(f"RAG 인덱싱 오류 {file_path}: {e}")

    def _index_text_file(self, file_path: str, doc_id: str, repo: Repository, embedder: ColQwen2Embedder):
        """텍스트 파일을 RAG 시스템에 인덱싱"""
        try:
            # 파일 내용 읽기
            content = self._extract_text_content(file_path)
            if not content:
                return
            
            # 텍스트 청킹
            chunks = self._chunk_text(content, chunk_size=1000)
            
            for i, chunk in enumerate(chunks):
                # 텍스트 임베딩 생성
                vectors = embedder.encode_text(chunk)
                
                # 메타데이터 생성
                meta = {
                    'page': i + 1,
                    'snippet': chunk[:200] + "..." if len(chunk) > 200 else chunk,
                    'path': file_path
                }
                
                # Qdrant에 인덱싱
                repo.index_text_chunks(doc_id, vectors, [meta])
                
        except Exception as e:
            print(f"텍스트 파일 인덱싱 오류 {file_path}: {e}")

    def _index_image_file(self, file_path: str, doc_id: str, repo: Repository, embedder: ColQwen2Embedder):
        """이미지 파일을 RAG 시스템에 인덱싱"""
        try:
            from PIL import Image
            
            # 이미지 로드
            image = Image.open(file_path)
            
            # 이미지 임베딩 생성
            vectors = embedder.encode_image_patches(image)
            
            # 메타데이터 생성
            meta = {
                'bbox': [0, 0, image.width, image.height],
                'path': file_path,
                'image_size': f"{image.width}x{image.height}"
            }
            
            # Qdrant에 인덱싱
            repo.index_image_patches(doc_id, vectors, [meta])
            
        except Exception as e:
            print(f"이미지 파일 인덱싱 오류 {file_path}: {e}")

    def _extract_text_content(self, file_path: str) -> str:
        """파일에서 텍스트 내용을 추출"""
        try:
            ext = Path(file_path).suffix.lower()
            
            # 텍스트 파일 직접 읽기
            if ext in ['.txt', '.py', '.js', '.html', '.css', '.md', '.json', '.xml', '.csv']:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            
            # PDF 파일 처리
            elif ext == '.pdf':
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as f:
                        pdf_reader = PyPDF2.PdfReader(f)
                        text = ""
                        for page in pdf_reader.pages:
                            text += page.extract_text() + "\n"
                        return text
                except ImportError:
                    print("PyPDF2가 설치되지 않았습니다. PDF 파일을 건너뜁니다.")
                    return ""
            
            # Word 문서 처리
            elif ext in ['.docx', '.doc']:
                try:
                    from docx import Document
                    doc = Document(file_path)
                    text = ""
                    for paragraph in doc.paragraphs:
                        text += paragraph.text + "\n"
                    return text
                except ImportError:
                    print("python-docx가 설치되지 않았습니다. Word 파일을 건너뜁니다.")
                    return ""
            
            # Excel 파일 처리
            elif ext in ['.xlsx', '.xls']:
                try:
                    import pandas as pd
                    df = pd.read_excel(file_path)
                    return df.to_string()
                except ImportError:
                    print("pandas가 설치되지 않았습니다. Excel 파일을 건너뜁니다.")
                    return ""
            
            return ""
            
        except Exception as e:
            print(f"텍스트 추출 오류 {file_path}: {e}")
            return ""

    def _chunk_text(self, text: str, chunk_size: int = 1000) -> List[str]:
        """텍스트를 청크로 분할"""
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size]
            if chunk.strip():
                chunks.append(chunk)
        return chunks

    def _get_mime_type(self, file_path: str) -> str:
        """파일의 MIME 타입을 반환"""
        import mimetypes
        return mimetypes.guess_type(file_path)[0] or 'application/octet-stream'

    def _get_file_preview(self, file_path: str) -> str:
        """파일 내용 미리보기 생성"""
        try:
            content = self._extract_text_content(file_path)
            if content:
                return content[:500] + "..." if len(content) > 500 else content
        except:
            pass
        return ""

# -----------------------------------------------------------------------------
# 아래의 다른 Collector 및 Manager 클래스들은 변경사항이 없습니다.
# -----------------------------------------------------------------------------

class BrowserHistoryCollector:
    # ... (변경 없음)
    """브라우저 사용 기록을 수집하는 클래스"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.sqlite_meta = SQLiteMeta()
        # 운영체제별 브라우저 경로 설정
        if platform.system() == "Windows":
            self.browser_paths = {
                'chrome': {
                    'path': os.path.expanduser('~\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\History'),
                    'name': 'Chrome'
                },
                'edge': {
                    'path': os.path.expanduser('~\\AppData\\Local\\Microsoft\\Edge\\User Data\\Default\\History'),
                    'name': 'Edge'
                }
            }
        elif platform.system() == "Darwin":  # macOS
            self.browser_paths = {
                'chrome': {
                    'path': os.path.expanduser('~/Library/Application Support/Google/Chrome/Default/History'),
                    'name': 'Chrome'
                },
                'edge': {
                    'path': os.path.expanduser('~/Library/Application Support/Microsoft Edge/Default/History'),
                    'name': 'Edge'
                },
                'safari': {
                    'path': os.path.expanduser('~/Library/Safari/History.db'),
                    'name': 'Safari'
                }
            }
        else:  # Linux
            self.browser_paths = {
                'chrome': {
                    'path': os.path.expanduser('~/.config/google-chrome/Default/History'),
                    'name': 'Chrome'
                },
                'firefox': {
                    'path': os.path.expanduser('~/.mozilla/firefox/*/places.sqlite'),
                    'name': 'Firefox'
                }
            }
        # 브라우저 히스토리 캐시 (중복 방지용)
        self.history_cache = set()
    
    def get_chrome_history(self, incremental: bool = True) -> List[Dict[str, Any]]:
        """Chrome 브라우저 히스토리를 수집합니다."""
        history_data = []
        
        try:
            chrome_path = self.browser_paths['chrome']['path']
            if not os.path.exists(chrome_path):
                return history_data
            
            # Chrome 히스토리 파일 복사 (사용 중인 파일이므로)
            import shutil
            temp_path = f"{chrome_path}_temp"
            shutil.copy2(chrome_path, temp_path)
            
            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()
            
            # 증분 수집을 위해 마지막 수집 시간 이후의 히스토리만 가져오기
            if incremental:
                last_collection_time = self.sqlite_meta.get_last_browser_collection_time(self.user_id, 'Chrome')
                if last_collection_time:
                    # Chrome 시간 형식으로 변환
                    chrome_timestamp = int((last_collection_time - datetime(1601, 1, 1)).total_seconds() * 1000000)
                    cursor.execute("""
                        SELECT url, title, visit_count, last_visit_time, typed_count
                        FROM urls 
                        WHERE last_visit_time > ?
                        ORDER BY last_visit_time DESC LIMIT 1000
                    """, (chrome_timestamp,))
                else:
                    cursor.execute("""
                        SELECT url, title, visit_count, last_visit_time, typed_count
                        FROM urls ORDER BY last_visit_time DESC LIMIT 1000
                    """)
            else:
                cursor.execute("""
                    SELECT url, title, visit_count, last_visit_time, typed_count
                    FROM urls ORDER BY last_visit_time DESC LIMIT 1000
                """)
            
            for row in cursor.fetchall():
                url, title, visit_count, last_visit_time, typed_count = row
                
                # Chrome 시간을 datetime으로 변환
                chrome_time = datetime(1601, 1, 1) + timedelta(microseconds=last_visit_time)
                
                # 중복 체크 (URL + 방문 시간 조합)
                history_key = f"{url}_{chrome_time.timestamp()}"
                if history_key in self.history_cache:
                    continue
                
                # 데이터베이스에서 중복 확인
                if self.sqlite_meta.is_browser_history_duplicate(self.user_id, url, chrome_time):
                    continue
                
                self.history_cache.add(history_key)
                
                history_data.append({
                    'user_id': self.user_id,
                    'browser_name': 'Chrome',
                    'browser_version': self.get_chrome_version(),
                    'url': url,
                    'title': title,
                    'visit_count': visit_count,
                    'visit_time': chrome_time,
                    'last_visit_time': chrome_time,
                    'page_transition': 'typed' if typed_count > 0 else 'link',
                    'recorded_at': datetime.utcnow()
                })
            
            conn.close()
            os.remove(temp_path)
            
        except Exception as e:
            print(f"Chrome 히스토리 수집 오류: {e}")
            
        return history_data
    
    def get_chrome_version(self) -> str:
        """Chrome 버전을 가져옵니다."""
        try:
            if platform.system() == "Windows" and winreg is not None:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                    r"Software\Google\Chrome\BLBeacon")
                version, _ = winreg.QueryValueEx(key, "version")
                return version
            elif platform.system() == "Darwin":  # macOS
                plist_path = "/Applications/Google Chrome.app/Contents/Info.plist"
                if os.path.exists(plist_path):
                    with open(plist_path, 'rb') as f:
                        plist_data = plistlib.load(f)
                        return plist_data.get('CFBundleShortVersionString', 'Unknown')
                else:
                    return "Chrome not installed"
            else:  # Linux
                try:
                    result = subprocess.run(['google-chrome', '--version'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return result.stdout.strip().split()[-1]
                except:
                    pass
                return "Unknown"
        except:
            return "Unknown"
    
    def get_edge_history(self, incremental: bool = True) -> List[Dict[str, Any]]:
        """Edge 브라우저 히스토리를 수집합니다."""
        history_data = []
        
        try:
            edge_path = self.browser_paths['edge']['path']
            if not os.path.exists(edge_path):
                return history_data
            
            # Edge 히스토리 파일 복사 (사용 중인 파일이므로)
            import shutil
            temp_path = f"{edge_path}_temp"
            shutil.copy2(edge_path, temp_path)
            
            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()
            
            # 증분 수집을 위해 마지막 수집 시간 이후의 히스토리만 가져오기
            if incremental:
                last_collection_time = self.sqlite_meta.get_last_browser_collection_time(self.user_id, 'Edge')
                if last_collection_time:
                    # Edge 시간 형식으로 변환 (Chrome과 동일한 형식)
                    edge_timestamp = int((last_collection_time - datetime(1601, 1, 1)).total_seconds() * 1000000)
                    cursor.execute("""
                        SELECT url, title, visit_count, last_visit_time, typed_count
                        FROM urls 
                        WHERE last_visit_time > ?
                        ORDER BY last_visit_time DESC LIMIT 1000
                    """, (edge_timestamp,))
                else:
                    cursor.execute("""
                        SELECT url, title, visit_count, last_visit_time, typed_count
                        FROM urls ORDER BY last_visit_time DESC LIMIT 1000
                    """)
            else:
                cursor.execute("""
                    SELECT url, title, visit_count, last_visit_time, typed_count
                    FROM urls ORDER BY last_visit_time DESC LIMIT 1000
                """)
            
            for row in cursor.fetchall():
                url, title, visit_count, last_visit_time, typed_count = row
                
                # Edge 시간을 datetime으로 변환 (Chrome과 동일한 형식)
                edge_time = datetime(1601, 1, 1) + timedelta(microseconds=last_visit_time)
                
                # 중복 체크 (URL + 방문 시간 조합)
                history_key = f"{url}_{edge_time.timestamp()}"
                if history_key in self.history_cache:
                    continue
                
                # 데이터베이스에서 중복 확인
                if self.sqlite_meta.is_browser_history_duplicate(self.user_id, url, edge_time):
                    continue
                
                self.history_cache.add(history_key)
                
                history_data.append({
                    'user_id': self.user_id,
                    'browser_name': 'Edge',
                    'browser_version': self.get_edge_version(),
                    'url': url,
                    'title': title,
                    'visit_count': visit_count,
                    'visit_time': edge_time,
                    'last_visit_time': edge_time,
                    'page_transition': 'typed' if typed_count > 0 else 'link',
                    'recorded_at': datetime.utcnow()
                })
            
            conn.close()
            os.remove(temp_path)
            
        except Exception as e:
            print(f"Edge 히스토리 수집 오류: {e}")
            
        return history_data
    
    def get_edge_version(self) -> str:
        """Edge 버전을 가져옵니다."""
        try:
            if platform.system() == "Windows" and winreg is not None:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                    r"Software\Microsoft\Edge\BLBeacon")
                version, _ = winreg.QueryValueEx(key, "version")
                return version
            elif platform.system() == "Darwin":  # macOS
                plist_path = "/Applications/Microsoft Edge.app/Contents/Info.plist"
                if os.path.exists(plist_path):
                    with open(plist_path, 'rb') as f:
                        plist_data = plistlib.load(f)
                        return plist_data.get('CFBundleShortVersionString', 'Unknown')
                else:
                    return "Edge not installed"
            else:  # Linux
                try:
                    result = subprocess.run(['microsoft-edge', '--version'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return result.stdout.strip().split()[-1]
                except:
                    pass
                return "Unknown"
        except:
            return "Unknown"
    
    def collect_all_browser_history(self, incremental: bool = True) -> List[Dict[str, Any]]:
        """모든 브라우저의 히스토리를 수집합니다."""
        all_history = []
        
        # Chrome 히스토리
        chrome_history = self.get_chrome_history(incremental)
        all_history.extend(chrome_history)
        
        # Edge 히스토리
        edge_history = self.get_edge_history(incremental)
        all_history.extend(edge_history)
        
        return all_history
    
    def save_browser_history_to_db(self, history_data: List[Dict[str, Any]]) -> int:
        """브라우저 히스토리를 데이터베이스에 저장하고 RAG 시스템에 인덱싱합니다."""
        saved_count = 0
        
        # RAG 시스템 초기화
        try:
            repo = Repository()
            embedder = ColQwen2Embedder()
        except Exception as e:
            print(f"RAG 시스템 초기화 오류: {e}")
            repo = None
            embedder = None
        
        for history_item in history_data:
            try:
                # 1. SQLite에 저장
                success = self.sqlite_meta.insert_collected_browser_history(history_item)
                
                if success:
                    saved_count += 1
                    
                    # 2. RAG 시스템에 인덱싱
                    if repo and embedder:
                        self._index_web_history_for_rag(history_item, repo, embedder)
                        
            except Exception as e:
                print(f"브라우저 히스토리 저장 오류: {e}")
                continue
            
        return saved_count

    def _index_web_history_for_rag(self, history_item: Dict[str, Any], repo: Repository, embedder: ColQwen2Embedder):
        """웹 히스토리를 RAG 시스템에 인덱싱"""
        try:
            url = history_item['url']
            title = history_item['title']
            visit_time = history_item['visit_time']
            
            # 1. SQLite 메타데이터에 저장
            doc_id = f"web_{hash(url + str(visit_time))}"
            repo.sqlite.insert_web_history(
                url=url,
                title=title,
                visited_at=int(visit_time.timestamp()),
                visit_count=history_item.get('visit_count', 1),
                transition=history_item.get('page_transition', 'link'),
                browser=history_item.get('browser_name', 'Unknown'),
                version=history_item.get('browser_version', 'Unknown'),
                domain=self._extract_domain(url),
                duration_sec=0,  # 기본값
                tab_title=title
            )
            
            # 2. 웹 페이지 내용을 텍스트로 변환하여 벡터화
            content = f"제목: {title}\nURL: {url}\n방문 시간: {visit_time}"
            
            # 텍스트 임베딩 생성
            vectors = embedder.encode_text(content)
            
            # 메타데이터 생성
            meta = {
                'url': url,
                'title': title,
                'visit_time': int(visit_time.timestamp()),
                'browser': history_item.get('browser_name', 'Unknown'),
                'domain': self._extract_domain(url)
            }
            
            # Qdrant에 인덱싱
            repo.index_text_chunks(doc_id, vectors, [meta])
            
        except Exception as e:
            print(f"웹 히스토리 RAG 인덱싱 오류: {e}")

    def _extract_domain(self, url: str) -> str:
        """URL에서 도메인을 추출"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except:
            return "unknown"

class ActiveApplicationCollector:
    # ... (변경 없음)
    """실행 중인 애플리케이션 정보를 수집하는 클래스"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.sqlite_meta = SQLiteMeta()
        self.app_categories = {
            'productivity': ['word', 'excel', 'powerpoint', 'outlook', 'notepad', 'wordpad'],
            'development': ['code', 'pycharm', 'intellij', 'eclipse', 'visual studio', 'sublime'],
            'browser': ['chrome', 'firefox', 'edge', 'safari', 'opera'],
            'entertainment': ['spotify', 'youtube', 'netflix', 'vlc', 'media player'],
            'communication': ['teams', 'zoom', 'skype', 'discord', 'slack'],
            'gaming': ['steam', 'origin', 'battle.net', 'epic games']
        }
    
    def get_app_category(self, app_name: str) -> str:
        """애플리케이션 이름을 기반으로 카테고리를 결정합니다."""
        app_lower = app_name.lower()
        
        for category, apps in self.app_categories.items():
            if any(app in app_lower for app in apps):
                return category
        return 'other'
    
    def collect_active_applications(self) -> List[Dict[str, Any]]:
        """현재 실행 중인 애플리케이션들을 수집합니다."""
        active_apps = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'cpu_percent', 'memory_info', 'create_time']):
                try:
                    proc_info = proc.info
                    
                    if proc_info['exe'] and os.path.exists(proc_info['exe']):
                        app_info = {
                            'user_id': self.user_id,
                            'app_name': proc_info['name'],
                            'app_path': proc_info['exe'],
                            'app_version': self.get_app_version(proc_info['exe']),
                            'app_category': self.get_app_category(proc_info['name']),
                            'start_time': datetime.fromtimestamp(proc_info['create_time']),
                            'end_time': None,  # 아직 실행 중
                            'duration': int(time.time() - proc_info['create_time']),
                            'cpu_usage': proc_info['cpu_percent'],
                            'memory_usage': proc_info['memory_info'].rss / 1024 / 1024,  # MB
                            'recorded_at': datetime.utcnow()
                        }
                        
                        active_apps.append(app_info)
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                    
        except Exception as e:
            print(f"활성 애플리케이션 수집 오류: {e}")
            
        return active_apps
    
    def get_app_version(self, exe_path: str) -> str:
        """실행 파일의 버전을 가져옵니다."""
        try:
            if platform.system() == "Windows":
                import win32api
                info = win32api.GetFileVersionInfo(exe_path, "\\")
                ms = info['FileVersionMS']
                ls = info['FileVersionLS']
                version = f"{win32api.HIWORD(ms)}.{win32api.LOWORD(ms)}.{win32api.HIWORD(ls)}.{win32api.LOWORD(ls)}"
                return version
            elif platform.system() == "Darwin":  # macOS
                return self._get_app_version_macos(exe_path)
            else:  # Linux
                return self._get_app_version_linux(exe_path)
        except:
            return "Unknown"
    
    def _get_app_version_macos(self, app_path: str) -> str:
        """macOS에서 앱 버전을 가져옵니다."""
        try:
            # .app 번들인 경우 Info.plist에서 버전 정보 추출
            if app_path.endswith('.app'):
                plist_path = os.path.join(app_path, 'Contents', 'Info.plist')
                if os.path.exists(plist_path):
                    with open(plist_path, 'rb') as f:
                        plist_data = plistlib.load(f)
                        return plist_data.get('CFBundleShortVersionString', 'Unknown')
            
            # 일반 실행파일인 경우 otool 명령어 사용
            try:
                result = subprocess.run(['otool', '-L', app_path], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    # 버전 정보 파싱 로직 (간단한 예시)
                    return "1.0.0"  # 실제로는 더 복잡한 파싱 필요
            except:
                pass
            
            return "Unknown"
        except:
            return "Unknown"
    
    def _get_app_version_linux(self, exe_path: str) -> str:
        """Linux에서 앱 버전을 가져옵니다."""
        try:
            # dpkg를 사용해서 패키지 버전 확인 (Debian/Ubuntu)
            try:
                result = subprocess.run(['dpkg', '-S', exe_path], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    package_name = result.stdout.split(':')[0]
                    version_result = subprocess.run(['dpkg', '-l', package_name], 
                                                  capture_output=True, text=True, timeout=5)
                    if version_result.returncode == 0:
                        lines = version_result.stdout.split('\n')
                        for line in lines:
                            if package_name in line:
                                parts = line.split()
                                if len(parts) >= 3:
                                    return parts[2]
            except:
                pass
            
            # rpm을 사용해서 패키지 버전 확인 (Red Hat/CentOS)
            try:
                result = subprocess.run(['rpm', '-qf', exe_path], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return result.stdout.strip()
            except:
                pass
            
            return "Unknown"
        except:
            return "Unknown"
    
    def save_active_apps_to_db(self, apps_data: List[Dict[str, Any]]) -> int:
        """활성 애플리케이션 정보를 데이터베이스에 저장합니다."""
        saved_count = 0
        
        for app_data in apps_data:
            try:
                # SQLite를 사용하여 저장
                if self.sqlite_meta.insert_collected_app(app_data):
                    saved_count += 1
                
            except Exception as e:
                print(f"활성 애플리케이션 저장 오류: {e}")
                continue
            
        return saved_count

class ScreenActivityCollector:
    # ... (변경 없음)
    """화면 활동을 수집하고 분석하는 클래스"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.sqlite_meta = SQLiteMeta()
        self.screenshot_dir = Path("uploads/screenshots")
        # 폴더가 존재하지 않을 때만 생성
        if not self.screenshot_dir.exists():
            self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        # LLM 초기화
        self.llm = self._initialize_llm()
    
    def _initialize_llm(self):
        """LLM을 초기화합니다."""
        try:
            if settings.GEMINI_API_KEY:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                return genai.GenerativeModel(settings.GEMINI_MODEL)
            else:
                return None
        except Exception as e:
            print(f"LLM 초기화 오류: {e}")
            return None
    
    def capture_screenshot(self) -> Optional[Tuple[bytes, str]]:
        """화면 스크린샷을 캡처합니다."""
        try:
            # macOS에서는 screencapture 명령어 사용
            if platform.system() == "Darwin":
                return self._capture_screenshot_macos()
            # Windows/Linux에서는 PIL ImageGrab 사용
            elif ImageGrab is not None:
                return self._capture_screenshot_pil()
            else:
                print("스크린샷 캡처 기능을 사용할 수 없습니다.")
                return None
        except Exception as e:
            print(f"스크린샷 캡처 오류: {e}")
            return None
    
    def _capture_screenshot_macos(self) -> Optional[Tuple[bytes, str]]:
        """macOS에서 screencapture 명령어를 사용해 스크린샷을 캡처합니다."""
        try:
            # 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{self.user_id}_{timestamp}.png"
            file_path = self.screenshot_dir / filename
            
            # screencapture 명령어로 스크린샷 캡처
            result = subprocess.run(['screencapture', '-x', str(file_path)], 
                                  capture_output=True, timeout=10)
            
            if result.returncode == 0 and os.path.exists(file_path):
                # 파일을 바이트로 읽기
                with open(file_path, 'rb') as f:
                    screenshot_data = f.read()
                return screenshot_data, str(file_path)
            else:
                print("screencapture 명령어 실행 실패")
                return None
        except Exception as e:
            print(f"macOS 스크린샷 캡처 오류: {e}")
            return None
    
    def _capture_screenshot_pil(self) -> Optional[Tuple[bytes, str]]:
        """PIL ImageGrab을 사용해 스크린샷을 캡처합니다."""
        try:
            # 스크린샷 캡처
            screenshot = ImageGrab.grab()
            
            # 파일명 생성 (예: screenshot_1_20241201_143022.png)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{self.user_id}_{timestamp}.png"
            file_path = self.screenshot_dir / filename
            
            # 이미지를 uploads/screenshots/ 디렉토리에 저장
            screenshot.save(file_path, 'PNG')
            
            # 바이너리 데이터 읽기
            with open(file_path, 'rb') as f:
                image_data = f.read()
            
            return image_data, str(file_path)
            
        except Exception as e:
            print(f"PIL 스크린샷 캡처 오류: {e}")
            return None
    
    async def analyze_screenshot_with_llm(self, image_data: bytes) -> Dict[str, Any]:
        """LLM을 사용하여 스크린샷을 분석합니다."""
        try:
            if not self.llm:
                return self._fallback_analysis()
            
            # 이미지를 base64로 인코딩
            import base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # LLM 프롬프트 생성
            prompt = f"""
다음 스크린샷을 분석하여 사용자가 현재 무엇을 하고 있는지 설명해주세요.

분석 결과는 다음과 같은 JSON 형식으로 제공해주세요:
{{
    "activity_description": "사용자가 현재 하고 있는 활동에 대한 상세한 설명",
    "activity_category": "작업, 브라우징, 엔터테인먼트, 개발, 통신 중 하나",
    "activity_confidence": 0.95,
    "detected_apps": ["감지된 애플리케이션 목록"],
    "detected_text": ["화면에서 감지된 주요 텍스트들"],
    "detected_objects": ["화면에서 감지된 주요 객체들"]
}}

스크린샷: data:image/png;base64,{image_base64}

JSON 응답만 제공해주세요:
"""
            
            # LLM 호출
            response = self.llm.generate_content(prompt)
            analysis_text = response.text
            
            # JSON 파싱
            import json
            import re
            
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                return analysis
            else:
                return self._fallback_analysis()
                
        except Exception as e:
            print(f"LLM 분석 오류: {e}")
            return self._fallback_analysis()
    
    def _fallback_analysis(self) -> Dict[str, Any]:
        """LLM이 없을 때의 기본 분석"""
        return {
            "activity_description": "스크린샷이 캡처되었습니다.",
            "activity_category": "unknown",
            "activity_confidence": 0.5,
            "detected_apps": [],
            "detected_text": [],
            "detected_objects": []
        }
    
    def save_screen_activity_to_db(self, screenshot_data: bytes, file_path: str, 
                                 analysis: Dict[str, Any]) -> bool:
        """화면 활동 정보를 데이터베이스에 저장하고 RAG 시스템에 인덱싱합니다."""
        try:
            # 화면 해상도 가져오기
            screen = ImageGrab.grab()
            resolution = f"{screen.width}x{screen.height}"
            
            # SQLite에 저장
            screenshot_info = {
                'user_id': self.user_id,
                'screenshot_path': file_path,
                'screenshot_data': screenshot_data,
                'activity_description': analysis.get('activity_description', ''),
                'activity_category': analysis.get('activity_category', ''),
                'activity_confidence': analysis.get('activity_confidence', 0.0),
                'detected_apps': analysis.get('detected_apps', []),
                'detected_text': analysis.get('detected_text', []),
                'detected_objects': analysis.get('detected_objects', []),
                'screen_resolution': resolution,
                'color_mode': 'light'
            }
            
            success = self.sqlite_meta.insert_collected_screenshot(screenshot_info)
            
            if success:
                # RAG 시스템에 인덱싱
                self._index_screen_activity_for_rag(screenshot_data, file_path, analysis)
            
            return success
            
        except Exception as e:
            print(f"화면 활동 저장 오류: {e}")
            return False

    def _index_screen_activity_for_rag(self, screenshot_data: bytes, file_path: str, analysis: Dict[str, Any]):
        """화면 활동을 RAG 시스템에 인덱싱"""
        try:
            # RAG 시스템 초기화
            repo = Repository()
            embedder = ColQwen2Embedder()
            
            # 1. SQLite 메타데이터에 저장
            doc_id = f"screen_{hash(file_path)}"
            repo.sqlite.insert_screenshot(
                doc_id=doc_id,
                path=file_path,
                captured_at=int(datetime.utcnow().timestamp()),
                app_name=analysis.get('detected_apps', ['Unknown'])[0] if analysis.get('detected_apps') else 'Unknown',
                window_title=analysis.get('activity_description', ''),
                hash=hashlib.md5(screenshot_data).hexdigest(),
                ocr="",  # OCR 결과가 있다면 여기에 추가
                gemini_desc=analysis.get('activity_description', ''),
                category=analysis.get('activity_category', 'unknown'),
                confidence=analysis.get('activity_confidence', 0.0)
            )
            
            # 2. 스크린샷 이미지 벡터화
            from PIL import Image
            import io
            
            # 바이너리 데이터를 PIL Image로 변환
            image = Image.open(io.BytesIO(screenshot_data))
            
            # 이미지 임베딩 생성
            vectors = embedder.encode_image_patches(image)
            
            # 메타데이터 생성
            meta = {
                'bbox': [0, 0, image.width, image.height],
                'path': file_path,
                'app_name': analysis.get('detected_apps', ['Unknown'])[0] if analysis.get('detected_apps') else 'Unknown',
                'activity_description': analysis.get('activity_description', ''),
                'activity_category': analysis.get('activity_category', 'unknown'),
                'detected_text': analysis.get('detected_text', [])
            }
            
            # Qdrant에 인덱싱
            repo.index_screen_patches(doc_id, vectors, [meta])
            
        except Exception as e:
            print(f"화면 활동 RAG 인덱싱 오류: {e}")

class DataCollectionManager:
    # ... (변경 없음)
    """전체 데이터 수집을 관리하는 클래스"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.file_collector = FileCollector(user_id)
        self.browser_collector = BrowserHistoryCollector(user_id)
        self.app_collector = ActiveApplicationCollector(user_id)
        self.screen_collector = ScreenActivityCollector(user_id)
        
        self.running = False
        self.collection_thread = None
        self.initial_collection_done = False
        
        # 진행률 추적용 속성 추가
        self.progress = 0.0
        self.progress_message = "초기화 중..."
        
        # 선택된 폴더 목록
        self.selected_folders = None
        
        # 폴더 선택 상태 관리
        self.folders_selected = False  # 사용자가 폴더를 선택했는지 여부
        self.waiting_for_folder_selection = True  # 폴더 선택을 기다리고 있는지 여부
    
    def start_collection(self, selected_folders: Optional[List[str]] = None):
        """데이터 수집을 시작합니다."""
        if self.running:
            return
        
        # 선택된 폴더 설정
        self.selected_folders = selected_folders
        
        # 폴더 선택 상태 업데이트
        if selected_folders is not None:
            self.folders_selected = True
            self.waiting_for_folder_selection = False
            print(f"폴더 선택 완료: {len(selected_folders)}개 폴더")
        else:
            # selected_folders가 None이면 전체 C드라이브 스캔을 의미
            self.folders_selected = True
            self.waiting_for_folder_selection = False
            print("전체 C드라이브 스캔 모드로 설정")
        
        # 초기 데이터 수집 수행 (폴더가 선택된 경우에만)
        if not self.initial_collection_done and self.folders_selected:
            self.perform_initial_collection()
        
        self.running = True
        self.collection_thread = threading.Thread(target=self._collection_loop)
        self.collection_thread.daemon = True
        self.collection_thread.start()
        
        folder_info = f" (선택된 폴더: {len(selected_folders)}개)" if selected_folders else " (전체 C드라이브)"
        print(f"사용자 {self.user_id}의 데이터 수집이 시작되었습니다{folder_info}.")
    
    def perform_initial_collection(self):
        """프로그램 시작 시 초기 데이터 수집을 수행합니다."""
        print(f"사용자 {self.user_id}의 초기 데이터 수집을 시작합니다...")
        
        try:
            # 1. 파일 수집 (전체 수집) - 전체 진행률의 80% 할당
            self.progress_message = "📁 초기 파일 수집 중..."
            print(self.progress_message)
            # manager 인스턴스(self)를 전달하여 진행률을 업데이트하도록 함
            files = self.file_collector.collect_files_from_drive(incremental=False, manager=self, selected_folders=self.selected_folders)
            
            # 2. 브라우저 히스토리 수집 (전체 진행률의 15% 할당)
            self.progress = 80.0
            self.progress_message = "🌐 초기 브라우저 히스토리 수집 중..."
            print(self.progress_message)
            history = self.browser_collector.collect_all_browser_history(incremental=False)
            
            # 3. 데이터베이스 저장 (전체 진행률의 5% 할당)
            self.progress = 95.0
            self.progress_message = "💾 데이터베이스에 저장 중..."
            print(self.progress_message)
            saved_files = self.file_collector.save_files_to_db(files)
            print(f"✅ 파일 수집 완료: {saved_files}개 저장")
            saved_history = self.browser_collector.save_browser_history_to_db(history)
            print(f"✅ 브라우저 히스토리 수집 완료: {saved_history}개 저장")
            
            self.progress = 100.0
            self.progress_message = "🎉 초기 데이터 수집 완료!"
            print(self.progress_message)
            
        except Exception as e:
            print(f"❌ 초기 데이터 수집 중 오류 발생: {e}")
            self.progress_message = "오류 발생"
        finally:
            # 완료 플래그를 마지막에 설정
            self.initial_collection_done = True
    
    def stop_collection(self):
        """데이터 수집을 중지합니다."""
        self.running = False
        if self.collection_thread:
            self.collection_thread.join()
        print(f"사용자 {self.user_id}의 데이터 수집이 중지되었습니다.")
    
    def _collection_loop(self):
        """데이터 수집 루프"""
        last_file_collection = 0
        last_browser_collection = 0
        last_app_collection = 0
        last_screen_collection = 0
        
        while self.running:
            try:
                current_time = time.time()
                
                # 파일 수집 (1시간마다) - 폴더가 선택된 경우에만
                if current_time - last_file_collection >= 3600 and self.folders_selected:
                    self._collect_files()
                    last_file_collection = current_time
                elif not self.folders_selected and self.waiting_for_folder_selection:
                    # 폴더 선택을 기다리는 중이면 메시지 출력 (최초 1회만)
                    if last_file_collection == 0:
                        print("폴더 선택을 기다리는 중입니다. 우클릭 → '폴더 선택'을 통해 수집할 폴더를 선택하세요.")
                        last_file_collection = current_time  # 메시지 중복 출력 방지
                
                # 브라우저 히스토리 수집 (30분마다)
                if current_time - last_browser_collection >= 1800:
                    self._collect_browser_history()
                    last_browser_collection = current_time
                
                # 활성 애플리케이션 수집 (5분마다)
                if current_time - last_app_collection >= 300:
                    self._collect_active_apps()
                    last_app_collection = current_time
                
                # 화면 활동 수집 (1분마다)
                if current_time - last_screen_collection >= 60:
                    self._collect_screen_activity()
                    last_screen_collection = current_time
                
                time.sleep(10)  # 10초마다 체크
                
            except Exception as e:
                print(f"데이터 수집 루프 오류: {e}")
                time.sleep(30)  # 오류 발생 시 30초 대기
    
    def _collect_files(self):
        """파일 수집 (증분 수집)"""
        try:
            print("파일 수집 시작...")
            files = self.file_collector.collect_files_from_drive(incremental=True, selected_folders=self.selected_folders)
            saved_count = self.file_collector.save_files_to_db(files)
            print(f"파일 수집 완료: {saved_count}개 저장")
        except Exception as e:
            print(f"파일 수집 오류: {e}")
    
    def _collect_browser_history(self):
        """브라우저 히스토리 수집 (증분 수집)"""
        try:
            print("브라우저 히스토리 수집 시작...")
            history = self.browser_collector.collect_all_browser_history(incremental=True)
            saved_count = self.browser_collector.save_browser_history_to_db(history)
            print(f"브라우저 히스토리 수집 완료: {saved_count}개 저장")
        except Exception as e:
            print(f"브라우저 히스토리 수집 오류: {e}")
    
    def _collect_active_apps(self):
        """활성 애플리케이션 수집"""
        try:
            print("활성 애플리케이션 수집 시작...")
            apps = self.app_collector.collect_active_applications()
            saved_count = self.app_collector.save_active_apps_to_db(apps)
            print(f"활성 애플리케이션 수집 완료: {saved_count}개 저장")
        except Exception as e:
            print(f"활성 애플리케이션 수집 오류: {e}")
    
    def _collect_screen_activity(self):
        """화면 활동 수집"""
        try:
            print("화면 활동 수집 시작...")
            
            # 스크린샷 캡처
            screenshot_result = self.screen_collector.capture_screenshot()
            if screenshot_result:
                image_data, file_path = screenshot_result
                
                # LLM 분석 (비동기로 실행)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                analysis = loop.run_until_complete(
                    self.screen_collector.analyze_screenshot_with_llm(image_data)
                )
                loop.close()
                
                # 데이터베이스에 저장
                success = self.screen_collector.save_screen_activity_to_db(
                    image_data, file_path, analysis
                )
                
                if success:
                    print(f"화면 활동 수집 완료: {analysis.get('activity_category', 'unknown')}")
                else:
                    print("화면 활동 저장 실패")
            else:
                print("스크린샷 캡처 실패")
                
        except Exception as e:
            print(f"화면 활동 수집 오류: {e}")

# 전역 데이터 수집 관리자들
data_collection_managers = {}

def start_user_data_collection(user_id: int, selected_folders: Optional[List[str]] = None):
    """사용자 데이터 수집을 시작합니다."""
    if user_id not in data_collection_managers:
        manager = DataCollectionManager(user_id)
        data_collection_managers[user_id] = manager
        
        # 폴더 선택이 있으면 데이터 수집 시작, 없으면 대기 상태로 설정
        if selected_folders is not None:
            manager.start_collection(selected_folders)
        else:
            # 폴더 선택 없이 호출된 경우, 대기 상태로 설정
            manager.running = True
            manager.collection_thread = threading.Thread(target=manager._collection_loop)
            manager.collection_thread.daemon = True
            manager.collection_thread.start()
            print(f"사용자 {user_id}의 데이터 수집 시스템이 대기 상태로 시작되었습니다.")
            print("폴더 선택을 기다리는 중입니다. 우클릭 → '폴더 선택'을 통해 수집할 폴더를 선택하세요.")
    else:
        # 이미 실행 중인 경우, 폴더 선택이 있으면 업데이트
        manager = data_collection_managers[user_id]
        if selected_folders is not None:
            manager.start_collection(selected_folders)
        else:
            print(f"사용자 {user_id}의 데이터 수집이 이미 실행 중입니다.")

def stop_user_data_collection(user_id: int):
    """사용자 데이터 수집을 중지합니다."""
    if user_id in data_collection_managers:
        data_collection_managers[user_id].stop_collection()
        del data_collection_managers[user_id]

def stop_all_data_collection():
    """모든 사용자의 데이터 수집을 중지합니다."""
    for user_id in list(data_collection_managers.keys()):
        stop_user_data_collection(user_id)