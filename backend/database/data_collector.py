import os
import sys
import time
import json
import sqlite3
import psutil
import platform
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import asyncio
import aiofiles
import sqlite3
import winreg
import subprocess
import numpy as np
import hashlib

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from .models import User, UserFile, BrowserHistory, ActiveApplication, ScreenActivity
from .connection import get_db_session
from config.settings import settings

class FileCollector:
    """사용자 드라이브의 파일들을 수집하는 클래스"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.db_session = get_db_session()
        self.supported_extensions = {
            'document': ['.txt', '.doc', '.docx', '.pdf', '.rtf', '.odt'],
            'spreadsheet': ['.xls', '.xlsx', '.csv', '.ods'],
            'presentation': ['.ppt', '.pptx', '.odp'],
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'],
            'video': ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv'],
            'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg'],
            'code': ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.php', '.rb', '.go', '.rs'],
            'archive': ['.zip', '.rar', '.7z', '.tar', '.gz']
        }
        
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
            'AppData', 'Local', 'Roaming', 'Temp', 'tmp'
        ]
        
        dir_name = Path(dir_path).name.lower()
        return any(pattern.lower() in dir_name for pattern in skip_patterns)
    
    def collect_files_from_drive(self, drive_path: str = "C:\\") -> List[Dict[str, Any]]:
        """지정된 드라이브에서 파일들을 수집합니다."""
        collected_files = []
        
        try:
            for root, dirs, files in os.walk(drive_path):
                # 건너뛸 디렉토리 제거
                dirs[:] = [d for d in dirs if not self.should_skip_directory(os.path.join(root, d))]
                
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        
                        # 파일 정보 수집
                        stat = os.stat(file_path)
                        
                        file_info = {
                            'user_id': self.user_id,
                            'file_path': file_path,
                            'file_name': file,
                            'file_size': stat.st_size,
                            'file_type': Path(file).suffix.lower(),
                            'file_category': self.get_file_category(file_path),
                            'created_date': datetime.fromtimestamp(stat.st_ctime),
                            'modified_date': datetime.fromtimestamp(stat.st_mtime),
                            'accessed_date': datetime.fromtimestamp(stat.st_atime),
                            'discovered_at': datetime.utcnow()
                        }
                        
                        collected_files.append(file_info)
                        
                    except (PermissionError, OSError) as e:
                        print(f"파일 접근 오류 {file_path}: {e}")
                        continue
                        
        except Exception as e:
            print(f"드라이브 스캔 오류: {e}")
            
        return collected_files
    
    def save_files_to_db(self, files: List[Dict[str, Any]]) -> int:
        """수집된 파일들을 데이터베이스에 저장합니다."""
        saved_count = 0
        
        for file_info in files:
            try:
                # 중복 체크
                existing_file = self.db_session.query(UserFile).filter(
                    and_(
                        UserFile.user_id == self.user_id,
                        UserFile.file_path == file_info['file_path']
                    )
                ).first()
                
                if existing_file:
                    # 기존 파일 정보 업데이트
                    existing_file.modified_date = file_info['modified_date']
                    existing_file.accessed_date = file_info['accessed_date']
                    existing_file.file_size = file_info['file_size']
                else:
                    # 새 파일 추가
                    new_file = UserFile(**file_info)
                    self.db_session.add(new_file)
                
                saved_count += 1
                
            except Exception as e:
                print(f"파일 저장 오류 {file_info['file_path']}: {e}")
                continue
        
        try:
            self.db_session.commit()
        except Exception as e:
            print(f"데이터베이스 커밋 오류: {e}")
            self.db_session.rollback()
            
        return saved_count

class BrowserHistoryCollector:
    """브라우저 사용 기록을 수집하는 클래스"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.db_session = get_db_session()
        self.browser_paths = {
            'chrome': {
                'path': os.path.expanduser('~\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\History'),
                'name': 'Chrome'
            },
            'firefox': {
                'path': os.path.expanduser('~\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles'),
                'name': 'Firefox'
            },
            'edge': {
                'path': os.path.expanduser('~\\AppData\\Local\\Microsoft\\Edge\\User Data\\Default\\History'),
                'name': 'Edge'
            }
        }
    
    def get_chrome_history(self) -> List[Dict[str, Any]]:
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
            
            cursor.execute("""
                SELECT url, title, visit_count, last_visit_time, typed_count
                FROM urls ORDER BY last_visit_time DESC LIMIT 1000
            """)
            
            for row in cursor.fetchall():
                url, title, visit_count, last_visit_time, typed_count = row
                
                # Chrome 시간을 datetime으로 변환
                chrome_time = datetime(1601, 1, 1) + timedelta(microseconds=last_visit_time)
                
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
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                               r"Software\Google\Chrome\BLBeacon")
            version, _ = winreg.QueryValueEx(key, "version")
            return version
        except:
            return "Unknown"
    
    def get_firefox_history(self) -> List[Dict[str, Any]]:
        """Firefox 브라우저 히스토리를 수집합니다."""
        history_data = []
        
        try:
            firefox_path = self.browser_paths['firefox']['path']
            if not os.path.exists(firefox_path):
                return history_data
            
            # Firefox 프로필 폴더 찾기
            profiles = [d for d in os.listdir(firefox_path) if d.endswith('.default')]
            if not profiles:
                return history_data
            
            profile_path = os.path.join(firefox_path, profiles[0])
            places_path = os.path.join(profile_path, 'places.sqlite')
            
            if not os.path.exists(places_path):
                return history_data
            
            # Firefox 히스토리 파일 복사
            import shutil
            temp_path = f"{places_path}_temp"
            shutil.copy2(places_path, temp_path)
            
            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT url, title, visit_count, last_visit_date
                FROM moz_places WHERE last_visit_date IS NOT NULL
                ORDER BY last_visit_date DESC LIMIT 1000
            """)
            
            for row in cursor.fetchall():
                url, title, visit_count, last_visit_date = row
                
                # Firefox 시간을 datetime으로 변환
                firefox_time = datetime.fromtimestamp(last_visit_date / 1000000)
                
                history_data.append({
                    'user_id': self.user_id,
                    'browser_name': 'Firefox',
                    'browser_version': self.get_firefox_version(),
                    'url': url,
                    'title': title,
                    'visit_count': visit_count,
                    'visit_time': firefox_time,
                    'last_visit_time': firefox_time,
                    'page_transition': 'link',
                    'recorded_at': datetime.utcnow()
                })
            
            conn.close()
            os.remove(temp_path)
            
        except Exception as e:
            print(f"Firefox 히스토리 수집 오류: {e}")
            
        return history_data
    
    def get_firefox_version(self) -> str:
        """Firefox 버전을 가져옵니다."""
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                               r"SOFTWARE\Mozilla\Mozilla Firefox")
            version, _ = winreg.QueryValueEx(key, "CurrentVersion")
            return version
        except:
            return "Unknown"
    
    def collect_all_browser_history(self) -> List[Dict[str, Any]]:
        """모든 브라우저의 히스토리를 수집합니다."""
        all_history = []
        
        # Chrome 히스토리
        chrome_history = self.get_chrome_history()
        all_history.extend(chrome_history)
        
        # Firefox 히스토리
        firefox_history = self.get_firefox_history()
        all_history.extend(firefox_history)
        
        return all_history
    
    def save_browser_history_to_db(self, history_data: List[Dict[str, Any]]) -> int:
        """브라우저 히스토리를 데이터베이스에 저장합니다."""
        saved_count = 0
        
        for history_item in history_data:
            try:
                # 중복 체크 (URL과 방문 시간 기준)
                existing_history = self.db_session.query(BrowserHistory).filter(
                    and_(
                        BrowserHistory.user_id == self.user_id,
                        BrowserHistory.url == history_item['url'],
                        BrowserHistory.visit_time == history_item['visit_time']
                    )
                ).first()
                
                if not existing_history:
                    new_history = BrowserHistory(**history_item)
                    self.db_session.add(new_history)
                    saved_count += 1
                
            except Exception as e:
                print(f"브라우저 히스토리 저장 오류: {e}")
                continue
        
        try:
            self.db_session.commit()
        except Exception as e:
            print(f"데이터베이스 커밋 오류: {e}")
            self.db_session.rollback()
            
        return saved_count

class ActiveApplicationCollector:
    """실행 중인 애플리케이션 정보를 수집하는 클래스"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.db_session = get_db_session()
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
            import win32api
            info = win32api.GetFileVersionInfo(exe_path, "\\")
            ms = info['FileVersionMS']
            ls = info['FileVersionLS']
            version = f"{win32api.HIWORD(ms)}.{win32api.LOWORD(ms)}.{win32api.HIWORD(ls)}.{win32api.LOWORD(ls)}"
            return version
        except:
            return "Unknown"
    
    def save_active_apps_to_db(self, apps_data: List[Dict[str, Any]]) -> int:
        """활성 애플리케이션 정보를 데이터베이스에 저장합니다."""
        saved_count = 0
        
        for app_data in apps_data:
            try:
                # 중복 체크 (같은 시간에 같은 앱이 이미 기록되어 있는지)
                existing_app = self.db_session.query(ActiveApplication).filter(
                    and_(
                        ActiveApplication.user_id == self.user_id,
                        ActiveApplication.app_name == app_data['app_name'],
                        ActiveApplication.recorded_at >= datetime.utcnow() - timedelta(minutes=1)
                    )
                ).first()
                
                if not existing_app:
                    new_app = ActiveApplication(**app_data)
                    self.db_session.add(new_app)
                    saved_count += 1
                
            except Exception as e:
                print(f"활성 애플리케이션 저장 오류: {e}")
                continue
        
        try:
            self.db_session.commit()
        except Exception as e:
            print(f"데이터베이스 커밋 오류: {e}")
            self.db_session.rollback()
            
        return saved_count

