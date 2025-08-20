#!/usr/bin/env python3
"""
Desktop Floating Chat Application
현재 화면에 플로팅 채팅 버튼을 추가하는 데스크톱 애플리케이션
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import requests
import json
import threading
from datetime import datetime
import os

class FloatingChatApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("JAVIS Floating Chat")
        
        # 한글 폰트 설정
        self.setup_korean_fonts()
        
        # API 설정
        self.API_BASE_URL = "http://localhost:8000"
        
        # 채팅 히스토리
        self.chat_history = []
        
        # 드래그 관련 변수
        self.drag_data = {"x": 0, "y": 0, "dragging": False}
        
        # 플로팅 버튼 생성
        self.create_floating_button()
        
        # 채팅창 생성 (초기에는 숨김)
        self.create_chat_window()
        
        # 항상 최상단에 표시
        self.root.attributes('-topmost', True)
        
        # ESC 키로 채팅창 닫기
        self.root.bind('<Escape>', self.close_chat_window)
    
    def setup_korean_fonts(self):
        """한글 폰트를 설정합니다."""
        # Windows에서 사용 가능한 한글 폰트들
        korean_fonts = [
            'Malgun Gothic',  # 맑은 고딕 (Windows 기본)
            'Nanum Gothic',   # 나눔고딕
            'Nanum Barun Gothic',  # 나눔바른고딕
            'Dotum',          # 돋움
            'Gulim',          # 굴림
            'Batang',         # 바탕
            'Arial Unicode MS'  # Arial Unicode MS
        ]
        
        # 사용 가능한 폰트 찾기
        self.default_font = 'Arial'  # 기본값
        for font in korean_fonts:
            try:
                # 폰트 존재 여부 확인
                test_label = tk.Label(self.root, font=(font, 12))
                test_label.destroy()
                self.default_font = font
                print(f"한글 폰트 설정: {font}")
                break
            except:
                continue
        
        # 폰트 크기 설정
        self.title_font = (self.default_font, 18, 'bold')
        self.subtitle_font = (self.default_font, 12)
        self.message_font = (self.default_font, 12)
        self.input_font = (self.default_font, 14)
        self.button_font = (self.default_font, 12, 'bold')
        self.emoji_font = (self.default_font, 22)
        
    def create_floating_button(self):
        """플로팅 버튼 생성"""
        # 메인 윈도우를 완전히 투명하게
        self.root.configure(bg='black')
        self.root.wm_attributes('-transparentcolor', 'black')
        
        # 윈도우 테두리와 제목 표시줄 제거
        self.root.overrideredirect(True)
        
        # 윈도우 크기를 버튼 크기로 설정 (더 크게)
        self.root.geometry('70x70')
        
        # 화면 우측 하단에 위치
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = screen_width - 100
        y = screen_height - 150
        self.root.geometry(f'70x70+{x}+{y}')
        
        # 동그란 버튼을 위한 캔버스 생성
        self.button_canvas = tk.Canvas(
            self.root,
            width=70,
            height=70,
            bg='black',
            highlightthickness=0,
            relief='flat'
        )
        self.button_canvas.pack(fill='both', expand=True)
        
        # 동그란 버튼 그리기 (더 크게)
        self.button_canvas.create_oval(
            3, 3, 67, 67,
            fill='#4f46e5',
            outline='#4f46e5',
            tags='button'
        )
        
        # 이모지 텍스트 추가 (더 크게)
        self.button_canvas.create_text(
            35, 35,
            text="💬",
            font=self.emoji_font,
            fill='white',
            tags='text'
        )
        
        # 클릭 이벤트 바인딩
        self.button_canvas.bind('<Button-1>', self.on_button_click)
        self.button_canvas.bind('<B1-Motion>', self.on_drag)
        self.button_canvas.bind('<ButtonRelease-1>', self.stop_drag)
        
        # 우클릭 메뉴 이벤트 바인딩
        self.button_canvas.bind('<Button-3>', self.show_context_menu)
        
        # 호버 효과
        self.button_canvas.bind('<Enter>', self.on_hover)
        self.button_canvas.bind('<Leave>', self.on_leave)
        
    def on_button_click(self, event):
        """버튼 클릭 이벤트"""
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        self.drag_data["dragging"] = False
        # 클릭 시 즉시 토글 실행하지 않고, 드래그 여부를 확인 후 실행
        
    def on_hover(self, event):
        """호버 효과"""
        self.button_canvas.itemconfig('button', fill='#4338ca')
        
    def on_leave(self, event):
        """호버 해제"""
        self.button_canvas.itemconfig('button', fill='#4f46e5')
        
    def on_drag(self, event):
        """드래그 중"""
        # 드래그 시작 시 dragging 플래그 설정
        if not self.drag_data["dragging"]:
            self.drag_data["dragging"] = True
            return
            
        # 마우스 커서를 정확히 따라가도록 수정
        # 현재 마우스 위치를 기준으로 윈도우 위치 계산
        mouse_x = self.root.winfo_pointerx()
        mouse_y = self.root.winfo_pointery()
        
        # 버튼 중앙이 마우스 커서 위치가 되도록 조정
        x = mouse_x - 35  # 버튼 중앙 (70/2)
        y = mouse_y - 35  # 버튼 중앙 (70/2)
        
        # 화면 경계 확인
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        if x < 0:
            x = 0
        elif x > screen_width - 70:
            x = screen_width - 70
            
        if y < 0:
            y = 0
        elif y > screen_height - 70:
            y = screen_height - 70
        
        self.root.geometry(f'70x70+{x}+{y}')
        
        # 드래그 데이터 업데이트
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        
    def stop_drag(self, event):
        """드래그 종료"""
        # 드래그가 아니었다면 클릭으로 간주하여 채팅창 토글
        if not self.drag_data["dragging"]:
            self.toggle_chat_window()
        self.drag_data["dragging"] = False
        
    def show_context_menu(self, event):
        """우클릭 컨텍스트 메뉴 표시"""
        # 팝업 메뉴 생성
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="옵션 설정", command=self.show_options)
        context_menu.add_separator()
        context_menu.add_command(label="시스템 종료", command=self.quit_system)
        
        # 메뉴를 마우스 위치에 표시
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
            
    def show_options(self):
        """옵션 설정 창 표시 (현재는 선택지만 표시)"""
        # 간단한 알림 창으로 옵션 설정 기능이 있다는 것을 표시
        import tkinter.messagebox as messagebox
        messagebox.showinfo("옵션 설정", "옵션 설정 기능은 현재 개발 중입니다.")
        
    def quit_system(self):
        """시스템 종료"""
        # 종료 확인
        import tkinter.messagebox as messagebox
        result = messagebox.askyesno("시스템 종료", "정말로 JAVIS를 종료하시겠습니까?")
        if result:
            # 프로그램 완전 종료
            self.root.quit()
            self.root.destroy()
            import sys
            sys.exit(0)
        
    def create_chat_window(self):
        """채팅창 생성"""
        # 채팅창 윈도우
        self.chat_window = tk.Toplevel(self.root)
        self.chat_window.title("JAVIS AI Assistant")
        self.chat_window.geometry('500x600')
        self.chat_window.configure(bg='white')
        
        # 버튼과 같은 위치에 배치
        button_x = self.root.winfo_x()
        button_y = self.root.winfo_y()
        self.chat_window.geometry(f'500x600+{button_x}+{button_y}')
        
        # 항상 최상단에 표시
        self.chat_window.attributes('-topmost', True)
        
        # 윈도우 크기 조정 방지
        self.chat_window.resizable(False, False)
        
        # 헤더
        header_frame = tk.Frame(self.chat_window, bg='#4f46e5', height=80)
        header_frame.pack(fill='x', padx=0, pady=0)
        header_frame.pack_propagate(False)
        
        # 제목
        title_label = tk.Label(
            header_frame,
            text="JAVIS AI Assistant",
            font=self.title_font,
            bg='#4f46e5',
            fg='white'
        )
        title_label.pack(side='left', padx=20, pady=20)
        
        # 부제목
        subtitle_label = tk.Label(
            header_frame,
            text="Multi-Agent System",
            font=self.subtitle_font,
            bg='#4f46e5',
            fg='#e0e7ff'
        )
        subtitle_label.pack(side='left', padx=20, pady=(0, 20))
        
        # 메시지 영역
        self.messages_frame = tk.Frame(self.chat_window, bg='white')
        self.messages_frame.pack(fill='both', expand=True, padx=15, pady=15)
        
        # 스크롤 가능한 메시지 영역
        self.messages_canvas = tk.Canvas(self.messages_frame, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.messages_frame, orient="vertical", command=self.messages_canvas.yview)
        self.scrollable_frame = tk.Frame(self.messages_canvas, bg='white')
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.messages_canvas.configure(scrollregion=self.messages_canvas.bbox("all"))
        )
        
        self.messages_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.messages_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.messages_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 입력 영역
        input_frame = tk.Frame(self.chat_window, bg='white', height=100)
        input_frame.pack(fill='x', padx=15, pady=15)
        input_frame.pack_propagate(False)
        
        # 메시지 입력
        self.message_input = tk.Entry(
            input_frame,
            font=self.input_font,
            relief='solid',
            borderwidth=2,
            bg='#f9fafb'
        )
        self.message_input.pack(side='left', fill='x', expand=True, padx=(0, 15))
        self.message_input.bind('<Return>', self.send_message)
        
        # 전송 버튼
        send_button = tk.Button(
            input_frame,
            text="전송",
            font=self.button_font,
            bg='#4f46e5',
            fg='white',
            relief='flat',
            cursor='hand2',
            command=self.send_message,
            width=8,
            height=2
        )
        send_button.pack(side='right')
        
        # 초기 메시지
        self.add_bot_message("안녕하세요! JAVIS AI Assistant입니다. 무엇을 도와드릴까요?")
        
        # 채팅창 초기에는 숨김
        self.chat_window.withdraw()
        
        # 채팅창 닫기 이벤트 바인딩
        self.chat_window.protocol("WM_DELETE_WINDOW", self.close_chat_window)
        
    def toggle_chat_window(self):
        """채팅창 토글"""
        if self.chat_window.state() == 'withdrawn':
            # 버튼 숨기기
            self.root.withdraw()
            # 채팅창을 버튼 위치에 표시 
            button_x = self.root.winfo_x() - 420
            button_y = self.root.winfo_y() - 550
            self.chat_window.geometry(f'500x600+{button_x}+{button_y}')
            self.chat_window.deiconify()
            self.message_input.focus()
        else:
            self.chat_window.withdraw()
            self.root.deiconify()
            
    def close_chat_window(self, event=None):
        """채팅창 닫기"""
        self.chat_window.withdraw()
        # 버튼 다시 표시
        self.root.deiconify()
        self.root.lift()  # 윈도우를 최상단으로 올림
        self.root.focus_force()  # 포커스 강제 설정
        
        # 약간의 지연 후 다시 한번 확인
        self.root.after(100, self.ensure_button_visible)
        
    def ensure_button_visible(self):
        """버튼이 확실히 보이도록 보장"""
        if not self.root.winfo_viewable():
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        
    def add_user_message(self, message):
        """사용자 메시지 추가"""
        message_frame = tk.Frame(self.scrollable_frame, bg='white')
        message_frame.pack(fill='x', pady=8)
        
        # 사용자 메시지 (우측 정렬)
        user_label = tk.Label(
            message_frame,
            text=message,
            font=self.message_font,
            bg='#eef2ff',
            fg='#111827',
            wraplength=350,
            justify='left',
            padx=15,
            pady=10,
            relief='flat'
        )
        user_label.pack(side='right', padx=(100, 0))
        
        # 스크롤을 맨 아래로
        self.messages_canvas.update_idletasks()
        self.messages_canvas.yview_moveto(1)
        
    def add_bot_message(self, message):
        """봇 메시지 추가"""
        message_frame = tk.Frame(self.scrollable_frame, bg='white')
        message_frame.pack(fill='x', pady=8)
        
        # 봇 메시지 (좌측 정렬)
        bot_label = tk.Label(
            message_frame,
            text="",
            font=self.message_font,
            bg='#f3f4f6',
            fg='#111827',
            wraplength=350,
            justify='left',
            padx=15,
            pady=10,
            relief='flat'
        )
        bot_label.pack(side='left', padx=(0, 100))
        
        # 스크롤을 맨 아래로
        self.messages_canvas.update_idletasks()
        self.messages_canvas.yview_moveto(1)
        
        # 타이핑 애니메이션 시작
        self.animate_typing(bot_label, message)
    
    def animate_typing(self, label, full_text, current_index=0):
        """타이핑 애니메이션을 실행합니다."""
        if current_index <= len(full_text):
            # 현재까지의 텍스트 표시
            current_text = full_text[:current_index]
            label.config(text=current_text)
            
            # 다음 글자로 진행
            if current_index < len(full_text):
                # 타이핑 속도 조절 (밀리초)
                typing_speed = 30  # 빠른 타이핑
                self.root.after(typing_speed, lambda: self.animate_typing(label, full_text, current_index + 1))
            
            # 스크롤을 맨 아래로 유지
            self.messages_canvas.update_idletasks()
            self.messages_canvas.yview_moveto(1)
    
    def show_loading_message(self):
        """로딩 메시지를 표시합니다."""
        message_frame = tk.Frame(self.scrollable_frame, bg='white')
        message_frame.pack(fill='x', pady=8)
        
        # 로딩 메시지 (좌측 정렬)
        loading_label = tk.Label(
            message_frame,
            text="답변을 생성하고 있습니다...",
            font=self.message_font,
            bg='#f3f4f6',
            fg='#6b7280',
            wraplength=350,
            justify='left',
            padx=15,
            pady=10,
            relief='flat'
        )
        loading_label.pack(side='left', padx=(0, 100))
        
        # 로딩 애니메이션 시작
        self.animate_loading(loading_label)
        
        # 스크롤을 맨 아래로
        self.messages_canvas.update_idletasks()
        self.messages_canvas.yview_moveto(1)
        
        return loading_label
    
    def animate_loading(self, label, dots=0):
        """로딩 애니메이션을 실행합니다."""
        dots_text = "." * (dots + 1)
        label.config(text=f"답변을 생성하고 있습니다{dots_text}")
        
        # 다음 애니메이션 프레임
        self.root.after(500, lambda: self.animate_loading(label, (dots + 1) % 4))
    
    def remove_loading_message(self, loading_label):
        """로딩 메시지를 제거합니다."""
        if loading_label and loading_label.winfo_exists():
            loading_label.master.destroy()
    
    def send_message(self, event=None):
        """메시지 전송"""
        message = self.message_input.get().strip()
        if not message:
            return
            
        # 입력창 초기화
        self.message_input.delete(0, tk.END)
        
        # 사용자 메시지 표시
        self.add_user_message(message)
        
        # 로딩 메시지 표시
        loading_label = self.show_loading_message()
        
        # 백그라운드에서 API 호출
        threading.Thread(target=self.get_bot_response, args=(message, loading_label), daemon=True).start()
        
    def get_bot_response(self, message, loading_label):
        """봇 응답 가져오기"""
        try:
            # API 호출 - Supervisor 기반 처리
            response = requests.post(
                f"{self.API_BASE_URL}/api/v2/process",
                json={"message": message, "user_id": 1},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                # Supervisor 응답 구조에 맞게 처리
                if result.get("success"):
                    bot_response = result.get("content", "응답을 처리할 수 없습니다.")
                else:
                    bot_response = result.get("content", "처리 중 오류가 발생했습니다.")
            else:
                bot_response = f"Error: {response.status_code} - {response.text}"
                
        except Exception as e:
            bot_response = "Sorry, I'm having trouble connecting to the server."
            
        # 메인 스레드에서 UI 업데이트
        self.root.after(0, lambda: self.handle_bot_response(bot_response, loading_label))
    
    def handle_bot_response(self, bot_response, loading_label):
        """봇 응답을 처리합니다."""
        # 로딩 메시지 제거
        self.remove_loading_message(loading_label)
        
        # 타이핑 애니메이션으로 봇 메시지 표시
        self.add_bot_message(bot_response)
        
    def run(self):
        """애플리케이션 실행"""
        self.root.mainloop()

def main():
    """메인 함수"""
    print("JAVIS Floating Chat Desktop App")
    print("=" * 50)
    print("화면 우측 하단에 플로팅 버튼이 나타납니다.")
    print("버튼을 클릭하면 채팅창이 열립니다.")
    print("버튼을 드래그하여 이동할 수 있습니다.")
    print("ESC 키로 채팅창을 닫을 수 있습니다.")
    print("=" * 50)
    
    app = FloatingChatApp()
    app.run()

if __name__ == "__main__":
    main()
