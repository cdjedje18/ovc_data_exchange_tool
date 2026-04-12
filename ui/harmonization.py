import customtkinter as ctk
import threading
import queue
import sys

from common.modules.extract_modules import extract_data
from common.modules.transform_modules import evaluators, transform_and_load
from common.modules.mixins.DataExchangeExecutionConfig import HarmonizationExecutionConfig
from core.helpers.orgunits import (
    get_organisation_units_by_level,
    get_organisation_units_by_parent_id,
)


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
    form_frame.grid_columnconfigure(1, weight=1)

    province_list = []
    district_list = []

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

    def run_selected_action(action_name: str, action):
        try:
            orgunits = get_selected_orgunits()
        except Exception as e:
            append_log(f"[ERROR] Failed to resolve organisation units: {e}")
            return

        append_log(
            f"[INFO] Starting {action_name} for province='{selected_province.get()}', "
            f"district='{selected_district.get()}', orgunits={len(orgunits)}"
        )

        def worker():
            class StdoutCapture:
                def write(self, text):
                    if text.strip():
                        for line in text.splitlines():
                            if line.strip():
                                log_queue.put(line.strip())

                def flush(self):
                    pass

            old_stdout = sys.stdout
            sys.stdout = StdoutCapture()
            try:
                action(orgunits=orgunits)
                log_queue.put(f"[SUCCESS] {action_name} completed")
            except Exception as e:
                log_queue.put(f"[ERROR] {action_name} failed: {e}")
            finally:
                sys.stdout = old_stdout

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    ctk.CTkLabel(form_frame, text="Province:").grid(row=0, column=0, sticky="w", pady=4)
    selected_province = ctk.StringVar(value="<All Provinces>")
    province_dropdown = ctk.CTkOptionMenu(
        form_frame,
        values=["<All Provinces>"],
        variable=selected_province,
        width=220,
        command=refresh_districts,
    )
    province_dropdown.grid(row=0, column=1, pady=4, sticky="ew")
    ctk.CTkButton(form_frame, text="↻", width=36, command=refresh_orgunits).grid(row=0, column=2, padx=(6, 0), pady=4)

    ctk.CTkLabel(form_frame, text="District:").grid(row=1, column=0, sticky="w", pady=4)
    selected_district = ctk.StringVar(value="<All Districts>")
    district_dropdown = ctk.CTkOptionMenu(
        form_frame,
        values=["<All Districts>"],
        variable=selected_district,
        width=220,
    )
    district_dropdown.grid(row=1, column=1, pady=4, sticky="ew")

    ctk.CTkLabel(form_frame, text="Beneficiary Program Server:").grid(row=2, column=0, sticky="w", pady=4)
    selected_beneficiary_server = ctk.StringVar(value="origin_server")
    beneficiary_server_dropdown = ctk.CTkOptionMenu(
        form_frame,
        values=["origin_server", "destiny_server"],
        variable=selected_beneficiary_server,
        width=220,
    )
    beneficiary_server_dropdown.grid(row=2, column=1, pady=4, sticky="ew")

    def _build_harmonization_config(orgunits):
        return HarmonizationExecutionConfig(
            page_size=500,
            beneficiary_program_server=selected_beneficiary_server.get(),
            orgunits=orgunits,
        )

    extract_button = ctk.CTkButton(
        form_frame,
        text="Extract Data",
        width=180,
        command=lambda: run_selected_action(
            "Extract data",
            lambda orgunits: extract_data.execute(_build_harmonization_config(orgunits)),
        ),
    )
    extract_button.grid(row=3, column=0, columnspan=2, pady=(15, 8))

    evaluate_button = ctk.CTkButton(
        form_frame,
        text="Evaluate",
        width=180,
        command=lambda: run_selected_action(
            "Evaluate",
            lambda orgunits: evaluators.execute(_build_harmonization_config(orgunits)),
        ),
    )
    evaluate_button.grid(row=4, column=0, columnspan=2, pady=8)

    harmonize_button = ctk.CTkButton(
        form_frame,
        text="Harmonize and Send",
        width=180,
        command=lambda: run_selected_action("Harmonize and Send", transform_and_load.execute),
    )
    harmonize_button.grid(row=5, column=0, columnspan=2, pady=8)

    clear_button = ctk.CTkButton(
        form_frame,
        text="Clear Logs",
        width=180,
        command=lambda: log_text.delete('1.0', 'end'),
    )
    clear_button.grid(row=6, column=0, columnspan=2, pady=(8, 15))

    refresh_orgunits()

    parent.after(100, process_queue)
    return frame
