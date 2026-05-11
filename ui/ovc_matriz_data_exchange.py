import customtkinter as ctk
import sys
import threading
import queue

from common.modules.mixins.DataExchangeExecutionConfig import MatrizDataExchangeExecutionConfig
from common.modules.ovc_data_exchange import matrix_exchange
from common.utils import utils
from core.helpers.orgunits import (
    get_organisation_units_by_level,
    get_organisation_units_by_parent_id,
)
from core.helpers.programs import get_program_data_elements
from common.modules.data_exchange.data_exchange import get_programs, create_client
from core.location_mapping.location_mapping import list_mappings as list_location_mappings, read_mapping as read_location_mapping
from core.data_mapping.data_mapping import list_mappings as list_data_mappings, read_mapping as read_data_mapping


PROVINCE_LEVEL = 2
DISTRICT_LEVEL = 3


def _format_orgunit_option(orgunit: dict) -> str:
    return f"{orgunit.get('name', '')} ({orgunit.get('id', '')})"


def _extract_orgunit_id(option: str):
    if not option or option.startswith("<"):
        return None
    if "(" in option and option.endswith(")"):
        return option.rsplit("(", 1)[-1].rstrip(")")
    return None


def _extract_id(option: str):
    if not option or option.startswith("<"):
        return None
    if "(" in option and option.endswith(")"):
        return option.rsplit("(", 1)[-1].rstrip(")")
    return None


def _get_mapping_options(list_method):
    try:
        available = list_method()
        return ["<none>", *available] if available else ["<none>"]
    except Exception as e:
        print(f"[ERROR] Failed to load mappings: {e}")
        return ["<failed to load mappings>"]


def _get_default_mapping(options):
    return options[1] if len(options) > 1 and options[0] == "<none>" else (options[0] if options else "<none>")


def _set_option_menu_values(option_menu, variable, options):
    current_value = variable.get()
    option_menu.configure(values=options)
    if current_value in options:
        variable.set(current_value)
    else:
        variable.set(_get_default_mapping(options))


def _load_selected_mapping(mapping_name: str, read_method, mapping_label: str):
    if not mapping_name or mapping_name.startswith("<none"):
        return None
    if mapping_name.startswith("<failed"):
        raise ValueError(f"{mapping_label} options could not be loaded")
    return read_method(mapping_name)


