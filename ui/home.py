import customtkinter as ctk


def create_home_frame(parent, show_frame):
    frame = ctk.CTkFrame(parent)

    title = ctk.CTkLabel(frame, text="Home", font=ctk.CTkFont(size=24, weight="bold"))
    title.pack(pady=(20, 10))

    cards_container = ctk.CTkFrame(frame)
    cards_container.pack(padx=20, pady=20, fill="both", expand=True)

    def make_card(text, target):
        c = ctk.CTkFrame(cards_container, fg_color="#2b2b2b", width=170, height=85)
        c.pack(side="left", padx=10, pady=12, expand=True, fill="both")
        c.pack_propagate(False)

        label = ctk.CTkLabel(c, text=text, font=ctk.CTkFont(size=14))
        label.pack(expand=True)

        btn = ctk.CTkButton(c, text="Open", command=lambda: show_frame(target), width=100)
        btn.pack(pady=6)

        return c

    make_card("Configuration", "configuration")
    make_card("Harmonization", "harmonization")
    make_card("Data Exchange", "data_exchange")

    return frame
