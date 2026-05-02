from copy import deepcopy
from typing import Any

from dhis2_client import DHIS2Client
from dhis2_client.errors import DHIS2HTTPError

from common.modules.data_exchange import handle_transfomation
from common.modules.load_modules.load_data import create_client
from common.modules.mixins.DataExchangeExecutionConfig import DataExchangeExecutionConfig, OvcDataExchangeExecutionConfig
from common.utils import utils


TRACKER_ENDPOINT = "trackedEntities"
TRACKER_FIELDS = "*,!createdBy,!updatedBy,!relationships,enrollments[*,events[*,!createdBy,!updatedBy],!attributes]"


def _is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "sim"}


def download_data(execution_config: OvcDataExchangeExecutionConfig, client: DHIS2Client) -> list[dict]:
    tracked_entities: list[dict] = []
    orgunits = execution_config.orgunits if execution_config.orgunits else [{"id": "ALL", "name": "All orgunits"}]

    for orgunit in orgunits:
        page = 1
        while True:
            params = {
                "program": execution_config.family_program["id"],
                "page": page,
                "pageSize": execution_config.page_size,
                "fields": TRACKER_FIELDS,
            }

            orgunit_id = orgunit.get("id")
            if orgunit_id and orgunit_id != "ALL":
                params.update({"ouMode": "DESCENDANTS", "orgUnit": orgunit_id})
            else:
                params.update({"ouMode": "ACCESSIBLE"})

            results = client.get(f"/api/tracker/{TRACKER_ENDPOINT}.json", params=params)
            page_data = results.get(TRACKER_ENDPOINT, results.get("instances", []))

            if not page_data:
                break

            tracked_entities.extend(page_data)

            pager = results.get("pager", {})
            page_count = pager.get("pageCount")
            if page_count and page >= page_count:
                break

            page += 1

    return tracked_entities


def filter_data(tracker_entities: list[dict], execution_config: OvcDataExchangeExecutionConfig) -> list[dict]:
    valid_data: list[dict] = []

    for tracked_entity in tracker_entities:
        waiver_attribute = next(
            (item for item in tracked_entity.get("attributes", []) if item.get("attribute") == execution_config.family_waiver_attribute),
            None,
        )

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


def load_data(data: list[dict], execution_config: OvcDataExchangeExecutionConfig, client: DHIS2Client):
    if not data:
        print("[INFO] No data to load.")
        return None

    payload = {"trackedEntities": data}

    try:
        results = client.post(
            "/api/tracker.json",
            json=payload,
            params={
                "async": execution_config.async_import,
                "skipRuleEngine": True,
                "validationMode": "SKIP",
            },
        )
        print(f"✅ Import summary: {results.get('stats')}")
        return results
    except DHIS2HTTPError as e:
        print("❌ Error sending data to destiny server")
        error_details = [report.get("message") for report in e.payload.get("validationReport", {}).get("errorReports", [])]
        print(f"❌ Import summary: {e.payload.get('stats')} {' | '.join(error_details)}")
        return None


def execute(execution_config: OvcDataExchangeExecutionConfig):
    config = utils.get_config_file()
    origin_server = config.get("originServer")
    destiny_server = config.get("destinyServer")

    if not origin_server or not destiny_server:
        raise KeyError("Both originServer and destinyServer must exist in config file")

    origin_client = create_client(config=origin_server)
    destiny_client = create_client(config=destiny_server)

    tracker_entities = download_data(execution_config=execution_config, client=origin_client)
    print(f"Downloaded {len(tracker_entities)} tracked entities from origin server.")
    print(f"Filtering data based on waiver attribute '{execution_config.family_waiver_attribute}'...")

    valid_data = filter_data(tracker_entities=tracker_entities, execution_config=execution_config)
    print(f"Filtered {len(valid_data)} tracked entities based on waiver attribute '{execution_config.family_waiver_attribute}'.")

    transformed_data = transform_data(valid_tracked_entities=valid_data, execution_config=execution_config)
    print(f"Transformed {len(transformed_data)} tracked entities.")
    
    return load_data(data=transformed_data, execution_config=execution_config, client=destiny_client)


if __name__ == '__main__':
    raise SystemExit("Please call execute(execution_config) with an OvcDataExchangeExecutionConfig instance.")