from copy import deepcopy
import json
import os
from typing import Any

from dhis2_client import DHIS2Client
from dhis2_client.errors import DHIS2HTTPError

from common import constants
from common.modules.data_exchange import handle_transfomation
from common.modules.load_modules.load_data import create_client
from common.modules.mixins.DataExchangeExecutionConfig import DataExchangeExecutionConfig, OvcDataExchangeExecutionConfig
from common.utils import utils
import more_itertools


TRACKER_ENDPOINT = "trackedEntities"
TRACKER_FIELDS = "*,!createdBy,!updatedBy,relationships[*],enrollments[*,events[*,!createdBy,!updatedBy],!attributes]"

FAMILY_FIELDS = "trackedEntity,relationships[*]"
RELATIONSHIP_TYPES = ["Z3p3fp4xTLU", "IBtE6ocVkN0"]
BENEFICIARY_PROGRAM_ID = "pVgO58r40Au"




def _is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "sim"}


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



def downloading_data_tracked_entities(tracked_entities_ids, fields: str, program:str, execution_config: DataExchangeExecutionConfig, orgunit: str | None, client: DHIS2Client = None) -> dict:

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




def download_family_data_tracked_entities(endpoint: str, fields: str, page: int, execution_config: DataExchangeExecutionConfig, orgunit: str | None, origin_client: DHIS2Client = None, destiny_client: DHIS2Client = None) -> dict:   

    family_data = []

    params = {"program": execution_config.beneficiary_program['id'], "page": page, "fields": fields, "pageSize": execution_config.page_size}
    if orgunit is not None and orgunit != "ALL":
        params.update({ "ouMode": "DESCENDANTS", "orgUnit": orgunit})
    else:
        params.update({"ouMode": "ACCESSIBLE"})
    
    results = destiny_client.get(f"/api/tracker/{endpoint}.json", params=params)
    # print(type(results))

    family_data.extend(results.get(TRACKER_ENDPOINT, constants.INSTANCES))

    family_ids = [family.get("trackedEntity") for family in family_data]

    family_tracker_entities = downloading_data_tracked_entities(tracked_entities_ids=family_ids, fields=fields, program=execution_config.family_program['id'], execution_config=execution_config, orgunit=orgunit, client=origin_client)
    # print("faaffa", family_tracker_entities)
    return family_tracker_entities



def custom_data(tracked_entities:list):

    custom_data = []
    for tracked_entity in tracked_entities:
        custom_data.append({
            **tracked_entity,
            'enrollments': [enrollment for enrollment in tracked_entity.get("enrollments", []) if enrollment.get("program") == BENEFICIARY_PROGRAM_ID]
        })

    return custom_data


    

def extract_teis_from_relationships(tracked_entities: list[dict], relationship_types: list[str]) -> str | None:

    relationships = []
    for tracked_entity in tracked_entities:
        relationships.extend(tracked_entity.get("relationships", []))

    return [relationship.get("to").get("trackedEntity").get("trackedEntity") 
            for relationship in relationships 
            if relationship.get("relationshipType") in relationship_types and relationship.get("to")]



def filter_data(tracker_entities: list[dict], waiver_attribute: str) -> list[dict]:
    valid_data: list[dict] = []

    for tracked_entity in tracker_entities:
        waiver_attribute_value = None
        for attribute in tracked_entity.get("attributes", []):
            if attribute.get("attribute") == waiver_attribute:
                waiver_attribute_value = attribute
                break

        if waiver_attribute_value is None:
            continue

        if _is_truthy(waiver_attribute_value.get("value")):
            valid_data.append(tracked_entity)

    return valid_data


