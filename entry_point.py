import json
import logging
import os
import threading
import customtkinter as ctk
import sys
from common.modules.extract_modules import extract_data
from common.modules.transform_modules import transform_data
from common.modules.load_modules import load_data
from common.utils import utils




def execute():


    utils.create_default_folders()
    
    extract_data.execute()
    
    transform_data.execute()

    load_data.execute()
    


if __name__ == "__main__":
    execute()