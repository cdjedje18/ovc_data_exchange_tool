from typing import Dict, List, Any, Optional
import json
import copy
from collections import defaultdict
import uuid

from common.modules.data_exchange.data_exchange import DataExchangeExecutionConfig




def _get_orgunit_from_mapping_hash(source_orgunit: str, orgunit_mapping_hash: dict | None) -> str:
    
    if orgunit_mapping_hash is None:
        return source_orgunit

    return orgunit_mapping_hash.get(source_orgunit, -1)



def _generate_relationships_from_mapping_hash(source_relationships: list, relationship_mapping_hash: dict | None) -> str:
    
    if relationship_mapping_hash is None:
        return source_relationships

    new_relationships = []
    for rel in source_relationships:
        rel_id = rel.get("relationshipType")

        if relationship_mapping_hash and rel_id in relationship_mapping_hash:
            new_relationships.append({
                **rel,
                "relationshipType": relationship_mapping_hash[rel_id]
            })

    return new_relationships if new_relationships else -1



def _get_value_from_mapping(source_value: Any, mapping_item: dict) -> Any:
    
    if "optionMapping" not in mapping_item:
        return source_value
    
    for option in mapping_item["optionMapping"]:
        if option.get("sourceOption") == source_value:
            return option.get("targetOption")
    
    return -1


def get_source_attribute_value(source_tei: dict, attribute_id: str) -> Any:
    for attr in source_tei.get("attributes", []):
        if attr.get("attribute") == attribute_id:
            return attr.get("value")
    return None


def get_source_tei_valid_event(source_tei: dict, mapping) -> List[dict]:
    events = []
    for enrollment in source_tei.get("enrollments", []):
        for event in enrollment.get("events", []):
            if event.get("programStage") == mapping.get("source").get("programStageId"):
                return event

    return None


def get_program_stage_mapping_for_event(source_event: dict, program_stage_mappings: List[dict]) -> Optional[dict]:
    for mapping in program_stage_mappings:
        if mapping.get("source", {}).get("programStageId") == source_event.get("programStage"):
            return mapping
    return None


def _generate_tei_attributes(
    source_tei: dict,
    tei_attribute_mappings: List[dict],
    
) -> List[dict]:
    """Build target TEI attributes (handles all three scenarios)."""
    target_attrs = []
    mapped_attribute_ids = set()
    for attribute_mapping in tei_attribute_mappings:

        value = None
        source_config = attribute_mapping.get("source", {})

        if source_config.get("type") == "attribute":
            source_attribute_value = get_source_attribute_value(source_tei, attribute_id=attribute_mapping.get("source").get("id"))
            value = _get_value_from_mapping(source_attribute_value, attribute_mapping)


        if source_config.get("type") == "dataElement":
            valid_event = get_source_tei_valid_event(source_tei, attribute_mapping)

            for data_value in valid_event.get("dataValues", []) if valid_event else []:
                if data_value.get("dataElement") == attribute_mapping.get("source").get("id"):
                    source_data_value = data_value.get("value")
                    value = _get_value_from_mapping(source_data_value, attribute_mapping)
                    break


        if source_config.get("type") == "default":
            value = source_config.get("value")

        target_attrs.append({
            "attribute": attribute_mapping.get("target").get("id"),
            "value": value
        })

    return target_attrs



def _generate_event_data_values(
    source_event: dict,
    mapping: dict
) -> List[dict]:
    
    target_data_values = []
    for data_value_mapping in mapping.get("mappings", []):
        value = None
        source_config = data_value_mapping.get("source", {})

        if source_config.get("type") == "default":
            value = source_config.get("value")
    
        else:
            for dv in source_event.get("dataValues", []):
                if dv.get("dataElement") == source_config.get("id"):
                    source_data_value = dv.get("value")
                    value = _get_value_from_mapping(source_data_value, data_value_mapping)
                    break

        target_data_values.append({
            "dataElement": data_value_mapping.get("target").get("id"),
            "value": value
        })

    return target_data_values



