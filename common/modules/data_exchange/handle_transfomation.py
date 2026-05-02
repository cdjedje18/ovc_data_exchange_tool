from typing import Dict, List, Any, Optional
import json
import copy
from collections import defaultdict
import uuid
from datetime import datetime
from common.modules.mixins.DataExchangeExecutionConfig import DataExchangeExecutionConfig




def _generate_value(value, value_type):

    # print(value, value_type)

    if value_type in ["AGE", "DATE", "DATETIME"]:
        # print("Here", value, value_type)
        # Expecting value to be None or str. If None, return as is.
        if value is None:
            return value

        if not isinstance(value, str):
            return value

        # If already in desired format, return as is
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return value
        except Exception:
            pass

        # Try a few common explicit formats first
        common_formats = ["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%m/%d/%Y", "%m-%d-%Y", "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y"]
        for fmt in common_formats:
            try:
                dt = datetime.strptime(value, fmt)
                return dt.strftime("%Y-%m-%d")
            except Exception:
                continue

    return value



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



def _get_value_from_mapping(source_value: Any, mapping_item: dict, value_type: str) -> Any:
    
    if "optionMapping" not in mapping_item:
        return _generate_value(source_value, value_type)
    
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
    program_details: dict = None
) -> List[dict]:
    """Build target TEI attributes (handles all three scenarios)."""
    target_attrs = []
    mapped_attribute_ids = set()

    # print("TEI Attribute Mappings:")

    if len(tei_attribute_mappings) == 0:
        
        for attr in source_tei.get("attributes", []):
            # print(attr)
            value = attr.get("value")
            if program_details and attr.get("attribute") in program_details.get("attributes", {}):
                value_type = program_details.get("attributes", {}).get(attr.get("attribute"), {}).get("valueType")
                value = _generate_value(value, value_type)

                target_attrs.append({
                    "attribute": attr.get("attribute"),
                    "value": value
                })

    else:
        #handling with mapping
        for attribute_mapping in tei_attribute_mappings:

            attribute_details = None
            if attribute_mapping.get("target").get("id") in program_details.get("attributes", {}):
                attribute_details = program_details.get("attributes", {}).get(attribute_mapping.get("target").get("id"), {})
                continue
            
            value = None
            source_config = attribute_mapping.get("source", {})

            if source_config.get("type") == "attribute":
                source_attribute_value = get_source_attribute_value(source_tei, attribute_id=attribute_mapping.get("source").get("id"))
                value = _get_value_from_mapping(source_attribute_value, attribute_mapping, attribute_details.get("valueType"))


            if source_config.get("type") == "dataElement":
                valid_event = get_source_tei_valid_event(source_tei, attribute_mapping)

                for data_value in valid_event.get("dataValues", []) if valid_event else []:
                    if data_value.get("dataElement") == attribute_mapping.get("source").get("id"):
                        source_data_value = data_value.get("value")
                        value = _get_value_from_mapping(source_data_value, attribute_mapping, attribute_details)
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
    mapping: dict,
    program_details: dict = None
) -> List[dict]:
    
    target_data_values = []
    for data_value_mapping in mapping.get("mapping", []):
        value = None
        source_config = data_value_mapping.get("source", {})

        if source_config.get("type") == "default":
            value = source_config.get("value")
    
        else:
            for dv in source_event.get("dataValues", []):

                if dv.get("dataElement") == source_config.get("id"):
                    
                    data_element_details = program_details.get("programStages", {}).get(source_event['programStage'], {}).get(dv['dataElement'], {}) if program_details else {}

                    if not data_element_details:
                        continue
                        
                    source_data_value = dv.get("value")
                    value = _get_value_from_mapping(source_data_value, data_value_mapping, data_element_details.get("valueType"))
                    break

        target_data_values.append({
            "dataElement": data_value_mapping.get("target").get("id"),
            "value": value
        })

    return target_data_values



