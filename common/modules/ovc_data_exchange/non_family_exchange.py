from copy import deepcopy
import json
import os
from typing import Any

from dhis2_client import DHIS2Client
from dhis2_client.errors import DHIS2HTTPError
import more_itertools

from common import constants
from common.modules.data_exchange import handle_transfomation
from common.modules.load_modules.load_data import create_client
from common.modules.mixins.DataExchangeExecutionConfig import DataExchangeExecutionConfig, OvcDataExchangeExecutionConfig
from common.utils import utils


TRACKER_ENDPOINT = "trackedEntities"
TRACKER_FIELDS = "*,!createdBy,!updatedBy,relationships[*],enrollments[*,events[*,!createdBy,!updatedBy],!attributes]"

BENEFICIARY_FIELDS = "trackedEntity,attributes[attribute,value]"
RELATIONSHIP_TYPES = ["Z3p3fp4xTLU", "IBtE6ocVkN0"]
BENEFICIARY_PROGRAM_ID = "pVgO58r40Au"



def get_total_data(program:str, endpoint:str, orgunit:str, page_size:int, client: DHIS2Client):

    results = client.get(f"/api/tracker/{endpoint}.json", params={"totalPages": True, "program": program, "orgUnit": orgunit, "ouMode": "DESCENDANTS", "pageSize": page_size, "fields": "created"})
    # logger.info(f"Downloaded {len(results['organisationUnits'])} organisation units")
    return results


def get_program_details(program: dict, client: DHIS2Client):

    params = dict()

    if program['programType'] == constants.TRACKER_PROGRAM_TYPE:
        params = {"fields": "id,name,programTrackedEntityAttributes[trackedEntityAttribute[id,name,valueType]],programStages[id,name,programStageDataElements[dataElement[id,name,valueType]]]"}
    if program['programType'] == constants.EVENT_PROGRAM_TYPE:
        params = {"fields": "id,name,programStages[id,name,programStageDataElements[dataElement[id,name,valueType]]]"}
    
    program_data = client.get(f"/api/programs/{program['id']}", params=params)

    program_stages_data = dict()
    for stage in program_data.get("programStages", []):
        stage_data_element_list = dict()

        for stage_data_element in stage.get("programStageDataElements", []):
            data_element_id = stage_data_element['dataElement']['id']
            stage_data_element_list[data_element_id] = stage_data_element['dataElement']

        program_stages_data[stage['id']] = stage_data_element_list
   
    program_details = {
        "id": program_data['id'],
        "attributes":  {attribute['trackedEntityAttribute']['id']: attribute['trackedEntityAttribute'] for attribute in program_data.get("programTrackedEntityAttributes", [])} if program['programType'] == constants.TRACKER_PROGRAM_TYPE else None,
        "programStages": program_stages_data
    }

    return program_details


def downloading_data_tracked_entities(endpoint: str, program:str, fields: str, page: int, execution_config: DataExchangeExecutionConfig, orgunit: str | None, client: DHIS2Client = None) -> dict:

    # logger = get_logger()
    # logging.info(f"Download TEIs")

    params = {"program": program, "page": page, "fields": fields, "pageSize": execution_config.page_size}
    if orgunit is not None and orgunit != "ALL":
        params.update({ "ouMode": "DESCENDANTS", "orgUnit": orgunit})
    else:
        params.update({"ouMode": "ACCESSIBLE"})
    
    results = client.get(f"/api/tracker/{endpoint}.json", params=params)
    # print(type(results))
    return results



def downloading_beneficiary_tracked_entities(tracked_entities_ids, fields: str, program:str, execution_config: DataExchangeExecutionConfig, orgunit: str | None, client: DHIS2Client = None) -> dict:

    # logger = get_logger()
    # logging.info(f"Download TEIs")

    data = []
    splited_ids = list(more_itertools.chunked(tracked_entities_ids, 400))

    for ids_chunk in splited_ids:

        request_ids = ";".join(ids_chunk)

        params = {"fields": fields, "skipPaging": True, "trackedEntity": request_ids}
        if program is not None:
            params["program"] = program
                
        results = client.get(f"/api/tracker/{TRACKER_ENDPOINT}.json", params=params)
        # print(results)
        data.extend(results[TRACKER_ENDPOINT]) if TRACKER_ENDPOINT in results else data.extend(results[constants.INSTANCES])


    return data



def extract_teis_from_relationships(tracked_entities: list[dict], relationship_types: list[str]) -> str | None:

    relationships = []
    for tracked_entity in tracked_entities:
        relationships.extend(tracked_entity.get("relationships", []))

    return [relationship.get("to").get("trackedEntity").get("trackedEntity") 
            for relationship in relationships 
            if relationship.get("relationshipType") in relationship_types and relationship.get("to")]


def _is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "sim"}


def _is_cancelled(cancel_event=None) -> bool:
    return bool(cancel_event and cancel_event.is_set())