def _transform_mapped_events(
    source_events: List[dict],
    stage_mapping: dict,
    orgunit_mapping_hash: dict = None
) -> List[dict]:
    
    new_events = []
    for event in source_events:
        program_stage_mapping = get_program_stage_mapping_for_event(event, stage_mapping.get("programStageMappings", []))

        if program_stage_mapping is None:
            new_events.append(event)
        else:
            new_event = {
                **event,
                "programStage": program_stage_mapping.get("target").get("programStageId"),
                "orgUnit": _get_orgunit_from_mapping_hash(event.get("orgUnit"), orgunit_mapping_hash),
                "dataValues": _generate_event_data_values(event, program_stage_mapping)
            }
            new_events.append(new_event)

    return new_events





def transform_single_tei(
    source_tei: dict,
    data_mapping: dict,
    relationship_mapping_hash: dict | None,
    orgunit_mapping_hash: dict | None
) -> dict:
    

    new_tei = {
        **source_tei,
        "orgUnit":  _get_orgunit_from_mapping_hash(source_tei.get("orgUnit"), orgunit_mapping_hash),
        "attributes": _generate_tei_attributes(
            source_tei=source_tei,
            attribute_mappings=data_mapping.get("teiAttributeMappings", [])
        ),
        "relationships": _generate_relationships_from_mapping_hash(source_relationships=source_tei.get("relationships", []), relationship_mapping_hash=relationship_mapping_hash) if source_tei.get("relationships") else [],
        "enrollments": [
            {
                **enrollment,
                "orgUnit": _get_orgunit_from_mapping_hash(enrollment.get("orgUnit"), orgunit_mapping_hash),
                "events": _transform_mapped_events(
                    source_events=enrollment.get("events", []),
                    stage_mappings=data_mapping.get("programStageMappings", {}),
                    orgunit_mapping_hash=orgunit_mapping_hash
                )
            } for enrollment in source_tei.get("enrollments", [])
        ]

    }

    return new_tei


def transform_single_event(
    source_event: dict,
    data_mapping: dict,
    orgunit_mapping_hash: dict
) -> dict:
    
    program_stage_mapping = get_program_stage_mapping_for_event(source_event, data_mapping.get("programStageMappings", []))

    new_event = {
        **source_event,
        "orgUnit":  _get_orgunit_from_mapping_hash(source_event.get("orgUnit"), orgunit_mapping_hash),
        "programStage": program_stage_mapping.get("target").get("programStageId") if program_stage_mapping else source_event.get("programStage"),
        "dataValues": _generate_event_data_values(
            source_event=source_event,
            data_value_mappings=program_stage_mapping
        )
    }

    return new_event



def transform_tracker_payload(
    source_payload: dict,
    execution_config: DataExchangeExecutionConfig = None,
    orgunit_mapping_hash: dict = None,
    relationship_mapping_hash: dict = None
) -> dict:
    
    data_mapping = execution_config.variable_mapping

    if not data_mapping:
        return source_payload.get("trackedEntities", [])  # No mapping provided, return as is

    tracked_entities = source_payload.get("trackedEntities", [])

    new_tracked_entities = []
    for source_tei in tracked_entities:
        transformed = transform_single_tei(source_tei=source_tei, data_mapping=data_mapping, relationship_mapping_hash=relationship_mapping_hash, orgunit_mapping_hash=orgunit_mapping_hash)
        new_tracked_entities.append(transformed)
        
    return new_tracked_entities



def transform_event_payload(
    source_payload: dict,
    execution_config: DataExchangeExecutionConfig = None,
    orgunit_mapping_hash: dict = None
) -> dict:
    
    data_mapping = execution_config.variable_mapping

    if not data_mapping:
        return source_payload.get("events", [])  # No mapping provided, return as is

    events = source_payload.get("events", [])

    new_events = []
    for source_event in events:
        transformed = transform_single_event(source_event=source_event, data_mapping=data_mapping, orgunit_mapping_hash=orgunit_mapping_hash)
        new_events.append(transformed)
        
    return new_events


if __name__ == "__main__":
    pass