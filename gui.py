import customtkinter as ctk
import threading
import sys
import os
from pynput.keyboard import Key, Listener

# Import the core bot logic
from fishing_bot import FishingBot, load_config

class FishingBotGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("FiveM Fishing Bot")
        self.geometry("650x500")
        
        # Load Config
        try:
            self.cfg = load_config()
        except Exception as e:
            self.cfg = None
            print("Config load error:", e)

        # Bot instance
        self.bot = FishingBot(self.cfg, log_callback=self.log)
        
        # UI Elements
        self.setup_ui()
        
        # Setup hotkeys
        self.setup_hotkeys()
        
    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # Title & Disclaimer
        title = ctk.CTkLabel(self, text="FiveM Fishing Bot", font=ctk.CTkFont(size=24, weight="bold"))
        title.grid(row=0, column=0, pady=(20, 5))
        
        disclaimer_text = "Disclaimer: Calibrated for 2560x1600 resolution (auto-configured from config.json)"
        disclaimer = ctk.CTkLabel(self, text=disclaimer_text, text_color="gray")
        disclaimer.grid(row=1, column=0, pady=(0, 20))
        
        # Log Textbox
        self.log_box = ctk.CTkTextbox(self, state="disabled", font=("Consolas", 13), wrap="word")
        self.log_box.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        
        # Buttons Frame
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=3, column=0, pady=(0, 20))
        
        self.start_btn = ctk.CTkButton(
            btn_frame, text="▶ Start (F5)", fg_color="#2ecc71", hover_color="#27ae60", 
            text_color="white", font=ctk.CTkFont(weight="bold"), command=self.start_bot
        )
        self.start_btn.pack(side="left", padx=10)
        
        self.stop_btn = ctk.CTkButton(
            btn_frame, text="■ Stop (F11)", fg_color="#e74c3c", hover_color="#c0392b", 
            text_color="white", font=ctk.CTkFont(weight="bold"), command=self.stop_bot
        )
        self.stop_btn.pack(side="left", padx=10)
        
        self.log("=======================================================")
        self.log("  FiveM Fishing Bot — Vision-Based (GUI Mode)")
        self.log("=======================================================\n")
        self.log("Ready! Press Start or F5 to begin.")
        
    def log(self, text, end="\n"):
        # Schedule the UI update on the main thread (thread-safe for tkinter)
        self.after(0, self._append_log, text + end)
        
    def _append_log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        
    def start_bot(self):
        if not self.bot.running:
            self.bot.start()
            
    def stop_bot(self):
        if self.bot.running:
            self.bot.stop()
            
    def setup_hotkeys(self):
        def on_press(key):
            if key == Key.f5:
                self.after(0, self.start_bot)
            elif key == Key.f11:
                self.after(0, self.stop_bot)
            elif key == Key.f12:
                self.after(0, self.stop_bot)
                self.after(0, self.destroy)
                os._exit(0)
                
        self.listener = Listener(on_press=on_press)
        self.listener.start()

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    app = FishingBotGUI()
    app.mainloop()
