from copy import deepcopy
import json
import os
from typing import Any

from dhis2_client import DHIS2Client
from dhis2_client.errors import DHIS2HTTPError

from common import constants
from common.modules.data_exchange import handle_transfomation
from common.modules.load_modules.load_data import create_client
from common.modules.mixins.DataExchangeExecutionConfig import DataExchangeExecutionConfig, MatrizDataExchangeExecutionConfig, OvcDataExchangeExecutionConfig
from common.utils import utils


EVENT_ENDPOINT = "events"
EVENT_FIELDS = "*,!createdBy,!updatedBy"



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


def downloading_data_events(endpoint: str, fields: str, page: int, execution_config: MatrizDataExchangeExecutionConfig, orgunit: str | None, client: DHIS2Client = None) -> dict:

    # logger = get_logger()
    # logging.info(f"Download TEIs")

    params = {"program": execution_config.matriz_program['id'], "page": page, "fields": fields, "pageSize": execution_config.page_size}
    if orgunit is not None and orgunit != "ALL":
        params.update({ "ouMode": "DESCENDANTS", "orgUnit": orgunit})
    else:
        params.update({"ouMode": "ACCESSIBLE"})
    
    results = client.get(f"/api/tracker/{endpoint}.json", params=params)
    # print(type(results))
    return results



def _is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "sim"}


def _is_cancelled(cancel_event=None) -> bool:
    return bool(cancel_event and cancel_event.is_set())


def filter_data(events: list[dict], execution_config: MatrizDataExchangeExecutionConfig) -> list[dict]:
    valid_data: list[dict] = []

    # print(events)
    for event in events:
        # print(event)
        # print(type(events))
        waiver_data_element = None
        for data_element in event.get("dataValues", []):
            if data_element.get("dataElement") == execution_config.matriz_waiver_data_element:
                waiver_data_element = data_element
                break

        if waiver_data_element is None:
            continue

        if _is_truthy(waiver_data_element.get("value")):
            valid_data.append(event)

    return valid_data


def transform_data(valid_events: list[dict], execution_config: MatrizDataExchangeExecutionConfig, program_details: dict) -> list[dict]:
    # if not execution_config.variable_mapping:
    #     return valid_tracked_entities

    bridge_config = DataExchangeExecutionConfig(
        program=execution_config.matriz_program,
        page_size=execution_config.page_size,
        async_import=execution_config.async_import,
        include_relationships=False,
        variable_mapping=execution_config.variable_mapping,
        orgunit_mapping=execution_config.orgunit_mapping,
        relationship_mapping=None,
        orgunits=execution_config.orgunits,
    )

    orgunit_mapping_hash = None
    if execution_config.orgunit_mapping and execution_config.orgunit_mapping.get("mappings"):
        orgunit_mapping_hash = {
            item["sourceOrgUnit"]: item["targetOrgUnit"]
            for item in execution_config.orgunit_mapping.get("mappings", [])
            if item.get("sourceOrgUnit") and item.get("targetOrgUnit")
        }

    return handle_transfomation.transform_event_payload(
        source_payload=deepcopy(valid_events),
        execution_config=bridge_config,
        orgunit_mapping_hash=orgunit_mapping_hash,
        program_details=program_details,
    )


def send_data_to_destiny(data: dict, execution_config: MatrizDataExchangeExecutionConfig, client: DHIS2Client = None):

    try:
        # print(json.dumps(data))
        results = client.post(f"/api/tracker.json", json=data, params={"async": execution_config.async_import, "skipRuleEngine": True, "validationMode": "SKIP"})
        print(f"✅ Import summary: {results['stats']}")
        return results
    
    except DHIS2HTTPError as e:
        # print(e.payload)
        print("❌ Error sending data to destiny server")
        error_details = [report.get("message") for report in e.payload.get('validationReport', {}).get("errorReports", [])]
        print(error_details)
        # print(f"❌ Import summary: {e.payload['stats']}", *error_details)
        return None


def execute(execution_config: MatrizDataExchangeExecutionConfig, cancel_event=None):

    endpoint_tracker = EVENT_ENDPOINT

    config = utils.get_config_file()
    origin_server = config.get("originServer")
    destiny_server = config.get("destinyServer")

    if not origin_server or not destiny_server:
        raise KeyError("Both originServer and destinyServer must exist in config file")

    origin_client = create_client(config=origin_server)
    destiny_client = create_client(config=destiny_server)

    program_details = get_program_details(program=execution_config.matriz_program, client=destiny_client)

    orgunits = execution_config.orgunits if execution_config.orgunits is not None else [{ "id": "ALL" , "name": "All orgunits"}]

    for orgunit in orgunits:
        if _is_cancelled(cancel_event):
            print("[INFO] Cancellation requested. Stopping matriz exchange.")
            return

        folder_tracker = f"control/ovc_data_exchange/{execution_config.matriz_program['id']}/data/{orgunit['id']}/{execution_config.page_size}"
        os.makedirs(folder_tracker, exist_ok=True)

        program_pager_tracker = get_total_data(program=execution_config.matriz_program['id'], endpoint=endpoint_tracker, orgunit=orgunit['id'], page_size=execution_config.page_size, client=origin_client)

        if program_pager_tracker['pageCount'] > 0:

            for page in range(1, program_pager_tracker['pageCount'] + 1):
                if _is_cancelled(cancel_event):
                    print("[INFO] Cancellation requested. Stopping family exchange.")
                    return

                if os.path.exists(f"{folder_tracker}/{page}.txt"):
                    print(f"⚠️ Data for {execution_config.matriz_program['name']} tracker page {page} already processed, skipping.")
                    continue
            
                print(f"Downloading data for program {execution_config.matriz_program['name']} at {orgunit['name']} orgunit: page {page} / {program_pager_tracker['pageCount']}")
                events = downloading_data_events(endpoint=endpoint_tracker, fields=EVENT_FIELDS, page=page, execution_config=execution_config, orgunit=orgunit['id'], client=origin_client)
                events = events.get(endpoint_tracker, events.get(constants.INSTANCES, []))
                print(f"✅ {len(events)} Data downloaded for {orgunit['name']} orgunit")
                
                with open(f"{folder_tracker}/{page}_origin.txt", "w", encoding="utf8") as f:
                    f.write(json.dumps(events))

                print(f"Filtering data based on waiver data element '{execution_config.matriz_waiver_data_element}'...")

                valid_data = filter_data(events=events, execution_config=execution_config)
                print(f"✅ Filtered {len(valid_data)} events based on waiver data element '{execution_config.matriz_waiver_data_element}'.")

                with open(f"{folder_tracker}/{page}_valid.txt", "w", encoding="utf8") as f:
                    f.write(json.dumps(valid_data))

                transformed_data = transform_data(valid_events=valid_data, execution_config=execution_config, program_details=program_details)
                print(f"Transformed {len(transformed_data)} events.")

                if _is_cancelled(cancel_event):
                    print("[INFO] Cancellation requested. Stopping matriz exchange.")
                    return
                
                if len(transformed_data) == 0:
                    print("⚠️ No data to send to destiny server after transformation, skipping sending data.")
                    continue
                
                send_data_to_destiny(data={'events': transformed_data}, execution_config=execution_config, client=destiny_client)


if __name__ == '__main__':
    raise SystemExit("Please call execute(execution_config) with an OvcDataExchangeExecutionConfig instance.")