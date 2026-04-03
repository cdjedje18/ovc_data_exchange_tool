import json
import logging
from logging import config
import urllib3
import os


def get_config_file():

    f = open("config.json", "r", encoding="utf8")
    config = json.loads(f.read())
    f.close()

    return config



def get_harmonization_file():

    f = open("harmonization_programs.json", "r", encoding="utf8")
    harmonization_programs = json.loads(f.read())
    f.close()

    return harmonization_programs


def get_mapping_file():

    f = open("mapping.json", "r", encoding="utf8")
    mapping = json.loads(f.read())
    f.close()

    return mapping


def get_log_folder():
    return "logs"


def set_logger(log_file:str):

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", filename=f"{get_log_folder()}/{log_file}.log")
    logger = logging.getLogger(__name__)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    return logger



def create_default_folders():

    folders = ["logs", "results", "mappings/data_mappings", "mappings/location_mappings", "mappings/relationship_mappings"]

    for folder in folders:
        os.makedirs(folder, exist_ok=True)