def create_ovc_matriz_data_exchange_frame(parent, show_frame):
    frame = ctk.CTkFrame(parent)

    # ── Header ──────────────────────────────────────────────────────────────
    header = ctk.CTkFrame(frame)
    header.pack(fill="x", padx=15, pady=12)
    ctk.CTkLabel(header, text="OVC Matriz Data Exchange", font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
    ctk.CTkButton(header, text="Back", command=lambda: show_frame("home")).pack(side="right")

    content = ctk.CTkFrame(frame)
    content.pack(fill="both", expand=True, padx=15, pady=8)

    # ── Left form ───────────────────────────────────────────────────────────
    form_frame = ctk.CTkFrame(content)
    form_frame.pack(side="left", fill="y", padx=(0, 8), pady=4)
    form_frame.grid_columnconfigure(1, weight=1)

    prog_list = []
    province_list = []
    district_list = []
    data_elements_list = []

    # ── Program helpers ─────────────────────────────────────────────────────
    def load_program_options():
        nonlocal prog_list
        try:
            prog_list = get_programs()
            return [f"{p['name']} ({p['id']})" for p in prog_list]
        except Exception as e:
            prog_list = []
            return ["<failed to load programs>"]

    def _find_program(option: str) -> dict | None:
        prog_id = _extract_id(option)
        return next((p for p in prog_list if p.get("id") == prog_id), None)

    programs = load_program_options()

    # ── Row 0 – Matriz Program ───────────────────────────────────────────────
    ctk.CTkLabel(form_frame, text="Matriz Program:").grid(row=0, column=0, sticky="w", pady=4)
    selected_matriz_program = ctk.StringVar(value=programs[0] if programs else "")
    matriz_program_dropdown = ctk.CTkOptionMenu(form_frame, values=programs, variable=selected_matriz_program, width=220)
    matriz_program_dropdown.grid(row=0, column=1, pady=4, sticky="ew")

    def refresh_programs():
        options = load_program_options()
        _set_option_menu_values(matriz_program_dropdown, selected_matriz_program, options)
        append_log("[INFO] Program list refreshed")

    ctk.CTkButton(form_frame, text="↻", width=36, command=refresh_programs).grid(row=0, column=2, padx=(6, 0), pady=4)

    # ── Data element loading helpers ─────────────────────────────────────────
    def _data_element_options(de_list: list) -> list[str]:
        if not de_list:
            return ["<none>"]
        return ["<none>", *[f"{de['name']} ({de['id']})" for de in de_list]]

    def load_matriz_data_elements(_=None):
        nonlocal data_elements_list
        program = _find_program(selected_matriz_program.get())
        if not program:
            data_elements_list = []
            _set_option_menu_values(matriz_waiver_dropdown, selected_matriz_waiver, ["<select a program first>"])
            return
        try:
            origin_client = create_client(config=utils.get_config_file()["originServer"])
            data_elements_list = get_program_data_elements(program=program, client=origin_client)
            options = _data_element_options(data_elements_list)
            _set_option_menu_values(matriz_waiver_dropdown, selected_matriz_waiver, options)
            append_log(f"[INFO] Matriz program data elements loaded ({len(data_elements_list)})")
        except Exception as e:
            data_elements_list = []
            append_log(f"[ERROR] Failed to load matriz data elements: {e}")

    # Reload data elements when program selection changes
    selected_matriz_program.trace_add("write", load_matriz_data_elements)

    # ── Row 1 – Matriz Waiver Data Element ───────────────────────────────────
    ctk.CTkLabel(form_frame, text="Matriz Waiver Data Element:").grid(row=1, column=0, sticky="w", pady=4)
    selected_matriz_waiver = ctk.StringVar(value="<none>")
    matriz_waiver_dropdown = ctk.CTkOptionMenu(form_frame, values=["<none>"], variable=selected_matriz_waiver, width=220)
    matriz_waiver_dropdown.grid(row=1, column=1, pady=4, sticky="ew")
    ctk.CTkButton(form_frame, text="↻", width=36, command=load_matriz_data_elements).grid(row=1, column=2, padx=(6, 0), pady=4)

    # ── Row 2 – Province ─────────────────────────────────────────────────────
    def load_provinces():
        nonlocal province_list
        province_list = get_organisation_units_by_level(PROVINCE_LEVEL)
        return ["<All Provinces>", *[_format_orgunit_option(item) for item in province_list]]

    def refresh_districts(_selected_value=None):
        nonlocal district_list
        province_id = _extract_orgunit_id(selected_province.get())
        try:
            if province_id:
                district_list = get_organisation_units_by_parent_id(parent_id=province_id)
            else:
                district_list = get_organisation_units_by_level(DISTRICT_LEVEL)
            options = ["<All Districts>", *[_format_orgunit_option(item) for item in district_list]]
            district_dropdown.configure(values=options)
            if selected_district.get() not in options:
                selected_district.set(options[0])
        except Exception as e:
            district_list = []
            selected_district.set("<failed to load districts>")
            district_dropdown.configure(values=["<failed to load districts>"])
            append_log(f"[ERROR] Failed to load districts: {e}")

    def refresh_orgunits():
        try:
            province_options = load_provinces()
            province_dropdown.configure(values=province_options)
            if selected_province.get() not in province_options:
                selected_province.set(province_options[0])
            refresh_districts()
            append_log("[INFO] Province and district lists refreshed")
        except Exception as e:
            selected_province.set("<failed to load provinces>")
            province_dropdown.configure(values=["<failed to load provinces>"])
            selected_district.set("<failed to load districts>")
            district_dropdown.configure(values=["<failed to load districts>"])
            append_log(f"[ERROR] Failed to load organisation units: {e}")

    def get_selected_orgunits():
        if selected_province.get().startswith("<failed") or selected_district.get().startswith("<failed"):
            raise ValueError("province/district options are not loaded correctly")
        district_id = _extract_orgunit_id(selected_district.get())
        province_id = _extract_orgunit_id(selected_province.get())
        if district_id:
            district = next((item for item in district_list if item.get("id") == district_id), None)
            if district:
                return [district]
            raise ValueError("selected district was not found in the loaded list")
        if province_id:
            return get_organisation_units_by_parent_id(parent_id=province_id)
        return get_organisation_units_by_level(DISTRICT_LEVEL)

    ctk.CTkLabel(form_frame, text="Province:").grid(row=2, column=0, sticky="w", pady=4)
    selected_province = ctk.StringVar(value="<All Provinces>")
    province_dropdown = ctk.CTkOptionMenu(
        form_frame, values=["<All Provinces>"], variable=selected_province,
        width=220, command=refresh_districts,
    )
    province_dropdown.grid(row=2, column=1, pady=4, sticky="ew")
    ctk.CTkButton(form_frame, text="↻", width=36, command=refresh_orgunits).grid(row=2, column=2, padx=(6, 0), pady=4)

    # ── Row 3 – District ─────────────────────────────────────────────────────
    ctk.CTkLabel(form_frame, text="District:").grid(row=3, column=0, sticky="w", pady=4)
    selected_district = ctk.StringVar(value="<All Districts>")
    district_dropdown = ctk.CTkOptionMenu(form_frame, values=["<All Districts>"], variable=selected_district, width=220)
    district_dropdown.grid(row=3, column=1, pady=4, sticky="ew")

    # ── Row 4 – Page Size ────────────────────────────────────────────────────
    ctk.CTkLabel(form_frame, text="Page Size:").grid(row=4, column=0, sticky="w", pady=4)
    page_size_entry = ctk.CTkEntry(form_frame, width=220)
    page_size_entry.insert(0, "500")
    page_size_entry.grid(row=4, column=1, pady=4, sticky="ew")

    # ── Row 5 – Data Mapping ─────────────────────────────────────────────────
    data_mapping_options = _get_mapping_options(list_data_mappings)
    selected_data_mapping = ctk.StringVar(value="<none>")
    ctk.CTkLabel(form_frame, text="Data Mapping:").grid(row=5, column=0, sticky="w", pady=4)
    data_mapping_dropdown = ctk.CTkOptionMenu(form_frame, values=data_mapping_options, variable=selected_data_mapping, width=220)
    data_mapping_dropdown.grid(row=5, column=1, pady=4, sticky="ew")

    def refresh_data_mappings():
        options = _get_mapping_options(list_data_mappings)
        _set_option_menu_values(data_mapping_dropdown, selected_data_mapping, options)
        append_log("[INFO] Data mapping list refreshed")

    ctk.CTkButton(form_frame, text="↻", width=36, command=refresh_data_mappings).grid(row=5, column=2, padx=(6, 0), pady=4)

    # ── Row 6 – Location Mapping ─────────────────────────────────────────────
    location_mapping_options = _get_mapping_options(list_location_mappings)
    selected_location_mapping = ctk.StringVar(value="<none>")
    ctk.CTkLabel(form_frame, text="Location Mapping:").grid(row=6, column=0, sticky="w", pady=4)
    location_mapping_dropdown = ctk.CTkOptionMenu(form_frame, values=location_mapping_options, variable=selected_location_mapping, width=220)
    location_mapping_dropdown.grid(row=6, column=1, pady=4, sticky="ew")

    def refresh_location_mappings():
        options = _get_mapping_options(list_location_mappings)
        _set_option_menu_values(location_mapping_dropdown, selected_location_mapping, options)
        append_log("[INFO] Location mapping list refreshed")

    ctk.CTkButton(form_frame, text="↻", width=36, command=refresh_location_mappings).grid(row=6, column=2, padx=(6, 0), pady=4)

    # ── Row 7 – Async checkbox ───────────────────────────────────────────────
    async_var = ctk.BooleanVar(value=False)
    ctk.CTkCheckBox(form_frame, text="Async import", variable=async_var).grid(row=7, column=0, columnspan=2, sticky="w", pady=4)

    # ── Row 8 – Run button ───────────────────────────────────────────────────
    run_button = ctk.CTkButton(form_frame, text="Run Matriz Exchange", width=220)
    run_button.grid(row=8, column=0, columnspan=2, pady=(12, 4))

    # ── Row 9 – Cancel button ────────────────────────────────────────────────
    cancel_button = ctk.CTkButton(form_frame, text="Cancel", width=220, state="disabled")
    cancel_button.grid(row=9, column=0, columnspan=2, pady=(0, 8))

    # ── Row 10 – Clear log button ─────────────────────────────────────────────
    ctk.CTkButton(
        form_frame, text="Clear Prints", width=220,
        command=lambda: log_text.delete("1.0", "end"),
    ).grid(row=10, column=0, columnspan=2, pady=(0, 15))

    # ── Right log area ───────────────────────────────────────────────────────
    log_frame = ctk.CTkFrame(content)
    log_frame.pack(side="right", fill="both", expand=True, pady=4)
    log_text = ctk.CTkTextbox(log_frame, width=70, height=20)
    log_text.pack(fill="both", expand=True)

    log_queue = queue.Queue()

    def append_log(message: str):
        log_text.insert("end", f"{message}\n")
        log_text.see("end")

    # ── Thread state ─────────────────────────────────────────────────────────
    exchange_thread = None
    cancel_event = None

    def process_queue():
        nonlocal exchange_thread, cancel_event
        try:
            while True:
                append_log(log_queue.get_nowait())
        except queue.Empty:
            pass

        if exchange_thread is not None and not exchange_thread.is_alive():
            run_button.configure(state="normal")
            cancel_button.configure(state="disabled")
            exchange_thread = None
            cancel_event = None

        parent.after(100, process_queue)

    # ── Config builder ────────────────────────────────────────────────────────
    def _build_execution_config():
        matriz_program = _find_program(selected_matriz_program.get())
        if not matriz_program:
            append_log("[ERROR] Matriz program must be selected and loaded correctly")
            return None

        matriz_waiver_id = _extract_id(selected_matriz_waiver.get())
        if not matriz_waiver_id:
            append_log("[ERROR] Matriz waiver data element must be selected")
            return None

        try:
            page_size = int(page_size_entry.get().strip())
        except ValueError:
            append_log("[ERROR] Page size must be an integer")
            return None

        try:
            orgunits = get_selected_orgunits()
        except Exception as e:
            append_log(f"[ERROR] Failed to resolve organisation units: {e}")
            return None

        if not orgunits:
            append_log("[WARN] No organisation units matched the selected province/district.")
            return None

        try:
            variable_mapping = _load_selected_mapping(selected_data_mapping.get(), read_data_mapping, "Data mapping")
            orgunit_mapping = _load_selected_mapping(selected_location_mapping.get(), read_location_mapping, "Location mapping")
        except Exception as e:
            append_log(f"[ERROR] Failed to load selected mappings: {e}")
            return None

        return MatrizDataExchangeExecutionConfig(
            matriz_program=matriz_program,
            matriz_waiver_data_element=matriz_waiver_id,
            page_size=page_size,
            async_import=async_var.get(),
            variable_mapping=variable_mapping,
            orgunit_mapping=orgunit_mapping,
            orgunits=orgunits,
        )

    # ── Worker ────────────────────────────────────────────────────────────────
    def _make_worker(execution_config, ev):
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
                matrix_exchange.execute(execution_config=execution_config, cancel_event=ev)
                if ev.is_set():
                    log_queue.put("[INFO] Matriz Exchange cancelled")
                else:
                    log_queue.put("[SUCCESS] Matriz Exchange completed")
            except Exception as e:
                log_queue.put(f"[ERROR] Matriz Exchange failed: {e}")
            finally:
                sys.stdout = old_stdout
        return worker

    # ── Run / Cancel ──────────────────────────────────────────────────────────
    def run_matriz_exchange():
        nonlocal exchange_thread, cancel_event

        if exchange_thread is not None and exchange_thread.is_alive():
            append_log("[WARN] Matriz exchange is already running.")
            return

        execution_config = _build_execution_config()
        if execution_config is None:
            return

        append_log(
            f"[INFO] Starting Matriz Exchange | program='{execution_config.matriz_program['name']}' "
            f"| orgunits={len(execution_config.orgunits)} | pageSize={execution_config.page_size} "
            f"| async={execution_config.async_import}"
        )

        run_button.configure(state="disabled")
        cancel_button.configure(state="normal")
        cancel_event = threading.Event()

        exchange_thread = threading.Thread(
            target=_make_worker(execution_config, cancel_event),
            daemon=True,
        )
        exchange_thread.start()

    def cancel_matriz_exchange():
        if cancel_event:
            cancel_event.set()
            append_log("[INFO] Cancellation requested for Matriz Exchange.")

    run_button.configure(command=run_matriz_exchange)
    cancel_button.configure(command=cancel_matriz_exchange)

    # ── Boot ─────────────────────────────────────────────────────────────────
    refresh_orgunits()
    parent.after(100, process_queue)

    return frame
