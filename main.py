import customtkinter as ctk
from ui.home import create_home_frame
from ui.configuration import create_configuration_frame
from ui.harmonization import create_harmonization_frame
from ui.data_exchange import create_data_exchange_frame
from ui.data_mapping_ui import create_data_mapping_frame
from ui.location_mapping_ui import create_location_mapping_frame
from ui.relationship_mapping_ui import create_relationship_mapping_frame
from ui.mappings_hub import create_mappings_hub_frame
from ui.ovc_data_exchange import create_ovc_data_exchange_frame


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title("OVC Data Exchange")
        self.geometry("1000x700")

        self.frames = {}
        self.create_frames()
        self.show_frame("home")

    def create_frames(self):
        self.frames["home"] = create_home_frame(self, self.show_frame)
        self.frames["configuration"] = create_configuration_frame(self, self.show_frame)
        self.frames["harmonization"] = create_harmonization_frame(self, self.show_frame)
        self.frames["data_exchange"] = create_data_exchange_frame(self, self.show_frame)
        self.frames["mappings_hub"] = create_mappings_hub_frame(self, self.show_frame)
        self.frames["ovc_data_exchange"] = create_ovc_data_exchange_frame(self, self.show_frame)
        self.frames["data_mapping"] = create_data_mapping_frame(self, self.show_frame)
        self.frames["location_mapping"] = create_location_mapping_frame(self, self.show_frame)
        self.frames["relationship_mapping"] = create_relationship_mapping_frame(self, self.show_frame)

        for frame in self.frames.values():
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    def show_frame(self, frame_name):
        for name, frame in self.frames.items():
            if name == frame_name:
                frame.lift()


if __name__ == "__main__":
    app = App()
    app.mainloop()
