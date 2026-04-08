import json
import customtkinter as ctk
import os
from datetime import datetime


def create_mapping_table_frame(parent, show_frame, mapping_module, mapping_type_name):
    """
    Create a frame for managing mappings with a card-based list view.
    
    Args:
        parent: Parent widget
        show_frame: Function to show other frames
        mapping_module: Module with list_mappings, read_mapping, create_mapping, update_mapping, delete_mapping
        mapping_type_name: Display name (e.g., "Data Mapping", "Location Mapping")
    """
    frame = ctk.CTkFrame(parent)

    # Header with title and back button
    header = ctk.CTkFrame(frame, fg_color="#1a1a1a")
    header.pack(fill="x", padx=0, pady=0)
    
    header_inner = ctk.CTkFrame(header)
    header_inner.pack(fill="x", padx=15, pady=12)
    
    title = ctk.CTkLabel(header_inner, text=mapping_type_name, font=ctk.CTkFont(size=24, weight="bold"))
    title.pack(side="left")
    back = ctk.CTkButton(header_inner, text="← Back", command=lambda: show_frame("mappings_hub"), width=100)
    back.pack(side="right")

    # Status label
    status_label = ctk.CTkLabel(frame, text="Ready", text_color="green", font=ctk.CTkFont(size=10))
    status_label.pack(fill="x", padx=15, pady=(8, 0))

    def set_status(message, success=True):
        status_label.configure(text=message, text_color="green" if success else "red")

    # Search bar frame
    search_frame = ctk.CTkFrame(frame, fg_color="transparent")
    search_frame.pack(fill="x", padx=15, pady=(12, 8))
    
    ctk.CTkLabel(search_frame, text="Search:", font=ctk.CTkFont(size=10)).pack(side="left", padx=(0, 8))
    search_var = ctk.StringVar()
    search_entry = ctk.CTkEntry(search_frame, textvariable=search_var, placeholder_text="Type to filter...", width=250)
    search_entry.pack(side="left", padx=5)

    # Button bar frame
    button_bar = ctk.CTkFrame(frame, fg_color="transparent")
    button_bar.pack(fill="x", padx=15, pady=(0, 12))

    create_btn = ctk.CTkButton(button_bar, text="+ New Mapping", height=32, font=ctk.CTkFont(size=11, weight="bold"))
    create_btn.pack(side="left", padx=5)
    
    refresh_btn = ctk.CTkButton(button_bar, text="Refresh", width=100, height=32, font=ctk.CTkFont(size=11))
    refresh_btn.pack(side="left", padx=5)

    # Main scrollable container (uses CTkScrollableFrame to avoid CTkCanvas bugs)
    container_frame = ctk.CTkFrame(frame)
    container_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    scrollable_frame = ctk.CTkScrollableFrame(container_frame, fg_color="transparent")
    scrollable_frame.pack(fill="both", expand=True)

    def create_mapping_card(mapping_name):
        """Create a single card widget for a mapping"""
        card = ctk.CTkFrame(scrollable_frame, fg_color="#2b2b2b", corner_radius=8)
        card.pack(fill="x", pady=6, padx=5)

        # Content frame
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=15, pady=12)

        # Name on the left
        name_label = ctk.CTkLabel(
            content, 
            text=mapping_name, 
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ffffff"
        )
        name_label.pack(side="left", anchor="w", padx=5)

        # Buttons on the right
        button_frame = ctk.CTkFrame(content, fg_color="transparent")
        button_frame.pack(side="right", padx=5)

        def edit():
            edit_dialog_window(mapping_module, mapping_name, refresh_mappings, set_status, None)

        def delete():
            try:
                mapping_module.delete_mapping(mapping_name)
                refresh_mappings()
                set_status(f"✓ Deleted '{mapping_name}'", True)
            except Exception as exc:
                set_status(f"✗ Delete failed: {exc}", False)

        edit_btn = ctk.CTkButton(
            button_frame, 
            text="✎ Edit", 
            command=edit, 
            width=80, 
            height=28,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#1f6aa5",
            hover_color="#0d4a84"
        )
        edit_btn.pack(side="left", padx=3)

        delete_btn = ctk.CTkButton(
            button_frame, 
            text="✕ Delete", 
            command=delete, 
            width=80, 
            height=28,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#d32f2f",
            hover_color="#b71c1c"
        )
        delete_btn.pack(side="left", padx=3)

    def refresh_mappings(search_term=""):
        """Refresh the card list"""
        try:
            # Clear all cards
            for widget in scrollable_frame.winfo_children():
                widget.destroy()

            mappings = mapping_module.list_mappings()
            
            # Filter if search term provided
            if search_term:
                mappings = [m for m in mappings if search_term.lower() in m.lower()]
            
            if not mappings:
                empty_message = "No mappings found. Click '+ New Mapping' to create one."
                if search_term:
                    empty_message = f"No results for '{search_term}'"
                empty_label = ctk.CTkLabel(
                    scrollable_frame,
                    text=empty_message,
                    text_color="gray",
                    font=ctk.CTkFont(size=12),
                )
                empty_label.pack(fill="both", expand=True, pady=50)
                set_status(f"No mappings" + (f" matching '{search_term}'" if search_term else ""), True)
                return
            
            # Create cards for each mapping
            for mapping_name in sorted(mappings):
                create_mapping_card(mapping_name)
            
            set_status(f"Loaded {len(mappings)} mapping(s)" + (f" (filtered)" if search_term else ""), True)
            
        except Exception as exc:
            set_status(f"✗ Error loading mappings: {exc}", False)

    def on_search_change(*args):
        """Handle search input changes"""
        search_term = search_var.get()
        refresh_mappings(search_term)

    search_var.trace("w", on_search_change)

    def open_create_dialog():
        create_dialog_window(mapping_module, lambda: refresh_mappings(search_var.get()), set_status)

    create_btn.configure(command=open_create_dialog)
    refresh_btn.configure(command=lambda: refresh_mappings(search_var.get()))

    # Initial load
    refresh_mappings()

    return frame


