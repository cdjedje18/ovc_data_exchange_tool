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
    orgunits: list | None = None


@dataclass
class HarmonizationExecutionConfig:
    page_size: int
    beneficiary_program_server: str
    orgunits: list | None = None



@dataclass
class OvcDataExchangeExecutionConfig:
    family_program: dict
    beneficiary_program: dict
    family_waiver_attribute: str
    beneficiary_waiver_attribute: str
    page_size: int
    async_import: bool
    variable_mapping: dict = None
    orgunit_mapping: dict = None
    relationship_mapping: dict = None
    orgunits: list | None = None