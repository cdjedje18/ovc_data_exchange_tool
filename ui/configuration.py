import customtkinter as ctk
from common.utils import config_utils
from common.modules.data_exchange.data_exchange import create_client


def _format_program_option(program: dict) -> str:
    return f"{program.get('name', '')} ({program.get('id', '')})"


def _extract_program_id(option: str):
    if not option or option.startswith("<"):
        return None

    if "(" in option and option.endswith(")"):
        return option.rsplit("(", 1)[-1].rstrip(")")

    return None


def _load_destiny_program_options(server_config: dict):
    if not server_config.get("url") or not server_config.get("username") or not server_config.get("pass"):
        return [], ["<configure destiny server first>"]

    client = create_client(config=server_config)
    programs = client.get("/api/programs", params={"fields": "id,name,programType", "paging": False}).get("programs", [])
    options = ["<none>", *[_format_program_option(program) for program in programs]]
    return programs, options


def _set_option_menu_values(option_menu, variable, options, fallback="<none>"):
    option_menu.configure(values=options)

    current_value = variable.get()
    if current_value in options:
        variable.set(current_value)
        return

    if fallback in options:
        variable.set(fallback)
        return

    variable.set(options[0] if options else fallback)


def create_configuration_frame(parent, show_frame):
    frame = ctk.CTkFrame(parent)

    header = ctk.CTkFrame(frame)
    header.pack(fill="x", padx=15, pady=12)
    title = ctk.CTkLabel(header, text="Configuration", font=ctk.CTkFont(size=20, weight="bold"))
    title.pack(side="left")
    back = ctk.CTkButton(header, text="Back", command=lambda: show_frame("home"))
    back.pack(side="right")

    content_frame = ctk.CTkScrollableFrame(frame)
    content_frame.pack(fill="both", expand=True, padx=15, pady=(0, 12))

    config = config_utils.load_config()

    # Origin server settings
    origin_frame = ctk.CTkFrame(content_frame)
    origin_frame.pack(padx=5, pady=8, fill="x")

    ctk.CTkLabel(origin_frame, text="Origin Server", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0, 5))

    ctk.CTkLabel(origin_frame, text="URL").pack(anchor="w", padx=2)
    origin_url = ctk.CTkEntry(origin_frame)
    origin_url.pack(fill="x", pady=2)
    origin_url.insert(0, config.get("originServer", {}).get("url", ""))

    ctk.CTkLabel(origin_frame, text="Username").pack(anchor="w", padx=2)
    origin_username = ctk.CTkEntry(origin_frame)
    origin_username.pack(fill="x", pady=2)
    origin_username.insert(0, config.get("originServer", {}).get("username", ""))

    ctk.CTkLabel(origin_frame, text="Password").pack(anchor="w", padx=2)
    origin_password = ctk.CTkEntry(origin_frame, show="*")
    origin_password.pack(fill="x", pady=2)
    origin_password.insert(0, config.get("originServer", {}).get("pass", ""))

    # Destiny server settings
    destiny_frame = ctk.CTkFrame(content_frame)
    destiny_frame.pack(padx=5, pady=8, fill="x")

    ctk.CTkLabel(destiny_frame, text="Destiny Server", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0, 5))

    ctk.CTkLabel(destiny_frame, text="URL").pack(anchor="w", padx=2)
    destiny_url = ctk.CTkEntry(destiny_frame)
    destiny_url.pack(fill="x", pady=2)
    destiny_url.insert(0, config.get("destinyServer", {}).get("url", ""))

    ctk.CTkLabel(destiny_frame, text="Username").pack(anchor="w", padx=2)
    destiny_username = ctk.CTkEntry(destiny_frame)
    destiny_username.pack(fill="x", pady=2)
    destiny_username.insert(0, config.get("destinyServer", {}).get("username", ""))

    ctk.CTkLabel(destiny_frame, text="Password").pack(anchor="w", padx=2)
    destiny_password = ctk.CTkEntry(destiny_frame, show="*")
    destiny_password.pack(fill="x", pady=2)
    destiny_password.insert(0, config.get("destinyServer", {}).get("pass", ""))

    ctk.CTkLabel(destiny_frame, text="Matrix Program").pack(anchor="w", padx=2)
    destiny_programs = []
    selected_matrix_program = ctk.StringVar(value="<none>")
    matrix_program_dropdown = ctk.CTkOptionMenu(
        destiny_frame,
        values=["<none>"],
        variable=selected_matrix_program,
    )
    matrix_program_dropdown.pack(fill="x", pady=2)

    ctk.CTkLabel(destiny_frame, text="Beneficiary Program").pack(anchor="w", padx=2)
    selected_beneficiary_program = ctk.StringVar(value="<none>")
    beneficiary_program_dropdown = ctk.CTkOptionMenu(
        destiny_frame,
        values=["<none>"],
        variable=selected_beneficiary_program,
    )
    beneficiary_program_dropdown.pack(fill="x", pady=2)

    def _select_program_from_config(variable, program_config):
        program_id = (program_config or {}).get("id")
        if not program_id:
            variable.set("<none>")
            return

        selected_option = next(
            (_format_program_option(program) for program in destiny_programs if program.get("id") == program_id),
            "<none>",
        )
        variable.set(selected_option)

    def refresh_destiny_programs(select_from_config=False):
        nonlocal destiny_programs

        try:
            destiny_programs, options = _load_destiny_program_options(
                {
                    "url": destiny_url.get().strip(),
                    "username": destiny_username.get().strip(),
                    "pass": destiny_password.get().strip(),
                }
            )
            _set_option_menu_values(matrix_program_dropdown, selected_matrix_program, options)
            _set_option_menu_values(beneficiary_program_dropdown, selected_beneficiary_program, options)

            if select_from_config:
                loaded = config_utils.load_config()
                _select_program_from_config(selected_matrix_program, loaded.get("matrixProgram", {}))
                _select_program_from_config(selected_beneficiary_program, loaded.get("beneficiaryProgram", {}))

            status_label.configure(text="Destiny programs loaded.", text_color="green")
        except Exception as e:
            destiny_programs = []
            error_options = ["<failed to load programs>"]
            _set_option_menu_values(matrix_program_dropdown, selected_matrix_program, error_options, fallback="<failed to load programs>")
            _set_option_menu_values(beneficiary_program_dropdown, selected_beneficiary_program, error_options, fallback="<failed to load programs>")
            status_label.configure(text=f"Error loading destiny programs: {e}", text_color="red")

    refresh_destiny_programs_btn = ctk.CTkButton(destiny_frame, text="Refresh programs", command=refresh_destiny_programs)
    refresh_destiny_programs_btn.pack(anchor="e", pady=(4, 0))

    # Other settings
    general_frame = ctk.CTkFrame(content_frame)
    general_frame.pack(padx=5, pady=8, fill="x")

    ctk.CTkLabel(general_frame, text="Other settings", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0, 5))

    ctk.CTkLabel(general_frame, text="TEI download page size").pack(anchor="w", padx=2)
    tei_page_size = ctk.CTkEntry(general_frame)
    tei_page_size.pack(fill="x", pady=2)
    tei_page_size.insert(0, str(config.get("teiDownloadPageSize", "")))

    ctk.CTkLabel(general_frame, text="Download level").pack(anchor="w", padx=2)
    download_level = ctk.CTkEntry(general_frame)
    download_level.pack(fill="x", pady=2)
    download_level.insert(0, str(config.get("downalodLevel", "")))

    status_label = ctk.CTkLabel(content_frame, text="", text_color="green")
    status_label.pack(pady=(5, 0))

    def save_config():
        try:
            current = config_utils.load_config()

            def get_selected_program(variable):
                selected_program_id = _extract_program_id(variable.get())
                if not selected_program_id:
                    return {}

                return next(
                    (program for program in destiny_programs if program.get("id") == selected_program_id),
                    {},
                )

            update = {
                "originServer": {
                    "url": origin_url.get().strip(),
                    "username": origin_username.get().strip(),
                    "pass": origin_password.get().strip(),
                },
                "destinyServer": {
                    "url": destiny_url.get().strip(),
                    "username": destiny_username.get().strip(),
                    "pass": destiny_password.get().strip(),
                },
                "teiDownloadPageSize": int(tei_page_size.get().strip() or current.get("teiDownloadPageSize", 0)),
                "downalodLevel": int(download_level.get().strip() or current.get("downalodLevel", 0)),
                "matrixProgram": get_selected_program(selected_matrix_program),
                "beneficiaryProgram": get_selected_program(selected_beneficiary_program),
            }

            config_utils.update_config(update)
            status_label.configure(text="Configuration saved successfully.", text_color="green")
        except Exception as e:
            status_label.configure(text=f"Error saving configuration: {e}", text_color="red")

    button_frame = ctk.CTkFrame(content_frame)
    button_frame.pack(padx=5, pady=12)

    save_btn = ctk.CTkButton(button_frame, text="Save configuration", command=save_config)
    save_btn.pack(side="left", padx=6)

    reload_btn = ctk.CTkButton(button_frame, text="Reload configuration", command=lambda: frame.after(10, _populate_from_config))
    reload_btn.pack(side="left", padx=6)

    def _populate_from_config():
        loaded = config_utils.load_config()
        origin_url.delete(0, "end")
        origin_url.insert(0, loaded.get("originServer", {}).get("url", ""))
        origin_username.delete(0, "end")
        origin_username.insert(0, loaded.get("originServer", {}).get("username", ""))
        origin_password.delete(0, "end")
        origin_password.insert(0, loaded.get("originServer", {}).get("pass", ""))

        destiny_url.delete(0, "end")
        destiny_url.insert(0, loaded.get("destinyServer", {}).get("url", ""))
        destiny_username.delete(0, "end")
        destiny_username.insert(0, loaded.get("destinyServer", {}).get("username", ""))
        destiny_password.delete(0, "end")
        destiny_password.insert(0, loaded.get("destinyServer", {}).get("pass", ""))

        refresh_destiny_programs(select_from_config=True)
        _select_program_from_config(selected_matrix_program, loaded.get("matrixProgram", {}))
        _select_program_from_config(selected_beneficiary_program, loaded.get("beneficiaryProgram", {}))

        tei_page_size.delete(0, "end")
        tei_page_size.insert(0, str(loaded.get("teiDownloadPageSize", "")))
        download_level.delete(0, "end")
        download_level.insert(0, str(loaded.get("downalodLevel", "")))

        status_label.configure(text="Configuration reloaded.", text_color="green")

    _populate_from_config()

    return frame