def _transform_mapped_events(
    source_events: List[dict],
    stage_mappings: list,
    skip_program_stages: list = None,
    orgunit_mapping_hash: dict = None,
    program_details: dict = None
) -> List[dict]:
    
    new_events = []
    for event in source_events:

        if skip_program_stages and event.get("programStage") in skip_program_stages:
            continue

        program_stage_mapping = get_program_stage_mapping_for_event(event, stage_mappings)

        if program_stage_mapping is None:

            new_data_values = []
            for dv in event.get("dataValues", []):
                if event.get("programStage") in program_details.get("programStages", {}):
                    program_stage_details = program_details.get("programStages", {}).get(event.get("programStage"), {})
                    if dv.get("dataElement") in program_stage_details:
                        new_data_values.append({
                            "dataElement": dv.get("dataElement"),
                            "value": _generate_value(dv.get("value"), program_stage_details[dv['dataElement']]['valueType'])
                        })
                    continue
            
            new_event = {
                **event,
                "orgUnit": _get_orgunit_from_mapping_hash(event.get("orgUnit"), orgunit_mapping_hash),
                'dataValues': new_data_values
            }
            new_events.append(new_event)



        else:
            new_event = {
                **event,
                "programStage": program_stage_mapping.get("target").get("programStageId"),
                "orgUnit": _get_orgunit_from_mapping_hash(event.get("orgUnit"), orgunit_mapping_hash),
                "dataValues": _generate_event_data_values(event, program_stage_mapping, program_details=program_details)
            }
            new_events.append(new_event)

    return new_events





def transform_single_tei(
    source_tei: dict,
    data_mapping: dict,
    relationship_mapping_hash: dict | None,
    orgunit_mapping_hash: dict | None,
    program_details: dict | None
) -> dict:
    

    new_tei = {
        **source_tei,
        "orgUnit":  _get_orgunit_from_mapping_hash(source_tei.get("orgUnit"), orgunit_mapping_hash),
        "attributes": _generate_tei_attributes(
            source_tei=source_tei,
            tei_attribute_mappings=data_mapping.get("teiAttributeMappings", []),
            program_details=program_details
        ),
        "relationships": _generate_relationships_from_mapping_hash(source_relationships=source_tei.get("relationships", []), relationship_mapping_hash=relationship_mapping_hash) if source_tei.get("relationships") else [],
        "enrollments": [
            {
                **enrollment,
                "orgUnit": _get_orgunit_from_mapping_hash(enrollment.get("orgUnit"), orgunit_mapping_hash),
                "events": _transform_mapped_events(
                    source_events=enrollment.get("events", []),
                    stage_mappings=data_mapping.get("programStageMappings", []),
                    skip_program_stages=data_mapping.get("skipProgramStages", []),
                    orgunit_mapping_hash=orgunit_mapping_hash,
                    program_details=program_details
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
    source_payload: list,
    execution_config: DataExchangeExecutionConfig = None,
    orgunit_mapping_hash: dict = None,
    relationship_mapping_hash: dict = None,
    program_details: dict = None
) -> dict:
    
    data_mapping = execution_config.variable_mapping if execution_config.variable_mapping is not None else {}

    # if not data_mapping:
    #     return source_payload # No mapping provided, return as is

    tracked_entities = source_payload

    new_tracked_entities = []
    for source_tei in tracked_entities:
        transformed = transform_single_tei(source_tei=source_tei, data_mapping=data_mapping, relationship_mapping_hash=relationship_mapping_hash, orgunit_mapping_hash=orgunit_mapping_hash, program_details=program_details)
        new_tracked_entities.append(transformed)
        
    return new_tracked_entities



def transform_event_payload(
    source_payload: dict,
    execution_config: DataExchangeExecutionConfig = None,
    orgunit_mapping_hash: dict = None,
    program_details: dict = None
) -> dict:
    

    print("Starting Event transformation...")

    data_mapping = execution_config.variable_mapping

    if not data_mapping:
        return source_payload.get("events", [])  # No mapping provided, return as is

    events = source_payload.get("events", [])

    new_events = []
    for source_event in events:
        transformed = transform_single_event(source_event=source_event, data_mapping=data_mapping, orgunit_mapping_hash=orgunit_mapping_hash, program_details=program_details)
        new_events.append(transformed)
        
    return new_events


if __name__ == "__main__":
    pass