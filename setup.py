#!/usr/bin/env python3
"""
JAVIS Multi-Agent System Setup Script
시스템 초기 설정을 도와주는 스크립트
"""

import os
import sys
from pathlib import Path

def create_env_file():
    """환경 변수 파일 생성"""
    print("🔧 환경 변수 파일 생성 중...")
    
    env_content = """# Gemini API 설정
GEMINI_API_KEY=your_gemini_api_key_here

# 데이터베이스 설정
DATABASE_URL=sqlite:///./javis.db

# API 설정
API_HOST=0.0.0.0
API_PORT=8000

# 이미지 업로드 설정
IMAGE_UPLOAD_PATH=./uploads/images
MAX_IMAGE_SIZE_MB=10

# 로깅 설정
LOG_LEVEL=INFO
"""
    
    env_file = Path(".env")
    if env_file.exists():
        print("⚠️ .env 파일이 이미 존재합니다.")
        overwrite = input("덮어쓰시겠습니까? (y/n): ").strip().lower()
        if overwrite != 'y':
            print("환경 변수 파일 생성을 건너뜁니다.")
            return True
    
    try:
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        print("✅ .env 파일이 생성되었습니다.")
        print("⚠️ Gemini API 키를 설정해야 합니다!")
        return True
    except Exception as e:
        print(f"❌ .env 파일 생성 실패: {e}")
        return False

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
        print(f"✅ {directory} 디렉토리 생성됨")
    
    return True

def check_python_version():
    """Python 버전 확인"""
    print("🐍 Python 버전 확인 중...")
    
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 이상이 필요합니다.")
        print(f"현재 버전: {sys.version}")
        return False
    
    print(f"✅ Python 버전: {sys.version}")
    return True

def main():
    """메인 함수"""
    print("🔧 JAVIS Multi-Agent System Setup")
    print("=" * 50)
    
    # Python 버전 확인
    if not check_python_version():
        return
    
    # 디렉토리 생성
    if not create_directories():
        return
    
    # 환경 변수 파일 생성
    if not create_env_file():
        return
    
    print("\n🎉 설정이 완료되었습니다!")
    print("=" * 50)
    print("다음 단계:")
    print("1. .env 파일에서 GEMINI_API_KEY를 설정하세요")
    print("2. pip install -r requirements.txt로 의존성을 설치하세요")
    print("3. python start.py로 RAG 시스템을 시작하세요")
    print("=" * 50)

if __name__ == "__main__":
    main()
