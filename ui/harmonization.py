import customtkinter as ctk
import threading
import queue
import sys
from entry_point import execute as run_harmonization_process


def create_harmonization_frame(parent, show_frame):
    frame = ctk.CTkFrame(parent)

    header = ctk.CTkFrame(frame)
    header.pack(fill="x", padx=15, pady=12)
    title = ctk.CTkLabel(header, text="Harmonization", font=ctk.CTkFont(size=20, weight="bold"))
    title.pack(side="left")
    back = ctk.CTkButton(header, text="Back", command=lambda: show_frame("home"))
    back.pack(side="right")

    content = ctk.CTkFrame(frame)
    content.pack(fill="both", expand=True, padx=15, pady=8)

    form_frame = ctk.CTkFrame(content)
    form_frame.pack(side="left", fill="y", padx=(0, 8), pady=4)

    run_button = ctk.CTkButton(form_frame, text="Run Harmonization", width=180)
    run_button.grid(row=0, column=0, columnspan=2, pady=15)

    clear_button = ctk.CTkButton(form_frame, text="Clear Logs", width=180, command=lambda: log_text.delete('1.0', 'end'))
    clear_button.grid(row=1, column=0, columnspan=2, pady=(0, 15))

    log_frame = ctk.CTkFrame(content)
    log_frame.pack(side="right", fill="both", expand=True, pady=4)
    log_text = ctk.CTkTextbox(log_frame, width=70, height=20)
    log_text.pack(fill="both", expand=True)

    log_queue = queue.Queue()

    def append_log(message: str):
        log_text.insert("end", f"{message}\n")
        log_text.see("end")

    def process_queue():
        try:
            while True:
                line = log_queue.get_nowait()
                append_log(line)
        except queue.Empty:
            pass
        parent.after(100, process_queue)

    def run_harmonization():
        append_log("[INFO] Starting Harmonization execute()")

        def worker():
            class StdoutCapture:
                def write(self, text):
                    if text.strip():
                        log_queue.put(text.strip())

                def flush(self):
                    pass

            old_stdout = sys.stdout
            sys.stdout = StdoutCapture()
            try:
                run_harmonization_process()
                log_queue.put("[SUCCESS] Harmonization execute() completed")
            except Exception as e:
                log_queue.put(f"[ERROR] Harmonization execute() failed: {e}")
            finally:
                sys.stdout = old_stdout

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    run_button.configure(command=run_harmonization)

    parent.after(100, process_queue)
    return frame
