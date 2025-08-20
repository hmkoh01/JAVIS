import sqlite3
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SQLiteMeta:
    """SQLite 메타데이터 관리 클래스"""
    
    def __init__(self, db_path: str = "./var/meta.db"):
        self.db_path = db_path
        self._ensure_db_dir()
        self._init_db()
    
    def _ensure_db_dir(self):
        """데이터베이스 디렉토리 생성"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def _init_db(self):
        """데이터베이스 초기화 및 테이블 생성"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    doc_id TEXT PRIMARY KEY,
                    path TEXT NOT NULL,
                    mime TEXT,
                    size INTEGER,
                    created_at INTEGER,
                    updated_at INTEGER,
                    accessed_at INTEGER,
                    category TEXT,
                    preview TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS web_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    title TEXT,
                    visited_at INTEGER,
                    visit_count INTEGER DEFAULT 1,
                    transition TEXT,
                    browser TEXT,
                    version TEXT,
                    domain TEXT,
                    duration_sec INTEGER,
                    tab_title TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS apps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    pid INTEGER,
                    cpu REAL,
                    mem REAL,
                    started_at INTEGER,
                    window_title TEXT,
                    category TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS screenshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id TEXT,
                    path TEXT,
                    captured_at INTEGER,
                    app_name TEXT,
                    window_title TEXT,
                    hash TEXT,
                    ocr TEXT,
                    gemini_desc TEXT,
                    category TEXT,
                    confidence REAL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS interests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    score REAL DEFAULT 1.0,
                    updated_at INTEGER
                )
            """)
            
            # 데이터 수집용 테이블들 추가
            conn.execute("""
                CREATE TABLE IF NOT EXISTS collected_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    file_name TEXT,
                    file_size INTEGER,
                    file_type TEXT,
                    file_category TEXT,
                    content_preview TEXT,
                    created_date INTEGER,
                    modified_date INTEGER,
                    accessed_date INTEGER,
                    processed BOOLEAN DEFAULT FALSE,
                    processing_error TEXT,
                    discovered_at INTEGER
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS collected_browser_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    browser_name TEXT,
                    browser_version TEXT,
                    url TEXT NOT NULL,
                    title TEXT,
                    visit_count INTEGER DEFAULT 1,
                    visit_time INTEGER,
                    last_visit_time INTEGER,
                    page_transition TEXT,
                    visit_duration INTEGER,
                    content_analyzed BOOLEAN DEFAULT FALSE,
                    content_summary TEXT,
                    recorded_at INTEGER
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS collected_apps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    app_name TEXT,
                    app_path TEXT,
                    app_version TEXT,
                    app_category TEXT,
                    start_time INTEGER,
                    end_time INTEGER,
                    duration INTEGER,
                    window_title TEXT,
                    window_state TEXT,
                    cpu_usage REAL,
                    memory_usage REAL,
                    recorded_at INTEGER
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS collected_screenshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    screenshot_path TEXT,
                    screenshot_data BLOB,
                    activity_description TEXT,
                    activity_category TEXT,
                    activity_confidence REAL,
                    detected_apps TEXT,  -- JSON as TEXT
                    detected_text TEXT,  -- JSON as TEXT
                    detected_objects TEXT,  -- JSON as TEXT
                    screen_resolution TEXT,
                    color_mode TEXT,
                    screenshot_embedding TEXT,  -- JSON as TEXT
                    activity_embedding TEXT,  -- JSON as TEXT
                    captured_at INTEGER,
                    analyzed_at INTEGER
                )
            """)
            
            # 인덱스 생성
            conn.execute("CREATE INDEX IF NOT EXISTS idx_web_history_visited_at ON web_history(visited_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_apps_started_at ON apps(started_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_screenshots_captured_at ON screenshots(captured_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_interests_user_updated ON interests(user_id, updated_at)")
            
            # 데이터 수집 테이블 인덱스
            conn.execute("CREATE INDEX IF NOT EXISTS idx_collected_files_user_id ON collected_files(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_collected_files_discovered_at ON collected_files(discovered_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_collected_browser_user_id ON collected_browser_history(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_collected_browser_recorded_at ON collected_browser_history(recorded_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_collected_apps_user_id ON collected_apps(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_collected_apps_recorded_at ON collected_apps(recorded_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_collected_screenshots_user_id ON collected_screenshots(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_collected_screenshots_captured_at ON collected_screenshots(captured_at)")
            
            conn.commit()
    
    def upsert_file(self, doc_id: str, path: str, mime: str = None, size: int = None,
                   created_at: int = None, updated_at: int = None, accessed_at: int = None,
                   category: str = None, preview: str = None) -> bool:
        """파일 정보 업서트"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO files 
                    (doc_id, path, mime, size, created_at, updated_at, accessed_at, category, preview)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (doc_id, path, mime, size, created_at, updated_at, accessed_at, category, preview))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"파일 업서트 오류: {e}")
            return False
    
    def insert_web_history(self, url: str, title: str = None, visited_at: int = None,
                          transition: str = None, browser: str = None, version: str = None,
                          domain: str = None, duration_sec: int = None, tab_title: str = None) -> bool:
        """웹 히스토리 삽입"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO web_history 
                    (url, title, visited_at, transition, browser, version, domain, duration_sec, tab_title)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (url, title, visited_at, transition, browser, version, domain, duration_sec, tab_title))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"웹 히스토리 삽입 오류: {e}")
            return False
    
    def insert_app(self, name: str, pid: int = None, cpu: float = None, mem: float = None,
                  started_at: int = None, window_title: str = None, category: str = None) -> bool:
        """앱 정보 삽입"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO apps 
                    (name, pid, cpu, mem, started_at, window_title, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (name, pid, cpu, mem, started_at, window_title, category))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"앱 정보 삽입 오류: {e}")
            return False
    
    def insert_screenshot(self, doc_id: str, path: str, captured_at: int = None,
                         app_name: str = None, window_title: str = None, hash: str = None,
                         ocr: str = None, gemini_desc: str = None, category: str = None,
                         confidence: float = None) -> bool:
        """스크린샷 정보 삽입"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO screenshots 
                    (doc_id, path, captured_at, app_name, window_title, hash, ocr, gemini_desc, category, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (doc_id, path, captured_at, app_name, window_title, hash, ocr, gemini_desc, category, confidence))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"스크린샷 삽입 오류: {e}")
            return False
    
    def upsert_interest(self, user_id: str, topic: str, score: float = 1.0) -> bool:
        """관심사 업서트"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO interests 
                    (user_id, topic, score, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (user_id, topic, score, int(datetime.now().timestamp())))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"관심사 업서트 오류: {e}")
            return False
    
    def get_file(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """파일 정보 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM files WHERE doc_id = ?", (doc_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"파일 조회 오류: {e}")
            return None
    
    def recent_web_history(self, limit: int = 100, since_ts: int = None) -> List[Dict[str, Any]]:
        """최근 웹 히스토리 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                query = "SELECT * FROM web_history"
                params = []
                if since_ts:
                    query += " WHERE visited_at >= ?"
                    params.append(since_ts)
                query += " ORDER BY visited_at DESC LIMIT ?"
                params.append(limit)
                
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"웹 히스토리 조회 오류: {e}")
            return []
    
    def recent_apps(self, limit: int = 100, since_ts: int = None) -> List[Dict[str, Any]]:
        """최근 앱 정보 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                query = "SELECT * FROM apps"
                params = []
                if since_ts:
                    query += " WHERE started_at >= ?"
                    params.append(since_ts)
                query += " ORDER BY started_at DESC LIMIT ?"
                params.append(limit)
                
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"앱 정보 조회 오류: {e}")
            return []
    
    def recent_screenshots(self, limit: int = 100, since_ts: int = None) -> List[Dict[str, Any]]:
        """최근 스크린샷 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                query = "SELECT * FROM screenshots"
                params = []
                if since_ts:
                    query += " WHERE captured_at >= ?"
                    params.append(since_ts)
                query += " ORDER BY captured_at DESC LIMIT ?"
                params.append(limit)
                
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"스크린샷 조회 오류: {e}")
            return []
    
    def top_interests(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """사용자 관심사 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM interests 
                    WHERE user_id = ? 
                    ORDER BY score DESC, updated_at DESC 
                    LIMIT ?
                """, (user_id, limit))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"관심사 조회 오류: {e}")
            return []

    # === 데이터 수집용 메서드들 ===
    
    def insert_collected_file(self, file_info: Dict[str, Any]) -> bool:
        """수집된 파일 정보 저장"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO collected_files 
                    (user_id, file_path, file_name, file_size, file_type, file_category, 
                     content_preview, created_date, modified_date, accessed_date, discovered_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    file_info['user_id'],
                    file_info['file_path'],
                    file_info['file_name'],
                    file_info['file_size'],
                    file_info['file_type'],
                    file_info['file_category'],
                    file_info.get('content_preview', ''),
                    int(file_info['created_date'].timestamp()) if file_info.get('created_date') else None,
                    int(file_info['modified_date'].timestamp()) if file_info.get('modified_date') else None,
                    int(file_info['accessed_date'].timestamp()) if file_info.get('accessed_date') else None,
                    int(datetime.now().timestamp())
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"수집된 파일 저장 오류: {e}")
            return False

    def insert_collected_browser_history(self, history_info: Dict[str, Any]) -> bool:
        """수집된 브라우저 히스토리 저장"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO collected_browser_history 
                    (user_id, browser_name, browser_version, url, title, visit_count,
                     visit_time, last_visit_time, page_transition, visit_duration, recorded_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    history_info['user_id'],
                    history_info.get('browser_name', ''),
                    history_info.get('browser_version', ''),
                    history_info['url'],
                    history_info.get('title', ''),
                    history_info.get('visit_count', 1),
                    int(history_info['visit_time'].timestamp()) if history_info.get('visit_time') else None,
                    int(history_info['last_visit_time'].timestamp()) if history_info.get('last_visit_time') else None,
                    history_info.get('page_transition', ''),
                    history_info.get('visit_duration', 0),
                    int(datetime.now().timestamp())
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"수집된 브라우저 히스토리 저장 오류: {e}")
            return False

    def insert_collected_app(self, app_info: Dict[str, Any]) -> bool:
        """수집된 앱 정보 저장"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO collected_apps 
                    (user_id, app_name, app_path, app_version, app_category, start_time,
                     end_time, duration, window_title, window_state, cpu_usage, memory_usage, recorded_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    app_info['user_id'],
                    app_info.get('app_name', ''),
                    app_info.get('app_path', ''),
                    app_info.get('app_version', ''),
                    app_info.get('app_category', ''),
                    int(app_info['start_time'].timestamp()) if app_info.get('start_time') else None,
                    int(app_info['end_time'].timestamp()) if app_info.get('end_time') else None,
                    app_info.get('duration', 0),
                    app_info.get('window_title', ''),
                    app_info.get('window_state', ''),
                    app_info.get('cpu_usage', 0.0),
                    app_info.get('memory_usage', 0.0),
                    int(datetime.now().timestamp())
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"수집된 앱 정보 저장 오류: {e}")
            return False

    def insert_collected_screenshot(self, screenshot_info: Dict[str, Any]) -> bool:
        """수집된 스크린샷 정보 저장"""
        try:
            import json
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO collected_screenshots 
                    (user_id, screenshot_path, screenshot_data, activity_description, activity_category,
                     activity_confidence, detected_apps, detected_text, detected_objects, screen_resolution,
                     color_mode, captured_at, analyzed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    screenshot_info['user_id'],
                    screenshot_info.get('screenshot_path', ''),
                    screenshot_info.get('screenshot_data'),
                    screenshot_info.get('activity_description', ''),
                    screenshot_info.get('activity_category', ''),
                    screenshot_info.get('activity_confidence', 0.0),
                    json.dumps(screenshot_info.get('detected_apps', [])),
                    json.dumps(screenshot_info.get('detected_text', [])),
                    json.dumps(screenshot_info.get('detected_objects', [])),
                    screenshot_info.get('screen_resolution', ''),
                    screenshot_info.get('color_mode', 'light'),
                    int(datetime.now().timestamp()),
                    int(datetime.now().timestamp())
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"수집된 스크린샷 저장 오류: {e}")
            return False

    def get_collected_files(self, user_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """사용자 수집 파일 목록 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM collected_files 
                    WHERE user_id = ? 
                    ORDER BY discovered_at DESC 
                    LIMIT ?
                """, (user_id, limit))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"수집된 파일 조회 오류: {e}")
            return []

    def get_collected_browser_history(self, user_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """사용자 수집 브라우저 히스토리 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM collected_browser_history 
                    WHERE user_id = ? 
                    ORDER BY recorded_at DESC 
                    LIMIT ?
                """, (user_id, limit))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"수집된 브라우저 히스토리 조회 오류: {e}")
            return []

    def get_collected_apps(self, user_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """사용자 수집 앱 정보 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM collected_apps 
                    WHERE user_id = ? 
                    ORDER BY recorded_at DESC 
                    LIMIT ?
                """, (user_id, limit))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"수집된 앱 정보 조회 오류: {e}")
            return []

    def get_collected_screenshots(self, user_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """사용자 수집 스크린샷 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM collected_screenshots 
                    WHERE user_id = ? 
                    ORDER BY captured_at DESC 
                    LIMIT ?
                """, (user_id, limit))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"수집된 스크린샷 조회 오류: {e}")
            return []

    def get_collection_stats(self) -> Dict[str, int]:
        """데이터 수집 통계 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                stats = {}
                tables = ['collected_files', 'collected_browser_history', 'collected_apps', 'collected_screenshots']
                for table in tables:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[table] = cursor.fetchone()[0]
                return stats
        except Exception as e:
            logger.error(f"수집 통계 조회 오류: {e}")
            return {}
    
    def find_file_by_path(self, path: str) -> Optional[str]:
        """경로로 파일 doc_id 찾기"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT doc_id FROM files WHERE path = ?", (path,))
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"파일 경로 조회 오류: {e}")
            return None
