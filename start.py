#!/usr/bin/env python3
"""
JAVIS Multi-Agent System Startup Script
멀티모달 RAG 시스템을 쉽게 시작할 수 있는 스크립트
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def check_dependencies():
    """필요한 의존성 확인"""
    print("🔍 의존성 확인 중...")
    
    required_packages = [
        ('fastapi', 'fastapi'),
        ('uvicorn', 'uvicorn'),
        ('streamlit', 'streamlit'),
        ('google-generativeai', 'google.generativeai'),
        ('pillow', 'PIL'),
        ('sqlalchemy', 'sqlalchemy'),
        ('pydantic', 'pydantic')
    ]
    
    missing_packages = []
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"❌ 누락된 패키지: {', '.join(missing_packages)}")
        print("다음 명령어로 설치하세요:")
        print("pip install -r requirements.txt")
        return False
    
    print("✅ 모든 의존성이 설치되어 있습니다.")
    return True

def check_env_file():
    """환경 변수 파일 확인"""
    print("🔍 환경 변수 파일 확인 중...")
    
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env 파일이 없습니다.")
        print("다음 내용으로 .env 파일을 생성하세요:")
        print("""
# Gemini API 설정
GEMINI_API_KEY=your_gemini_api_key_here

# 데이터베이스 설정
DATABASE_URL=sqlite:///./javis.db

# API 설정
API_HOST=0.0.0.0
API_PORT=8000

# 이미지 업로드 설정
IMAGE_UPLOAD_PATH=./uploads/images
MAX_IMAGE_SIZE_MB=10
        """)
        return False
    
    print("✅ .env 파일이 존재합니다.")
    return True

def create_directories():
    """필요한 디렉토리 생성"""
    print("📁 디렉토리 생성 중...")
    
    directories = [
        "uploads",
        "uploads/images",
        "backend/logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ 필요한 디렉토리가 생성되었습니다.")

def check_frontend_file():
    """프론트엔드 파일 확인"""
    print("🔍 프론트엔드 파일 확인 중...")
    
    frontend_file = Path("frontend/front.py")
    if not frontend_file.exists():
        print("❌ frontend/front.py 파일이 없습니다.")
        print("프론트엔드 파일을 생성해야 합니다.")
        return False
    
    print("✅ 프론트엔드 파일이 존재합니다.")
    return True

def initialize_database():
    """데이터베이스 초기화"""
    print("🗄️ 데이터베이스 초기화 중...")
    
    try:
        # backend 디렉토리를 Python 경로에 추가
        backend_path = Path("backend")
        if backend_path.exists():
            sys.path.insert(0, str(backend_path))
            
            from database.connection import create_tables
            create_tables()
            print("✅ 데이터베이스가 초기화되었습니다.")
            return True
        else:
            print("❌ backend 디렉토리를 찾을 수 없습니다.")
            return False
    except Exception as e:
        print(f"❌ 데이터베이스 초기화 실패: {e}")
        return False

def start_backend():
    """백엔드 서버 시작"""
    print("🚀 백엔드 서버 시작 중...")
    
    try:
        backend_dir = Path("backend")
        if not backend_dir.exists():
            print("❌ backend 디렉토리를 찾을 수 없습니다.")
            return None
        
        # 현재 작업 디렉토리 저장
        original_cwd = os.getcwd()
        
        # backend 디렉토리로 이동
        os.chdir(backend_dir)
        
        # 백엔드 서버 시작 (간단한 버전 사용)
        process = subprocess.Popen([
            sys.executable, 'main_simple.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 원래 디렉토리로 복원
        os.chdir(original_cwd)
        
        # 서버 시작 대기
        time.sleep(5)
        
        if process.poll() is None:
            print("✅ 백엔드 서버가 시작되었습니다.")
            print("🌐 API 문서: http://localhost:8000/docs")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ 백엔드 서버 시작 실패:")
            if stdout:
                print(f"stdout: {stdout.decode()}")
            if stderr:
                print(f"stderr: {stderr.decode()}")
            return None
    except Exception as e:
        print(f"❌ 백엔드 서버 시작 중 오류: {e}")
        return None

def start_frontend():
    """프론트엔드 시작 (데스크톱 플로팅 채팅 앱)"""
    print("🎨 데스크톱 플로팅 채팅 앱 시작 중...")
    
    try:
        frontend_file = Path("frontend/front.py")
        if not frontend_file.exists():
            print("❌ frontend/front.py 파일을 찾을 수 없습니다.")
            return None
        
        # 데스크톱 플로팅 채팅 앱 실행
        process = subprocess.Popen([
            sys.executable, str(frontend_file)
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 서버 시작 대기
        time.sleep(3)
        
        if process.poll() is None:
            print("✅ 데스크톱 플로팅 채팅 앱이 시작되었습니다.")
            print("💬 화면 우측 하단에 플로팅 버튼이 나타납니다.")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ 데스크톱 앱 시작 실패:")
            if stdout:
                print(f"stdout: {stdout.decode()}")
            if stderr:
                print(f"stderr: {stderr.decode()}")
            return None
    except Exception as e:
        print(f"❌ 데스크톱 앱 시작 중 오류: {e}")
        return None

def main():
    """메인 함수"""
    print("🤖 JAVIS Multi-Agent System - 멀티모달 RAG Edition")
    print("=" * 60)
    
    # 현재 디렉토리를 프로젝트 루트로 설정
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # 의존성 확인
    if not check_dependencies():
        return
    
    # 환경 변수 파일 확인
    if not check_env_file():
        return
    
    # 프론트엔드 파일 확인
    if not check_frontend_file():
        print("프론트엔드 파일이 없습니다. 백엔드만 시작하거나 파일을 생성하세요.")
        choice = input("백엔드만 시작하시겠습니까? (y/n): ").strip().lower()
        if choice != 'y':
            return
    
    # 디렉토리 생성
    create_directories()
    
    # 데이터베이스 초기화
    if not initialize_database():
        return
    
    while True:     
        print("\n🔄 전체 시스템을 시작합니다...")
        backend_process = start_backend()
        if not backend_process:
            break
        
        frontend_process = start_frontend()
        if not frontend_process:
            backend_process.terminate()
            break
            
        print("\n🎉 JAVIS Multi-Agent System이 성공적으로 시작되었습니다!")
        print("=" * 60)
        print("🔗 API 문서: http://localhost:8000/docs")
        print("📊 시스템 정보: http://localhost:8000/info")
        print("=" * 60)
        print("\n시스템을 종료하려면 Ctrl+C를 누르세요...")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 시스템을 종료합니다...")
            backend_process.terminate()
            frontend_process.terminate()
            print("✅ 시스템이 종료되었습니다.")
        break


if __name__ == "__main__":
    main()