class ScreenActivityCollector:
    """화면 활동을 수집하고 분석하는 클래스"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.db_session = get_db_session()
        self.screenshot_dir = Path("uploads/screenshots")
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
            # 스크린샷 캡처
            screenshot = ImageGrab.grab()
            
            # 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{self.user_id}_{timestamp}.png"
            file_path = self.screenshot_dir / filename
            
            # 이미지 저장
            screenshot.save(file_path, 'PNG')
            
            # 바이너리 데이터 읽기
            with open(file_path, 'rb') as f:
                image_data = f.read()
            
            return image_data, str(file_path)
            
        except Exception as e:
            print(f"스크린샷 캡처 오류: {e}")
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
        """화면 활동 정보를 데이터베이스에 저장합니다."""
        try:
            # 화면 해상도 가져오기
            screen = ImageGrab.grab()
            resolution = f"{screen.width}x{screen.height}"
            
            screen_activity = ScreenActivity(
                user_id=self.user_id,
                screenshot_path=file_path,
                screenshot_data=screenshot_data,
                activity_description=analysis.get('activity_description', ''),
                activity_category=analysis.get('activity_category', ''),
                activity_confidence=analysis.get('activity_confidence', 0.0),
                detected_apps=analysis.get('detected_apps', []),
                detected_text=analysis.get('detected_text', []),
                detected_objects=analysis.get('detected_objects', []),
                screen_resolution=resolution,
                color_mode='light',  # 기본값
                captured_at=datetime.utcnow(),
                analyzed_at=datetime.utcnow()
            )
            
            self.db_session.add(screen_activity)
            self.db_session.commit()
            
            return True
            
        except Exception as e:
            print(f"화면 활동 저장 오류: {e}")
            self.db_session.rollback()
            return False

class DataCollectionManager:
    """전체 데이터 수집을 관리하는 클래스"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.file_collector = FileCollector(user_id)
        self.browser_collector = BrowserHistoryCollector(user_id)
        self.app_collector = ActiveApplicationCollector(user_id)
        self.screen_collector = ScreenActivityCollector(user_id)
        
        self.running = False
        self.collection_thread = None
    
    def start_collection(self):
        """데이터 수집을 시작합니다."""
        if self.running:
            return
        
        self.running = True
        self.collection_thread = threading.Thread(target=self._collection_loop)
        self.collection_thread.daemon = True
        self.collection_thread.start()
        
        print(f"사용자 {self.user_id}의 데이터 수집이 시작되었습니다.")
    
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
                
                # 파일 수집 (1시간마다)
                if current_time - last_file_collection >= 3600:
                    self._collect_files()
                    last_file_collection = current_time
                
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
        """파일 수집"""
        try:
            print("파일 수집 시작...")
            files = self.file_collector.collect_files_from_drive()
            saved_count = self.file_collector.save_files_to_db(files)
            print(f"파일 수집 완료: {saved_count}개 저장")
        except Exception as e:
            print(f"파일 수집 오류: {e}")
    
    def _collect_browser_history(self):
        """브라우저 히스토리 수집"""
        try:
            print("브라우저 히스토리 수집 시작...")
            history = self.browser_collector.collect_all_browser_history()
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

def start_user_data_collection(user_id: int):
    """사용자 데이터 수집을 시작합니다."""
    if user_id not in data_collection_managers:
        manager = DataCollectionManager(user_id)
        data_collection_managers[user_id] = manager
        manager.start_collection()
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
