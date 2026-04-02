import customtkinter as ctk
from common.utils import config_utils


def create_configuration_frame(parent, show_frame):
    frame = ctk.CTkFrame(parent)

    header = ctk.CTkFrame(frame)
    header.pack(fill="x", padx=15, pady=12)
    title = ctk.CTkLabel(header, text="Configuration", font=ctk.CTkFont(size=20, weight="bold"))
    title.pack(side="left")
    back = ctk.CTkButton(header, text="Back", command=lambda: show_frame("home"))
    back.pack(side="right")

    config = config_utils.load_config()

    # Origin server settings
    origin_frame = ctk.CTkFrame(frame)
    origin_frame.pack(padx=20, pady=8, fill="x")

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
    destiny_frame = ctk.CTkFrame(frame)
    destiny_frame.pack(padx=20, pady=8, fill="x")

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

    # Other settings
    general_frame = ctk.CTkFrame(frame)
    general_frame.pack(padx=20, pady=8, fill="x")

    ctk.CTkLabel(general_frame, text="Other settings", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0, 5))

    ctk.CTkLabel(general_frame, text="TEI download page size").pack(anchor="w", padx=2)
    tei_page_size = ctk.CTkEntry(general_frame)
    tei_page_size.pack(fill="x", pady=2)
    tei_page_size.insert(0, str(config.get("teiDownloadPageSize", "")))

    ctk.CTkLabel(general_frame, text="Download level").pack(anchor="w", padx=2)
    download_level = ctk.CTkEntry(general_frame)
    download_level.pack(fill="x", pady=2)
    download_level.insert(0, str(config.get("downalodLevel", "")))

    status_label = ctk.CTkLabel(frame, text="", text_color="green")
    status_label.pack(pady=(5, 0))

    def save_config():
        try:
            current = config_utils.load_config()

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
            }

            config_utils.update_config(update)
            status_label.configure(text="Configuration saved successfully.")
        except Exception as e:
            status_label.configure(text=f"Error saving configuration: {e}", text_color="red")

    button_frame = ctk.CTkFrame(frame)
    button_frame.pack(padx=20, pady=12)

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

        tei_page_size.delete(0, "end")
        tei_page_size.insert(0, str(loaded.get("teiDownloadPageSize", "")))
        download_level.delete(0, "end")
        download_level.insert(0, str(loaded.get("downalodLevel", "")))

        status_label.configure(text="Configuration reloaded.", text_color="green")

    _populate_from_config()

    return frame
