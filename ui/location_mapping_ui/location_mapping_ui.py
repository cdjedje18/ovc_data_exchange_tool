import customtkinter as ctk
from core.location_mapping import location_mapping
from ui.mapping_table_ui import create_mapping_table_frame


def create_location_mapping_frame(parent, show_frame):
    return create_mapping_table_frame(parent, show_frame, location_mapping, "Location Mappings")
