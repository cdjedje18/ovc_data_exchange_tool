import customtkinter as ctk


def create_configuration_frame(parent, show_frame):
    frame = ctk.CTkFrame(parent)

    title = ctk.CTkLabel(frame, text="Configuration", font=ctk.CTkFont(size=20, weight="bold"))
    title.pack(pady=20)

    desc = ctk.CTkLabel(frame, text="Configuration screen placeholder.")
    desc.pack(pady=10)

    back = ctk.CTkButton(frame, text="Back", command=lambda: show_frame("home"))
    back.pack(pady=10)

    return frame