def transform_data(valid_tracked_entities: list[dict], execution_config: OvcDataExchangeExecutionConfig, program_details: dict) -> list[dict]:
    # if not execution_config.variable_mapping:
    #     return valid_tracked_entities

    bridge_config = DataExchangeExecutionConfig(
        program=execution_config.beneficiary_program,
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
        # print(e.payload)
        print("❌ Error sending data to destiny server")
        error_details = [report.get("message") for report in e.payload.get('validationReport', {}).get("errorReports", [])]
        # print(error_details)
        print(f"❌ Import summary: {e.payload['stats']}", *error_details)
        return None


def execute(execution_config: OvcDataExchangeExecutionConfig):

    endpoint_tracker = TRACKER_ENDPOINT

    config = utils.get_config_file()
    origin_server = config.get("originServer")
    destiny_server = config.get("destinyServer")

    if not origin_server or not destiny_server:
        raise KeyError("Both originServer and destinyServer must exist in config file")

    origin_client = create_client(config=origin_server)
    destiny_client = create_client(config=destiny_server)

    program_details = get_program_details(program=execution_config.beneficiary_program, client=destiny_client)

    orgunits = execution_config.orgunits if execution_config.orgunits is not None else [{ "id": "ALL" , "name": "All orgunits"}]

    for orgunit in orgunits:

        folder_tracker = f"control/ovc_data_exchange/beneficiary_data/data/{orgunit['id']}/{execution_config.page_size}"
        os.makedirs(folder_tracker, exist_ok=True)

        program_pager_tracker = get_total_data(program=execution_config.beneficiary_program['id'], endpoint=endpoint_tracker, orgunit=orgunit['id'], page_size=execution_config.page_size, client=destiny_client)

        if program_pager_tracker['pageCount'] > 0:

            for page in range(1, program_pager_tracker['pageCount'] + 1):

                if os.path.exists(f"{folder_tracker}/{page}.txt"):
                    print(f"⚠️ Data for {execution_config.beneficiary_program['name']} tracker page {page} already processed, skipping.")
                    continue
            
                print(f"Downloading data for family program {execution_config.beneficiary_program['name']} at {orgunit['name']} orgunit: page {page} / {program_pager_tracker['pageCount']}")
                family_tracker_entities = download_family_data_tracked_entities(endpoint=endpoint_tracker, fields=FAMILY_FIELDS, page=page, execution_config=execution_config, orgunit=orgunit['id'], origin_client=origin_client, destiny_client=destiny_client)
                print(f"✅ {len(family_tracker_entities)} Family Data downloaded for {orgunit['name']} orgunit")
                
                with open(f"{folder_tracker}/{page}_family.txt", "w", encoding="utf8") as f:
                    f.write(json.dumps(family_tracker_entities))

                benificiary_tracker_entities_ids = extract_teis_from_relationships(tracked_entities=family_tracker_entities, relationship_types=RELATIONSHIP_TYPES)
                # print(benificiary_tracker_entities_ids)
                print(f"Downloading data for beneficiary program {execution_config.beneficiary_program['name']} at {orgunit['name']} orgunit: page {page} / {program_pager_tracker['pageCount']}")
                beneficiary_tracker_entities = downloading_data_tracked_entities(tracked_entities_ids=benificiary_tracker_entities_ids, program=None, fields=TRACKER_FIELDS, execution_config=execution_config, orgunit=orgunit['id'], client=origin_client)
                print(f"✅ {len(beneficiary_tracker_entities)} Beneficiary Data downloaded for {orgunit['name']} orgunit")

                with open(f"{folder_tracker}/{page}_origin.txt", "w", encoding="utf8") as f:
                    f.write(json.dumps(beneficiary_tracker_entities))

                beneficiary_tracker_entities = custom_data(beneficiary_tracker_entities)

                with open(f"{folder_tracker}/{page}_custom.txt", "w", encoding="utf8") as f:
                    f.write(json.dumps(beneficiary_tracker_entities))

                print(f"Filtering data based on waiver attribute '{execution_config.beneficiary_waiver_attribute}'...")

                valid_data = filter_data(tracker_entities=beneficiary_tracker_entities, waiver_attribute=execution_config.beneficiary_waiver_attribute)
                print(f"✅ Filtered {len(valid_data)} tracked entities based on waiver attribute '{execution_config.beneficiary_waiver_attribute}'.")

                with open(f"{folder_tracker}/{page}_valid.txt", "w", encoding="utf8") as f:
                    f.write(json.dumps(valid_data))

                transformed_data = transform_data(valid_tracked_entities=valid_data, execution_config=execution_config, program_details=program_details)
                print(f"Transformed {len(transformed_data)} tracked entities.")
                if len(transformed_data) == 0:
                    print("⚠️ No data to send to destiny server after transformation, skipping sending data.")
                    continue
                with open(f"{folder_tracker}/{page}_transformed.txt", "w", encoding="utf8") as f:
                    f.write(json.dumps(transformed_data))
                # return send_data_to_destiny(data=transformed_data, execution_config=execution_config, client=destiny_client)


if __name__ == '__main__':
    raise SystemExit("Please call execute(execution_config) with an OvcDataExchangeExecutionConfig instance.")