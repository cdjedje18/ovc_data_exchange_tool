import json
import logging
import os
import threading
import customtkinter as ctk
import sys
from common.modules.extract_modules import extract_data
from common.modules.transform_modules import transform_data
from common.utils import utils




def execute(log_callback=None, print_callback=None):
    if log_callback:
        # Set up logging to callback
        class CallbackHandler(logging.Handler):
            def emit(self, record):
                log_callback(self.format(record) + "\n")
        
        logger = logging.getLogger()
        handler = CallbackHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    if print_callback:
        # Capture stdout
        class StdoutCapture:
            def __init__(self, callback):
                self.callback = callback
            def write(self, text):
                self.callback(text)
            def flush(self):
                pass
        
        old_stdout = sys.stdout
        sys.stdout = StdoutCapture(print_callback)
    
    try:
        utils.create_default_folders()
        
        extract_data.execute()
        
        transform_data.execute()
    finally:
        if print_callback:
            sys.stdout = old_stdout



class DataExchangeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("OVC Data Exchange")
        self.geometry("800x500")
        
        # Create tabview
        self.tabview = ctk.CTkTabview(self, width=780, height=450)
        self.tabview.pack(pady=20, padx=20, fill="both", expand=True)
        
        self.tabview.add("Logs")
        self.tabview.add("Prints")
        
        # Text areas
        self.log_text = ctk.CTkTextbox(self.tabview.tab("Logs"), wrap="word")
        self.log_text.pack(expand=True, fill="both", padx=10, pady=10)
        
        self.print_text = ctk.CTkTextbox(self.tabview.tab("Prints"), wrap="word")
        self.print_text.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Run button
        self.run_button = ctk.CTkButton(self, text="Run Data Exchange", command=self.run_process)
        self.run_button.pack(pady=(0, 20))
        
    def run_process(self):
        self.run_button.configure(state="disabled")
        self.log_text.delete("1.0", "end")
        self.print_text.delete("1.0", "end")
        thread = threading.Thread(target=self._execute_in_thread)
        thread.start()
    
    def _execute_in_thread(self):
        execute(log_callback=self.log_message, print_callback=self.print_message)
        self.after(0, self.show_completion)
        self.run_button.configure(state="normal")
    
    def show_completion(self):
        completion_msg = "\n--- Data Exchange Process Completed Successfully ---\n"
        self.log_message(completion_msg)
        self.print_message(completion_msg)
    
    def log_message(self, message):
        self.log_text.insert("end", message)
        self.log_text.see("end")
    
    def print_message(self, message):
        self.print_text.insert("end", message)
        self.print_text.see("end")



if __name__ == "__main__":
    app = DataExchangeApp()
    app.mainloop()