def get_non_waiver_families(families_tracked_entities: list[dict], execution_config: OvcDataExchangeExecutionConfig) -> list[dict]:

    """
    This function receives a list of family tracked entities and 
    returns only those that have all beneficiaries with the waiver attribute marked as false.
    """
    
    
    non_waiver_families = []
    for families_tracked_entity in families_tracked_entities:
        
        waiver_attribute_value = None
        for attribute in families_tracked_entity.get("attributes", []):
            if attribute.get("attribute") == execution_config.family_waiver_attribute:
                waiver_attribute_value = attribute.get("value")
                break
        
        if not _is_truthy(waiver_attribute_value):
            non_waiver_families.append(families_tracked_entity)

    return non_waiver_families



def get_valid_families(families_tracked_entities: list[dict], org_unit:str, client: DHIS2Client, execution_config: OvcDataExchangeExecutionConfig) -> list[dict]:

    """
    This function receives a list of family tracked entities and 
    returns only those that have at least one beneficiary with the waiver attribute marked as true.
    """
    
    
    valid_families = []

    beneficiary_teis_ids = extract_teis_from_relationships(tracked_entities=families_tracked_entities, relationship_types=RELATIONSHIP_TYPES)

    beneficiary_teis = downloading_beneficiary_tracked_entities(tracked_entities_ids=beneficiary_teis_ids, fields=BENEFICIARY_FIELDS, program=BENEFICIARY_PROGRAM_ID, execution_config=execution_config, orgunit=org_unit, client=client)
    

    valid_beneficiary_teis = set()
    for beneficiary_tei in beneficiary_teis:
        
        for attribute in beneficiary_tei.get("attributes", []):
            if attribute.get("attribute") == execution_config.beneficiary_waiver_attribute:
               
                valid_beneficiary_teis.add(beneficiary_tei.get("trackedEntity"))
                break

    
    for family in families_tracked_entities:
        family_relationships = family.get("relationships", [])
        family_beneficiaries = [relationship.get("to").get("trackedEntity").get("trackedEntity") for relationship in family_relationships if relationship.get("relationshipType") in RELATIONSHIP_TYPES and relationship.get("to")]

        if any(beneficiary in valid_beneficiary_teis for beneficiary in family_beneficiaries):
            valid_families.append(family)
    
    

    cleaned_valid_families = [
        {
            **family,
            "relationships": []
        }
        for family in valid_families
    ]

    return cleaned_valid_families



def filter_data(tracker_entities: list[dict], execution_config: OvcDataExchangeExecutionConfig) -> list[dict]:
    valid_data: list[dict] = []

    for tracked_entity in tracker_entities:
        waiver_attribute = None
        for attribute in tracked_entity.get("attributes", []):
            if attribute.get("attribute") == execution_config.family_waiver_attribute:
                waiver_attribute = attribute
                break

        if waiver_attribute is None:
            continue

        if _is_truthy(waiver_attribute.get("value")):
            valid_data.append(tracked_entity)

    return valid_data


def transform_data(valid_tracked_entities: list[dict], execution_config: OvcDataExchangeExecutionConfig, program_details: dict) -> list[dict]:
    # if not execution_config.variable_mapping:
    #     return valid_tracked_entities

    bridge_config = DataExchangeExecutionConfig(
        program=execution_config.family_program,
        page_size=execution_config.page_size,
        async_import=execution_config.async_import,
        include_relationships=False,
        variable_mapping=execution_config.variable_mapping,
        orgunit_mapping=execution_config.orgunit_mapping,
        relationship_mapping=execution_config.relationship_mapping,
        orgunits=execution_config.orgunits,
    )

    orgunit_mapping_hash = None
    if execution_config.orgunit_mapping and execution_config.orgunit_mapping.get("mappings"):
        orgunit_mapping_hash = {
            item["sourceOrgUnit"]: item["targetOrgUnit"]
            for item in execution_config.orgunit_mapping.get("mappings", [])
            if item.get("sourceOrgUnit") and item.get("targetOrgUnit")
        }

    relationship_mapping_hash = None
    if execution_config.relationship_mapping and execution_config.relationship_mapping.get("mappings"):
        relationship_mapping_hash = {
            item["source"]: item["target"]
            for item in execution_config.relationship_mapping.get("mappings", [])
            if item.get("source") and item.get("target")
        }

    return handle_transfomation.transform_tracker_payload(
        source_payload=deepcopy(valid_tracked_entities),
        execution_config=bridge_config,
        orgunit_mapping_hash=orgunit_mapping_hash,
        relationship_mapping_hash=relationship_mapping_hash,
        program_details=program_details,
    )


def send_data_to_destiny(data: dict, execution_config: OvcDataExchangeExecutionConfig, client: DHIS2Client = None):

    try:
        # print(json.dumps(data))
        results = client.post(f"/api/tracker.json", json=data, params={"async": execution_config.async_import, "skipRuleEngine": True, "validationMode": "SKIP"})
        print(f"✅ Import summary: {results['stats']}")
        return results
    
    except DHIS2HTTPError as e:
        print("❌ Error sending data to destiny server")
        print(e.payload)
        error_details = [report.get("message") for report in e.payload.get('validationReport', {}).get("errorReports", [])]
        # print(error_details)
        # print(f"❌ Import summary: {e.payload['stats']}", *error_details)
        return None


