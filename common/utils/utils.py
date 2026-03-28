import json
import logging
import urllib3
import os


def get_config_file():

    f = open("config.json", "r")
    config = json.loads(f.read())
    f.close()

    return config


def get_log_folder():
    return "logs"


def set_logger(log_file:str):

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", filename=f"{get_log_folder()}/{log_file}.log")
    logger = logging.getLogger(__name__)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    return logger



def create_default_folders():

    folders = ["logs", "results"]

    for folder in folders:
        os.makedirs(folder, exist_ok=True)

