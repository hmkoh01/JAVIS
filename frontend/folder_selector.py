#!/usr/bin/env python3
"""
Folder Selection UI
시스템 시작 시 폴더 선택을 위한 독립적인 UI
"""

import tkinter as tk
from tkinter import ttk, messagebox
import requests
import threading
import time
import logging
import queue  # 1. queue 모듈 추가

logger = logging.getLogger(__name__)

class FolderSelector:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("JAVIS - 폴더 선택")
        self.root.geometry('850x750')
        self.root.configure(bg='#f8fafc')
        self.root.resizable(True, True)
        self.root.minsize(750, 650)
        
        self.center_window()
        self.setup_korean_fonts()
        
        self.API_BASE_URL = "http://localhost:8000"
        self.selected_folders = None
        self.folder_data = []

        # 2. 스레드 통신을 위한 큐 생성 (크기 제한으로 메모리 보호)
        self.folder_queue = queue.Queue(maxsize=10)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.create_ui()
        
        # 3. 초기 로딩 메시지 표시
        self.show_loading_message()
        
        # 4. 폴더 로딩 및 큐 확인 시작 (안전한 초기화)
        try:
            self.load_folders()
            self.process_queue()
        except Exception as e:
            logger.error(f"초기화 중 오류: {e}")
            # 초기화 실패 시에도 기본 상태 메시지 표시
            try:
                self.status_label.config(text="❌ 초기화 중 오류가 발생했습니다.")
            except:
                pass
    
    def center_window(self):
        """창을 화면 중앙에 배치"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        
        # 화면 크기 가져오기
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 정확한 중앙 계산 (소수점 고려)
        x = int((screen_width - width) / 2)
        y = int((screen_height - height) / 2)
        
        # 최소값 보장 (화면 밖으로 나가지 않도록)
        x = max(0, x)
        y = max(0, y)
        
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
        # 창을 최상단으로 가져오기
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after_idle(lambda: self.root.attributes('-topmost', False))
    
    def setup_korean_fonts(self):
        """한글 폰트를 설정합니다."""
        korean_fonts = [
            'Malgun Gothic', 'Nanum Gothic', 'Nanum Barun Gothic',
            'Dotum', 'Gulim', 'Batang', 'Arial Unicode MS'
        ]
        
        self.default_font = 'Arial'
        for font in korean_fonts:
            try:
                test_label = tk.Label(self.root, font=(font, 12))
                test_label.destroy()
                self.default_font = font
                break
            except:
                continue
        
        self.title_font = (self.default_font, 20, 'bold')
        self.subtitle_font = (self.default_font, 14)
        self.message_font = (self.default_font, 12)
        self.button_font = (self.default_font, 12, 'bold')
    
    def create_ui(self):
        """UI를 생성합니다."""
        # 메인 컨테이너 프레임 (그라데이션 효과를 위한 배경)
        main_container = tk.Frame(self.root, bg='#f8fafc')
        main_container.pack(fill='both', expand=True)
        
        # 중앙 정렬을 위한 프레임
        center_frame = tk.Frame(main_container, bg='#f8fafc')
        center_frame.pack(expand=True, fill='both')
        
        # 메인 카드 스타일 프레임
        main_frame = tk.Frame(center_frame, bg='white', relief='flat', bd=0)
        main_frame.pack(expand=True, fill='both', padx=40, pady=40)
        
        # 그림자 효과를 위한 추가 프레임
        shadow_frame = tk.Frame(main_frame, bg='#e2e8f0', height=2)
        shadow_frame.pack(fill='x', side='bottom')
        
        # 상단 헤더 영역
        header_frame = tk.Frame(main_frame, bg='white')
        header_frame.pack(fill='x', padx=30, pady=(30, 20))
        
        # 아이콘과 제목을 위한 프레임
        title_frame = tk.Frame(header_frame, bg='white')
        title_frame.pack(fill='x')
        
        # 폴더 아이콘 (유니코드 이모지 사용)
        icon_label = tk.Label(
            title_frame,
            text="📁",
            font=('Arial', 32),
            bg='white',
            fg='#4f46e5'
        )
        icon_label.pack(side='left', padx=(0, 15))
        
        # 제목과 설명을 위한 프레임
        text_frame = tk.Frame(title_frame, bg='white')
        text_frame.pack(side='left', fill='x', expand=True)
        
        title_label = tk.Label(
            text_frame,
            text="JAVIS 파일 수집",
            font=('Malgun Gothic', 24, 'bold'),
            bg='white',
            fg='#1f2937'
        )
        title_label.pack(anchor='w')
        
        subtitle_label = tk.Label(
            text_frame,
            text="폴더 선택",
            font=('Malgun Gothic', 16),
            bg='white',
            fg='#6b7280'
        )
        subtitle_label.pack(anchor='w')
        
        # 설명 영역
        desc_frame = tk.Frame(main_frame, bg='white')
        desc_frame.pack(fill='x', padx=30, pady=(0, 25))
        
        desc_label = tk.Label(
            desc_frame,
            text="파일 수집할 폴더를 선택하세요.\nC:\\Users\\koh\\Desktop 폴더 내의 폴더들이 표시됩니다.\n선택하지 않으면 전체 폴더를 스캔합니다.",
            font=('Malgun Gothic', 12),
            bg='white',
            fg='#6b7280',
            wraplength=650,
            justify='left'
        )
        desc_label.pack(anchor='w')
        
        # 폴더 목록 영역
        list_container = tk.Frame(main_frame, bg='white')
        list_container.pack(fill='both', expand=True, padx=30, pady=(0, 25))
        
        # 폴더 목록 헤더
        list_header = tk.Frame(list_container, bg='#f8fafc', relief='flat', bd=1)
        list_header.pack(fill='x', pady=(0, 10))
        
        header_label = tk.Label(
            list_header,
            text="📂 사용 가능한 폴더",
            font=('Malgun Gothic', 14, 'bold'),
            bg='#f8fafc',
            fg='#374151',
            pady=10
        )
        header_label.pack(side='left', padx=15)
        
        # 폴더 목록 프레임 (카드 스타일)
        list_frame = tk.Frame(list_container, bg='#f8fafc', relief='flat', bd=1)
        list_frame.pack(fill='both', expand=True)
        
        # 스크롤바
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical')
        scrollbar.pack(side='right', fill='y', padx=(0, 5), pady=5)
        
        # 리스트박스 (더 모던한 스타일)
        self.folder_listbox = tk.Listbox(
            list_frame,
            font=('Malgun Gothic', 11),
            selectmode='multiple',
            yscrollcommand=scrollbar.set,
            bg='white',
            fg='#1f2937',
            selectbackground='#4f46e5',
            selectforeground='white',
            relief='flat',
            bd=0,
            highlightthickness=0,
            activestyle='none',
            height=12
        )
        self.folder_listbox.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        
        scrollbar.config(command=self.folder_listbox.yview)
        
        # 버튼 영역
        button_container = tk.Frame(main_frame, bg='white')
        button_container.pack(fill='x', padx=30, pady=(0, 30))
        
        # 왼쪽 버튼들 (유틸리티)
        left_buttons = tk.Frame(button_container, bg='white')
        left_buttons.pack(side='left')
        
        # 새로고침 버튼
        refresh_button = tk.Button(
            left_buttons, 
            text="🔄 새로고침", 
            font=('Malgun Gothic', 10, 'bold'), 
            bg='#6b7280', 
            fg='white',
            relief='flat', 
            bd=0,
            cursor='hand2', 
            command=self.load_folders, 
            width=13,
            pady=10,
            activebackground='#4b5563',
            activeforeground='white'
        )
        refresh_button.pack(side='left', padx=(0, 8))
        
        # 전체 선택 버튼
        select_all_button = tk.Button(
            left_buttons, 
            text="✅ 전체 선택", 
            font=('Malgun Gothic', 10, 'bold'), 
            bg='#059669', 
            fg='white',
            relief='flat', 
            bd=0,
            cursor='hand2', 
            command=self.select_all_folders, 
            width=13,
            pady=10,
            activebackground='#047857',
            activeforeground='white'
        )
        select_all_button.pack(side='left', padx=(0, 8))
        
        # 선택 해제 버튼
        deselect_all_button = tk.Button(
            left_buttons, 
            text="❌ 선택 해제", 
            font=('Malgun Gothic', 10, 'bold'), 
            bg='#dc2626', 
            fg='white',
            relief='flat', 
            bd=0,
            cursor='hand2', 
            command=self.deselect_all_folders, 
            width=13,
            pady=10,
            activebackground='#b91c1c',
            activeforeground='white'
        )
        deselect_all_button.pack(side='left')
        
        # 오른쪽 버튼들 (액션)
        right_buttons = tk.Frame(button_container, bg='white')
        right_buttons.pack(side='right')
        
        # 전체 스캔 버튼
        full_scan_button = tk.Button(
            right_buttons, 
            text="💾 전체 스캔", 
            font=('Malgun Gothic', 10, 'bold'), 
            bg='#7c3aed', 
            fg='white',
            relief='flat', 
            bd=0,
            cursor='hand2', 
            command=self.select_full_drive, 
            width=14,
            pady=10,
            activebackground='#6d28d9',
            activeforeground='white'
        )
        full_scan_button.pack(side='right', padx=(8, 0))
        
        # 확인 버튼 (주요 액션)
        confirm_button = tk.Button(
            right_buttons, 
            text="🚀 시작하기", 
            font=('Malgun Gothic', 12, 'bold'), 
            bg='#4f46e5', 
            fg='white',
            relief='flat', 
            bd=0,
            cursor='hand2', 
            command=self.confirm_selection, 
            width=16,
            pady=12,
            activebackground='#4338ca',
            activeforeground='white'
        )
        confirm_button.pack(side='right')
        
        # 상태 표시 영역
        status_frame = tk.Frame(main_frame, bg='#f0f9ff', relief='flat', bd=1)
        status_frame.pack(fill='x', padx=30, pady=(0, 30))
        
        self.status_label = tk.Label(
            status_frame, 
            text="⏳ 폴더 목록을 불러오는 중...", 
            font=('Malgun Gothic', 11),
            bg='#f0f9ff', 
            fg='#0369a1',
            pady=12
        )
        self.status_label.pack()
    
    def load_folders(self):
        """서버에서 폴더 목록을 로드합니다. (백그라운드 스레드 시작)"""
        # 메인 스레드에서만 UI 업데이트
        self.status_label.config(text="⏳ 폴더 목록을 불러오는 중...")
        # 로딩 메시지 표시
        self.show_loading_message()
        # 백그라운드 스레드 시작
        thread = threading.Thread(target=self.load_in_background, daemon=True)
        thread.start()

    def load_in_background(self):
        """백그라운드 스레드에서 실행될 함수 - UI를 직접 건드리지 않음"""
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                logger.info(f"API 호출 시도: {self.API_BASE_URL}/api/v2/data-collection/folders")
                response = requests.get(f"{self.API_BASE_URL}/api/v2/data-collection/folders", timeout=10)
                
                logger.info(f"응답 상태 코드: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        folders = result.get("folders", [])
                        # 백그라운드 스레드에서는 큐에만 데이터를 넣음 (UI 직접 업데이트 X)
                        try:
                            self.folder_queue.put({'status': 'success', 'data': folders}, timeout=2)
                        except queue.Full:
                            logger.warning("큐가 가득 참 - 메시지 드롭")
                        return

                # 실패 시 큐에 에러 메시지 전달
                try:
                    self.folder_queue.put({'status': 'error', 'message': f"폴더 목록 로드 실패 (코드: {response.status_code})"}, timeout=2)
                except queue.Full:
                    logger.warning("큐가 가득 참 - 에러 메시지 드롭")
                return
                
            except requests.exceptions.ConnectionError:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    try:
                        self.folder_queue.put({'status': 'error', 'message': "서버에 연결할 수 없습니다. 백엔드가 실행 중인지 확인하세요."}, timeout=2)
                    except queue.Full:
                        logger.warning("큐가 가득 참 - 연결 에러 메시지 드롭")
            except Exception as e:
                logger.error(f"폴더 로딩 중 예외 발생: {e}")
                try:
                    self.folder_queue.put({'status': 'error', 'message': f"알 수 없는 오류 발생: {str(e)}"}, timeout=2)
                except queue.Full:
                    logger.warning("큐가 가득 참 - 예외 메시지 드롭")
                
    def process_queue(self):
        """큐를 주기적으로 확인하여 UI를 안전하게 업데이트합니다. (메인 스레드에서만 실행)"""
        try:
            # 큐에서 메시지를 안전하게 가져오기
            message = self.folder_queue.get_nowait()
            
            # 메인 스레드에서 안전하게 UI 업데이트
            if message['status'] == 'success':
                folders = message['data']
                self.populate_folder_list(folders)
                if folders:
                    self.status_label.config(text=f"✅ 폴더 목록을 불러왔습니다. ({len(folders)}개 폴더)")
                else:
                    self.status_label.config(text="📂 표시할 폴더가 없습니다.")
            elif message['status'] == 'error':
                self.status_label.config(text=f"❌ {message['message']}")

        except queue.Empty:
            pass  # 큐가 비어있으면 아무것도 하지 않음
        except Exception as e:
            logger.error(f"큐 처리 중 오류: {e}")
        finally:
            # 메인 스레드의 after() 메서드를 사용하여 안전하게 재귀 호출
            try:
                self.root.after(100, self.process_queue)
            except tk.TclError:
                # 윈도우가 파괴된 경우 중지
                logger.info("윈도우가 파괴됨 - 큐 처리 중지")
                return

    def populate_folder_list(self, folders):
        """폴더 목록을 리스트박스에 채웁니다."""
        self.folder_listbox.delete(0, tk.END)
        self.folder_data.clear()
        
        if not folders:
            # 폴더가 없는 경우 안내 메시지
            self.folder_listbox.insert(tk.END, "📂 표시할 폴더가 없습니다.")
            return
        
        for folder in sorted(folders, key=lambda x: x.get('name', '').lower()):
            name = folder.get('name', '')
            path = folder.get('path', '')
            size = folder.get('size', 0)
            
            # 크기를 읽기 쉬운 형태로 변환
            if size > 1024 * 1024 * 1024:
                size_str = f"{size / (1024 * 1024 * 1024):.1f} GB"
            elif size > 1024 * 1024:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            elif size > 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size} bytes"
            
            # 폴더 아이콘과 함께 표시
            display_text = f"📁 {name}    ({size_str})"
            self.folder_listbox.insert(tk.END, display_text)
            self.folder_data.append(path)
    
    def show_loading_message(self):
        """로딩 중 메시지를 표시합니다."""
        self.folder_listbox.delete(0, tk.END)
        self.folder_data.clear()
        
        # 로딩 애니메이션을 위한 메시지들
        loading_messages = [
            "⏳ 폴더를 검색하는 중입니다...",
            "🔍 C:\\Users\\koh\\Desktop 폴더를 스캔하고 있습니다...",
            "📁 폴더 정보를 수집하는 중입니다...",
            "⏳ 잠시만 기다려주세요..."
        ]
        
        # 첫 번째 로딩 메시지 표시
        self.folder_listbox.insert(tk.END, loading_messages[0])
        
        # 로딩 애니메이션 시작
        self.loading_index = 0
        self.animate_loading()
    
    def animate_loading(self):
        """로딩 메시지 애니메이션"""
        loading_messages = [
            "⏳ 폴더를 검색하는 중입니다...",
            "🔍 C:\\Users\\koh\\Desktop 폴더를 스캔하고 있습니다...",
            "📁 폴더 정보를 수집하는 중입니다...",
            "⏳ 잠시만 기다려주세요..."
        ]
        
        if hasattr(self, 'folder_listbox') and self.folder_listbox.size() == 1:
            # 아직 로딩 중인 경우에만 애니메이션 계속
            self.folder_listbox.delete(0, tk.END)
            self.folder_listbox.insert(tk.END, loading_messages[self.loading_index])
            self.loading_index = (self.loading_index + 1) % len(loading_messages)
            
            # 2초마다 메시지 변경
            self.root.after(2000, self.animate_loading)
    
    def select_all_folders(self):
        """모든 폴더를 선택합니다."""
        self.folder_listbox.select_set(0, tk.END)
    
    def deselect_all_folders(self):
        """모든 폴더 선택을 해제합니다."""
        self.folder_listbox.select_clear(0, tk.END)
    
    def select_full_drive(self):
        """전체 C드라이브 스캔을 선택합니다."""
        result = messagebox.askyesno("전체 스캔", "전체 C드라이브를 스캔하시겠습니까?\n시간이 오래 걸릴 수 있습니다.")
        if result:
            self.selected_folders = None
            self.root.quit()
    
    def confirm_selection(self):
        """선택된 폴더를 확인하고 데이터 수집을 시작합니다."""
        selected_indices = self.folder_listbox.curselection()
        
        if not selected_indices:
            result = messagebox.askyesno("전체 스캔", "폴더를 선택하지 않았습니다.\n전체 C드라이브를 스캔하시겠습니까?")
            if result:
                self.selected_folders = None
                self.root.quit()
            else:
                return
        else:
            self.selected_folders = [self.folder_data[i] for i in selected_indices]
            self.root.quit()
    
    def on_closing(self):
        """창 닫기 시 확인"""
        result = messagebox.askyesno("종료", "폴더 선택을 취소하고 시스템을 종료하시겠습니까?")
        if result:
            try:
                # 큐 정리
                while not self.folder_queue.empty():
                    try:
                        self.folder_queue.get_nowait()
                    except queue.Empty:
                        break
            except Exception as e:
                logger.error(f"정리 작업 중 오류: {e}")
            finally:
                self.selected_folders = "cancelled"
                self.root.quit()
    
    def run(self):
        """폴더 선택 UI를 실행합니다."""
        try:
            self.root.mainloop()
        except Exception as e:
            logger.error(f"UI 실행 중 오류: {e}")
        finally:
            # 안전하게 창 정리
            try:
                if self.root.winfo_exists():
                    self.root.destroy()
            except tk.TclError:
                pass  # 이미 파괴된 경우 무시
        return self.selected_folders

def select_folders():
    """폴더 선택 UI를 실행하고 선택된 폴더를 반환합니다."""
    try:
        app = FolderSelector()
        return app.run()
    except Exception as e:
        logger.error(f"폴더 선택 UI 오류: {e}")
        return "cancelled"