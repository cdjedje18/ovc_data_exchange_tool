from dataclasses import dataclass
import shutil


@dataclass
class DataExchangeExecutionConfig:
    program: dict
    page_size: int
    async_import: bool
    include_relationships: bool = False
    variable_mapping: dict = None
    orgunit_mapping: dict = None
    relationship_mapping: dict = None