def create_dialog_window(mapping_module, on_create_callback, set_status_callback):
    """Dialog to create a new mapping with improved design"""
    dialog = ctk.CTkToplevel()
    dialog.title("Create New Mapping")
    dialog.geometry("700x600")
    dialog.resizable(True, True)
    dialog.attributes("-topmost", True)
    dialog.lift()
    dialog.grab_set()
    dialog.focus_force()

    # Title
    title_frame = ctk.CTkFrame(dialog, fg_color="#1a1a1a")
    title_frame.pack(fill="x", padx=0, pady=0)
    ctk.CTkLabel(title_frame, text="Create New Mapping", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=12, padx=15)

    # Content frame
    content_frame = ctk.CTkFrame(dialog)
    content_frame.pack(fill="both", expand=True, padx=15, pady=15)

    ctk.CTkLabel(content_frame, text="Mapping Name", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 5))
    name_entry = ctk.CTkEntry(content_frame, width=650, placeholder_text="Enter a unique name for this mapping")
    name_entry.pack(fill="x", pady=(0, 12))

    ctk.CTkLabel(content_frame, text="JSON Content", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 5))
    json_text = ctk.CTkTextbox(content_frame, width=650, height=350)
    json_text.pack(fill="both", expand=True, pady=(0, 12))
    json_text.insert("1.0", "{}")

    def save():
        name = name_entry.get().strip()
        content = json_text.get("1.0", "end").strip()
        if not name:
            set_status_callback("✗ Mapping name is required", False)
            return
        try:
            mapping_module.create_mapping(name, content)
            set_status_callback(f"✓ Created '{name}'", True)
            on_create_callback()
            dialog.destroy()
        except FileExistsError as exc:
            set_status_callback(f"✗ {exc}", False)
        except Exception as exc:
            set_status_callback(f"✗ Create failed: {exc}", False)

    button_frame = ctk.CTkFrame(content_frame)
    button_frame.pack(fill="x", pady=(0, 0))
    ctk.CTkButton(button_frame, text="Create", command=save, width=100, height=32, font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=5)
    ctk.CTkButton(button_frame, text="Cancel", command=dialog.destroy, width=100, height=32).pack(side="left", padx=5)


def edit_dialog_window(mapping_module, mapping_name, on_update_callback, set_status_callback, parent_window=None):
    """Dialog to edit an existing mapping with improved design"""
    dialog = ctk.CTkToplevel()
    dialog.title(f"Edit Mapping: {mapping_name}")
    dialog.geometry("700x600")
    dialog.resizable(True, True)
    dialog.attributes("-topmost", True)
    dialog.lift()
    dialog.grab_set()
    dialog.focus_force()

    try:
        existing_content = mapping_module.read_mapping(mapping_name)
    except Exception as exc:
        set_status_callback(f"✗ Load failed: {exc}", False)
        dialog.destroy()
        return

    # Title
    title_frame = ctk.CTkFrame(dialog, fg_color="#1a1a1a")
    title_frame.pack(fill="x", padx=0, pady=0)
    ctk.CTkLabel(title_frame, text="Edit Mapping", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=12, padx=15)

    # Content frame
    content_frame = ctk.CTkFrame(dialog)
    content_frame.pack(fill="both", expand=True, padx=15, pady=15)

    ctk.CTkLabel(content_frame, text="Mapping Name", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 5))
    name_entry = ctk.CTkEntry(content_frame, width=650, placeholder_text="Enter a unique name for this mapping")
    name_entry.pack(fill="x", pady=(0, 12))
    name_entry.insert(0, mapping_name)

    ctk.CTkLabel(content_frame, text="JSON Content", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 5))
    json_text = ctk.CTkTextbox(content_frame, width=650, height=350)
    json_text.pack(fill="both", expand=True, pady=(0, 12))
    json_text.insert("1.0", json.dumps(existing_content, indent=2, ensure_ascii=False))

    def save():
        new_name = name_entry.get().strip()
        content = json_text.get("1.0", "end").strip()
        if not new_name:
            set_status_callback("✗ Mapping name is required", False)
            return
        try:
            mapping_module.update_mapping(mapping_name, new_name, content)
            if new_name == mapping_name:
                set_status_callback(f"✓ Updated '{mapping_name}'", True)
            else:
                set_status_callback(f"✓ Renamed '{mapping_name}' to '{new_name}'", True)
            on_update_callback()
            dialog.destroy()
            if parent_window:
                parent_window.destroy()
        except FileExistsError as exc:
            set_status_callback(f"✗ {exc}", False)
        except Exception as exc:
            set_status_callback(f"✗ Update failed: {exc}", False)

    button_frame = ctk.CTkFrame(content_frame)
    button_frame.pack(fill="x", pady=(0, 0))
    ctk.CTkButton(button_frame, text="Save", command=save, width=100, height=32, font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=5)
    ctk.CTkButton(button_frame, text="Cancel", command=dialog.destroy, width=100, height=32).pack(side="left", padx=5)
