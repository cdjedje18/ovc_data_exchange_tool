import os
from ..mapping_base import MappingStore

RELATIONSHIP_MAPPING_DIR = os.path.join('mappings', 'relationship_mappings')
_relationship_store = MappingStore(RELATIONSHIP_MAPPING_DIR)


def list_mappings():
    return _relationship_store.list()


def read_mapping(name):
    return _relationship_store.read(name)


def create_mapping(name, json_content):
    return _relationship_store.save(name, json_content, overwrite=False)


def update_mapping(current_name, new_name, json_content):
    return _relationship_store.update(current_name, new_name, json_content)


def delete_mapping(name):
    return _relationship_store.delete(name)
