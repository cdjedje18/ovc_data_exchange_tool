import customtkinter as ctk


def create_mappings_hub_frame(parent, show_frame):
    """Landing page with cards for different mapping types"""
    frame = ctk.CTkFrame(parent)

    header = ctk.CTkFrame(frame)
    header.pack(fill="x", padx=15, pady=12)
    title = ctk.CTkLabel(header, text="Mappings", font=ctk.CTkFont(size=20, weight="bold"))
    title.pack(side="left")
    back = ctk.CTkButton(header, text="Back", command=lambda: show_frame("home"))
    back.pack(side="right")

    cards_container = ctk.CTkFrame(frame)
    cards_container.pack(padx=20, pady=20, fill="both", expand=True)

    def make_card(text, target):
        c = ctk.CTkFrame(cards_container, fg_color="#2b2b2b", width=200, height=100)
        c.pack(side="left", padx=10, pady=12, expand=True, fill="both")
        c.pack_propagate(False)

        label = ctk.CTkLabel(c, text=text, font=ctk.CTkFont(size=14))
        label.pack(expand=True)

        btn = ctk.CTkButton(c, text="Manage", command=lambda: show_frame(target), width=120)
        btn.pack(pady=6)

        return c

    make_card("Data Mappings", "data_mapping")
    make_card("Location Mappings", "location_mapping")
    make_card("Relationship Mappings", "relationship_mapping")

    return frame
