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


TRACKER_ENDPOINT = "trackedEntities"
TRACKER_FIELDS = "*,!createdBy,!updatedBy,!relationships,enrollments[*,events[*,!createdBy,!updatedBy],!attributes]"






def get_total_data(program:str, endpoint:str, orgunit:str, page_size:int, client: DHIS2Client):

    results = client.get(f"/api/tracker/{endpoint}.json", params={"totalPages": True, "program": program, "orgUnit": orgunit, "ouMode": "DESCENDANTS", "pageSize": page_size, "fields": "created"})
    # logger.info(f"Downloaded {len(results['organisationUnits'])} organisation units")
    return results


def downloading_data_tracked_entities(endpoint: str, fields: str, page: int, execution_config: DataExchangeExecutionConfig, orgunit: str | None, client: DHIS2Client = None) -> dict:

    # logger = get_logger()
    # logging.info(f"Download TEIs")

    params = {"program": execution_config.family_program['id'], "page": page, "fields": fields, "pageSize": execution_config.page_size}
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


def transform_data(valid_tracked_entities: list[dict], execution_config: OvcDataExchangeExecutionConfig) -> list[dict]:
    if not execution_config.variable_mapping:
        return valid_tracked_entities

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
        program_details=None,
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

    orgunits = execution_config.orgunits if execution_config.orgunits is not None else [{ "id": "ALL" , "name": "All orgunits"}]

    for orgunit in orgunits:

        folder_tracker = f"control/ovc_data_exchange/{execution_config.family_program['id']}/data/{orgunit['id']}/{execution_config.page_size}"
        os.makedirs(folder_tracker, exist_ok=True)

        program_pager_tracker = get_total_data(program=execution_config.family_program['id'], endpoint=endpoint_tracker, orgunit=orgunit['id'], page_size=execution_config.page_size, client=origin_client)

        if program_pager_tracker['pageCount'] > 0:

            for page in range(1, program_pager_tracker['pageCount'] + 1):

                if os.path.exists(f"{folder_tracker}/{page}.txt"):
                    print(f"⚠️ Data for {execution_config.family_program['name']} tracker page {page} already processed, skipping.")
                    continue
            
                print(f"Downloading data for program {execution_config.family_program['name']} at {orgunit['name']} orgunit: page {page} / {program_pager_tracker['pageCount']}")
                tracker_entities = downloading_data_tracked_entities(endpoint=endpoint_tracker, fields=TRACKER_FIELDS, page=page, execution_config=execution_config, orgunit=orgunit['id'], client=origin_client)
                print(f"✅ {len(tracker_entities[endpoint_tracker]) if endpoint_tracker in tracker_entities else len(tracker_entities[constants.INSTANCES])} Data downloaded for {orgunit['name']} orgunit")
                
                tracked_entities = tracker_entities.get(endpoint_tracker, tracker_entities.get(constants.INSTANCES, []))

                with open(f"{folder_tracker}/{page}_origin.txt", "w", encoding="utf8") as f:
                    f.write(json.dumps(tracked_entities))

                print(f"Filtering data based on waiver attribute '{execution_config.family_waiver_attribute}'...")

                valid_data = filter_data(tracker_entities=tracked_entities, execution_config=execution_config)
                print(f"✅ Filtered {len(valid_data)} tracked entities based on waiver attribute '{execution_config.family_waiver_attribute}'.")

                with open(f"{folder_tracker}/{page}_valid.txt", "w", encoding="utf8") as f:
                    f.write(json.dumps(valid_data))

                transformed_data = transform_data(valid_tracked_entities=valid_data, execution_config=execution_config)
                print(f"Transformed {len(transformed_data)} tracked entities.")

                return send_data_to_destiny(data=transformed_data, execution_config=execution_config, client=destiny_client)


if __name__ == '__main__':
    raise SystemExit("Please call execute(execution_config) with an OvcDataExchangeExecutionConfig instance.")