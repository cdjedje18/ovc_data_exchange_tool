import customtkinter as ctk
from common.modules.data_exchange.data_exchange import get_programs, DataExchangeExecutionConfig, execute
import sys
import threading
import queue


def create_data_exchange_frame(parent, show_frame):
    frame = ctk.CTkFrame(parent)

    header = ctk.CTkFrame(frame)
    header.pack(fill="x", padx=15, pady=12)
    title = ctk.CTkLabel(header, text="Data Exchange", font=ctk.CTkFont(size=20, weight="bold"))
    title.pack(side="left")
    back = ctk.CTkButton(header, text="Back", command=lambda: show_frame("home"))
    back.pack(side="right")

    content = ctk.CTkFrame(frame)
    content.pack(fill="both", expand=True, padx=15, pady=8)

    # Left form area
    form_frame = ctk.CTkFrame(content)
    form_frame.pack(side="left", fill="y", padx=(0, 8), pady=4)

    ctk.CTkLabel(form_frame, text="Program:").grid(row=0, column=0, sticky="w", pady=4)

    programs = []
    try:
        prog_list = get_programs()
        programs = [f"{p['name']} ({p['id']})" for p in prog_list]
    except Exception as e:
        programs = ["<failed to load programs>"]

    selected_program = ctk.StringVar(value=programs[0] if programs else "")
    program_dropdown = ctk.CTkOptionMenu(form_frame, values=programs, variable=selected_program)
    program_dropdown.grid(row=0, column=1, pady=4)

    ctk.CTkLabel(form_frame, text="Page Size:").grid(row=1, column=0, sticky="w", pady=4)
    page_size_entry = ctk.CTkEntry(form_frame, width=220)
    page_size_entry.insert(0, "500")
    page_size_entry.grid(row=1, column=1, pady=4)

    async_var = ctk.BooleanVar(value=True)
    ctk.CTkCheckBox(form_frame, text="Async import", variable=async_var).grid(row=2, column=0, columnspan=2, sticky="w", pady=4)

    run_button = ctk.CTkButton(form_frame, text="Run Data Exchange", width=180)
    run_button.grid(row=3, column=0, columnspan=2, pady=15)

    clear_button = ctk.CTkButton(form_frame, text="Clear Prints", width=180, command=lambda: log_text.delete('1.0', 'end'))
    clear_button.grid(row=4, column=0, columnspan=2, pady=(0, 15))

    # Right log area
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

    def run_data_exchange():
        if not selected_program.get() or selected_program.get().startswith("<failed"):
            append_log("[ERROR] Program must be selected and loaded correctly")
            return

        sel = selected_program.get()
        program_id = sel.split("(")[-1].strip(")") if "(" in sel else sel

        matching_program = next((p for p in prog_list if p['id'] == program_id), None)
        if not matching_program:
            append_log(f"[ERROR] Program not found: {program_id}")
            return

        try:
            page_size = int(page_size_entry.get().strip())
        except ValueError:
            append_log("[ERROR] Page size must be an integer")
            return

        append_log(f"[INFO] Starting DataExchangeExecution with program '{matching_program['name']}' ({matching_program['id']}), pageSize={page_size}, async={async_var.get()}")

        execution_config = DataExchangeExecutionConfig(
            program=matching_program,
            page_size=page_size,
            async_import=async_var.get()
        )

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
                execute(execution_config)
                log_queue.put("[SUCCESS] execute() completed")
            except Exception as e:
                log_queue.put(f"[ERROR] execute() failed: {e}")
            finally:
                sys.stdout = old_stdout

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    run_button.configure(command=run_data_exchange)

    parent.after(100, process_queue)
    return frame
