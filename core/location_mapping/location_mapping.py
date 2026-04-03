import os
from ..mapping_base import MappingStore

LOCATION_MAPPING_DIR = os.path.join('mappings', 'location_mappings')
_location_store = MappingStore(LOCATION_MAPPING_DIR)


def list_mappings():
    return _location_store.list()


def read_mapping(name):
    return _location_store.read(name)


def create_mapping(name, json_content):
    return _location_store.save(name, json_content, overwrite=False)


def update_mapping(current_name, new_name, json_content):
    return _location_store.update(current_name, new_name, json_content)


def delete_mapping(name):
    return _location_store.delete(name)
