import customtkinter as ctk
from core.relationship_mapping import relationship_mapping
from ui.mapping_table_ui import create_mapping_table_frame


def create_relationship_mapping_frame(parent, show_frame):
    return create_mapping_table_frame(parent, show_frame, relationship_mapping, "Relationship Mappings")