def execute(execution_config: OvcDataExchangeExecutionConfig, cancel_event=None):

    endpoint_tracker = TRACKER_ENDPOINT

    config = utils.get_config_file()
    origin_server = config.get("originServer")
    destiny_server = config.get("destinyServer")

    if not origin_server or not destiny_server:
        raise KeyError("Both originServer and destinyServer must exist in config file")

    origin_client = create_client(config=origin_server)
    destiny_client = create_client(config=destiny_server)

    program_details = get_program_details(program=execution_config.family_program, client=destiny_client)

    orgunits = execution_config.orgunits if execution_config.orgunits is not None else [{ "id": "ALL" , "name": "All orgunits"}]

    for orgunit in orgunits:
        if _is_cancelled(cancel_event):
            print("[INFO] Cancellation requested. Stopping family exchange.")
            return

        folder_tracker = f"control/ovc_data_exchange/non_families/data/{orgunit['id']}/{execution_config.page_size}"
        os.makedirs(folder_tracker, exist_ok=True)

        program_pager_tracker = get_total_data(program=execution_config.family_program['id'], endpoint=endpoint_tracker, orgunit=orgunit['id'], page_size=execution_config.page_size, client=origin_client)

        if program_pager_tracker['pageCount'] > 0:

            for page in range(1, program_pager_tracker['pageCount'] + 1):
                if _is_cancelled(cancel_event):
                    print("[INFO] Cancellation requested. Stopping family exchange.")
                    return

                if os.path.exists(f"{folder_tracker}/{page}.txt"):
                    print(f"⚠️ Data for {execution_config.family_program['name']} tracker page {page} already processed, skipping.")
                    continue
            
                print(f"Downloading data for program {execution_config.family_program['name']} at {orgunit['name']} orgunit: page {page} / {program_pager_tracker['pageCount']}")
                families_tracker_entities = downloading_data_tracked_entities(endpoint=endpoint_tracker, program=execution_config.family_program['id'], fields=TRACKER_FIELDS, page=page, execution_config=execution_config, orgunit=orgunit['id'], client=origin_client)
                print(f"✅ {len(families_tracker_entities[endpoint_tracker]) if endpoint_tracker in families_tracker_entities else len(families_tracker_entities[constants.INSTANCES])} Data downloaded for {orgunit['name']} orgunit")
                
                families_tracker_entities = families_tracker_entities.get(endpoint_tracker, families_tracker_entities.get(constants.INSTANCES, []))

                non_waiver_families_tracker_entities = get_non_waiver_families(families_tracked_entities=families_tracker_entities, execution_config=execution_config)
                print(f"✅ {len(non_waiver_families_tracker_entities)} non-waiver families identified based on waiver attribute '{execution_config.family_waiver_attribute}'.")

                with open(f"{folder_tracker}/{page}_origin.txt", "w", encoding="utf8") as f:
                    f.write(json.dumps(families_tracker_entities))
                
                if len(non_waiver_families_tracker_entities) == 0:
                    continue

                print(f"Filtering valid families for {orgunit['name']} orgunit based on beneficiaries' waiver attribute '{execution_config.beneficiary_waiver_attribute}'...")

                valid_data = get_valid_families(families_tracked_entities=non_waiver_families_tracker_entities, org_unit=orgunit['id'], client=origin_client, execution_config=execution_config)
                print(f"✅ Filtered {len(valid_data)} tracked entities based on waiver attribute '{execution_config.beneficiary_waiver_attribute}'.")

                with open(f"{folder_tracker}/{page}_valid.txt", "w", encoding="utf8") as f:
                    f.write(json.dumps(valid_data))

                transformed_data = transform_data(valid_tracked_entities=valid_data, execution_config=execution_config, program_details=program_details)
                print(f"Transformed {len(transformed_data)} tracked entities.")

                with open(f"{folder_tracker}/{page}_transformed.txt", "w", encoding="utf8") as f:
                    f.write(json.dumps(transformed_data))

                if _is_cancelled(cancel_event):
                    print("[INFO] Cancellation requested. Stopping family exchange.")
                    return
                
                if len(transformed_data) == 0:
                    print("⚠️ No data to send to destiny server after transformation, skipping sending data.")
                    continue
                
                send_result = send_data_to_destiny(data={'trackedEntities': transformed_data}, execution_config=execution_config, client=destiny_client)

                if send_result is not None:
                    with open(f"{folder_tracker}/{page}.txt", "w", encoding="utf8") as f:
                        f.write(json.dumps(send_result))


if __name__ == '__main__':
    raise SystemExit("Please call execute(execution_config) with an OvcDataExchangeExecutionConfig instance.")