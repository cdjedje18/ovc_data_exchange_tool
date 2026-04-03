import customtkinter as ctk
from core.data_mapping import data_mapping
from ui.mapping_table_ui import create_mapping_table_frame


def create_data_mapping_frame(parent, show_frame):
    return create_mapping_table_frame(parent, show_frame, data_mapping, "Data Mappings")
