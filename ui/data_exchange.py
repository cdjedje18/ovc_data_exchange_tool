import customtkinter as ctk
from common.modules.data_exchange.data_exchange import get_programs, DataExchangeExecutionConfig, execute
from core.data_mapping.data_mapping import list_mappings as list_data_mappings, read_mapping as read_data_mapping
from core.location_mapping.location_mapping import list_mappings as list_location_mappings, read_mapping as read_location_mapping
from core.relationship_mapping.relationship_mapping import list_mappings as list_relationship_mappings, read_mapping as read_relationship_mapping
import sys
import threading
import queue


def _get_mapping_options(list_method):
    try:
        available = list_method()
        return ["<none>", *available] if available else ["<none>"]
    except Exception as e:
        print(f"[ERROR] Failed to load mappings: {e}")
        return ["<failed to load mappings>"]


def _get_default_mapping(options):
    return options[1] if len(options) > 1 and options[0] == "<none>" else (options[0] if options else "<none>")


def _load_selected_mapping(mapping_name: str, read_method, mapping_label: str):
    if not mapping_name or mapping_name.startswith("<none"):
        return None
    if mapping_name.startswith("<failed"):
        raise ValueError(f"{mapping_label} options could not be loaded")
    return read_method(mapping_name)


def _set_option_menu_values(option_menu, variable, options):
    current_value = variable.get()
    option_menu.configure(values=options)

    if current_value in options:
        variable.set(current_value)
    else:
        variable.set(_get_default_mapping(options))


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
    form_frame.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(form_frame, text="Program:").grid(row=0, column=0, sticky="w", pady=4)

    prog_list = []

    def load_program_options():
        nonlocal prog_list
        try:
            prog_list = get_programs()
            return [f"{p['name']} ({p['id']})" for p in prog_list]
        except Exception as e:
            print(f"[ERROR] Failed to load programs: {e}")
            prog_list = []
            return ["<failed to load programs>"]

    programs = load_program_options()
    selected_program = ctk.StringVar(value=programs[0] if programs else "")
    program_dropdown = ctk.CTkOptionMenu(form_frame, values=programs, variable=selected_program, width=220)
    program_dropdown.grid(row=0, column=1, pady=4, sticky="ew")

    def refresh_programs():
        options = load_program_options()
        _set_option_menu_values(program_dropdown, selected_program, options)
        append_log("[INFO] Program list refreshed")

    refresh_program_button = ctk.CTkButton(form_frame, text="↻", width=36, command=refresh_programs)
    refresh_program_button.grid(row=0, column=2, padx=(6, 0), pady=4)

    ctk.CTkLabel(form_frame, text="Page Size:").grid(row=1, column=0, sticky="w", pady=4)
    page_size_entry = ctk.CTkEntry(form_frame, width=220)
    page_size_entry.insert(0, "500")
    page_size_entry.grid(row=1, column=1, pady=4, sticky="ew")

    data_mapping_options = _get_mapping_options(list_data_mappings)
    selected_data_mapping = ctk.StringVar(value=_get_default_mapping(data_mapping_options))
    ctk.CTkLabel(form_frame, text="Data Mapping:").grid(row=2, column=0, sticky="w", pady=4)
    data_mapping_dropdown = ctk.CTkOptionMenu(form_frame, values=data_mapping_options, variable=selected_data_mapping, width=220)
    data_mapping_dropdown.grid(row=2, column=1, pady=4, sticky="ew")

    def refresh_data_mappings():
        options = _get_mapping_options(list_data_mappings)
        _set_option_menu_values(data_mapping_dropdown, selected_data_mapping, options)
        append_log("[INFO] Data mapping list refreshed")

    ctk.CTkButton(form_frame, text="↻", width=36, command=refresh_data_mappings).grid(row=2, column=2, padx=(6, 0), pady=4)

    location_mapping_options = _get_mapping_options(list_location_mappings)
    selected_location_mapping = ctk.StringVar(value=_get_default_mapping(location_mapping_options))
    ctk.CTkLabel(form_frame, text="Location Mapping:").grid(row=3, column=0, sticky="w", pady=4)
    location_mapping_dropdown = ctk.CTkOptionMenu(form_frame, values=location_mapping_options, variable=selected_location_mapping, width=220)
    location_mapping_dropdown.grid(row=3, column=1, pady=4, sticky="ew")

    def refresh_location_mappings():
        options = _get_mapping_options(list_location_mappings)
        _set_option_menu_values(location_mapping_dropdown, selected_location_mapping, options)
        append_log("[INFO] Location mapping list refreshed")

    ctk.CTkButton(form_frame, text="↻", width=36, command=refresh_location_mappings).grid(row=3, column=2, padx=(6, 0), pady=4)

    relationship_mapping_options = _get_mapping_options(list_relationship_mappings)
    selected_relationship_mapping = ctk.StringVar(value=_get_default_mapping(relationship_mapping_options))
    ctk.CTkLabel(form_frame, text="Relationship Mapping:").grid(row=4, column=0, sticky="w", pady=4)
    relationship_mapping_dropdown = ctk.CTkOptionMenu(form_frame, values=relationship_mapping_options, variable=selected_relationship_mapping, width=220)
    relationship_mapping_dropdown.grid(row=4, column=1, pady=4, sticky="ew")

    def refresh_relationship_mappings():
        options = _get_mapping_options(list_relationship_mappings)
        _set_option_menu_values(relationship_mapping_dropdown, selected_relationship_mapping, options)
        append_log("[INFO] Relationship mapping list refreshed")
        toggle_relationship_mapping_state()

    ctk.CTkButton(form_frame, text="↻", width=36, command=refresh_relationship_mappings).grid(row=4, column=2, padx=(6, 0), pady=4)

    def toggle_relationship_mapping_state():
        relationship_mapping_dropdown.configure(state="normal" if include_relationships_var.get() else "disabled")

    async_var = ctk.BooleanVar(value=False)
    ctk.CTkCheckBox(form_frame, text="Async import", variable=async_var).grid(row=5, column=0, columnspan=2, sticky="w", pady=4)

    include_relationships_var = ctk.BooleanVar(value=False)
    ctk.CTkCheckBox(
        form_frame,
        text="Include relationships",
        variable=include_relationships_var,
        command=toggle_relationship_mapping_state
    ).grid(row=6, column=0, columnspan=2, sticky="w", pady=4)
    toggle_relationship_mapping_state()

    run_button = ctk.CTkButton(form_frame, text="Run Data Exchange", width=180)
    run_button.grid(row=7, column=0, columnspan=2, pady=15)

    clear_button = ctk.CTkButton(form_frame, text="Clear Prints", width=180, command=lambda: log_text.delete('1.0', 'end'))
    clear_button.grid(row=8, column=0, columnspan=2, pady=(0, 15))

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

        try:
            variable_mapping = _load_selected_mapping(selected_data_mapping.get(), read_data_mapping, "Data mapping")
            orgunit_mapping = _load_selected_mapping(selected_location_mapping.get(), read_location_mapping, "Location mapping")
            relationship_mapping_config = None

            if include_relationships_var.get():
                relationship_mapping_config = _load_selected_mapping(
                    selected_relationship_mapping.get(),
                    read_relationship_mapping,
                    "Relationship mapping"
                )
        except Exception as e:
            append_log(f"[ERROR] Failed to load selected mappings: {e}")
            return

        if variable_mapping is None:
            append_log("[WARN] No data mapping selected; transformed payload may be empty.")

        if include_relationships_var.get() and relationship_mapping_config is None:
            append_log("[WARN] Relationships are enabled but no relationship mapping was selected.")

        append_log(
            f"[INFO] Starting DataExchangeExecution with program '{matching_program['name']}' ({matching_program['id']}), "
            f"pageSize={page_size}, async={async_var.get()}, dataMapping={selected_data_mapping.get()}, "
            f"locationMapping={selected_location_mapping.get()}, includeRelationships={include_relationships_var.get()}, "
            f"relationshipMapping={selected_relationship_mapping.get() if include_relationships_var.get() else '<ignored>'}"
        )

        execution_config = DataExchangeExecutionConfig(
            program=matching_program,
            page_size=page_size,
            async_import=async_var.get(),
            include_relationships=include_relationships_var.get(),
            variable_mapping=variable_mapping,
            orgunit_mapping=orgunit_mapping,
            relationship_mapping=relationship_mapping_config
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
