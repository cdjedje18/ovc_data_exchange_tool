import os
from ..mapping_base import MappingStore

DATA_MAPPING_DIR = os.path.join('mappings', 'data_mappings')
_data_store = MappingStore(DATA_MAPPING_DIR)


def list_mappings():
    return _data_store.list()


def read_mapping(name):
    return _data_store.read(name)


def create_mapping(name, json_content):
    return _data_store.save(name, json_content, overwrite=False)


def update_mapping(current_name, new_name, json_content):
    return _data_store.update(current_name, new_name, json_content)


def delete_mapping(name):
    return _data_store.delete(name)
