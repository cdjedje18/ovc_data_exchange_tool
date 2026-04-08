from dhis2_client import DHIS2Client, client
import logging
from dhis2_client.errors import DHIS2HTTPError
import urllib3
from common import constants
from common.modules.data_exchange import handle_transfomation
from common.utils import utils
import os
import json
# from dataclasses import dataclass
import shutil
from common.modules.mixins.DataExchangeExecutionConfig import DataExchangeExecutionConfig


# @dataclass
# class DataExchangeExecutionConfig:
#     program: dict
#     page_size: int
#     async_import: bool
#     include_relationships: bool = False
#     variable_mapping: dict = None
#     orgunit_mapping: dict = None
#     relationship_mapping: dict = None



def get_logger():
    logger = utils.set_logger(log_file="extract_data.log")
    return logger



def generate_endpoint(program:dict):

    if program['programType'] == constants.TRACKER_PROGRAM_TYPE:
      return "trackedEntities"

    if program['programType'] == constants.EVENT_PROGRAM_TYPE:
      return "events"
    
    raise ValueError("Endpoint not correct defiend in config file")


def generate_fields(program:dict, execution_config: DataExchangeExecutionConfig = None):

    if program['programType'] == constants.TRACKER_PROGRAM_TYPE:
      
      if execution_config and execution_config.include_relationships:
          return "*,!createdBy,!updatedBy,relationships[relationship,relationshipType,from[trackedEntity[trackedEntity]],to[trackedEntity[trackedEntity]]],enrollments[*,events[*,!createdBy,!updatedBy],!attributes]"

      return "*,!createdBy,!updatedBy,!relationships,enrollments[*,events[*,!createdBy,!updatedBy],!attributes]"

    if program['programType'] == constants.EVENT_PROGRAM_TYPE:
      return "*"
    
    raise ValueError("Endpoint not correct defiend in config file")
      


def get_data_exchange_folder(program_id: str, page_size: int):

    data_folder = f"control/data_exchange/{program_id}/{page_size}"
    return data_folder


def create_data_exchange_folder(program_id: str, page_size: int):

    data_folder = get_data_exchange_folder(program_id=program_id, page_size=page_size)
    os.makedirs(data_folder, exist_ok=True)

    return True


def clear_data_exchange_folder(program_id: str):

    data_folder = f"control/data_exchange/{program_id}"

    if os.path.exists(data_folder): 
        shutil.rmtree(data_folder) 


def get_total_data(program:str, endpoint:str, page_size:int, client: DHIS2Client):

    results = client.get(f"/api/tracker/{endpoint}.json", params={"totalPages": True, "program": program, "ouMode": "ACCESSIBLE", "pageSize": page_size, "fields": "created"})
    # logger.info(f"Downloaded {len(results['organisationUnits'])} organisation units")
    return results


def create_client(config: dict) -> DHIS2Client:
    client = DHIS2Client(
        base_url=config['url'],
        username=config['username'],
        password=config['pass'],
        verify_ssl=False
    )
    return client




def get_programs() -> list:

    client = create_client(config=utils.get_config_file()['originServer'])
    programs = client.get("/api/programs", params={"fields": "id,name,programType", "paging": False})
    return programs['programs']



def get_program_info(program: dict, page_size: int, client: DHIS2Client) -> list:

    print("Retrieving info for program:", program['name'])
    endpoint = generate_endpoint(program=program)
    fields = generate_fields(program=program)
    program_pager = get_total_data(program=program['id'], endpoint=endpoint, page_size=page_size, client=client)

    return program_pager, endpoint, fields




def downloading_data_tracked_entities(endpoint: str, fields: str, page: int, execution_config: DataExchangeExecutionConfig, client: DHIS2Client = None) -> dict:

    # logger = get_logger()
    # logging.info(f"Download TEIs")

    results = client.get(f"/api/tracker/{endpoint}.json", params={"program": execution_config.program['id'], "ouMode": "ACCESSIBLE", "page": page, "fields": fields, "pageSize": execution_config.page_size})
    # print(results)

    print(f"✅ {len(results[endpoint]) if endpoint in results else len(results[constants.INSTANCES])}  Data downloaded")
    return results



def downloading_data_events(endpoint: str, fields: str, page: int, execution_config: DataExchangeExecutionConfig, client: DHIS2Client = None) -> dict:

    # logger = get_logger()
    # logging.info(f"Download TEIs")
    
    results = client.get(f"/api/tracker/{endpoint}.json", params={"program": execution_config.program['id'], "ouMode": "ALL", "page": page, "fields": fields, "pageSize": execution_config.page_size})
    # print(results)

    print(f"✅ {len(results[endpoint]) if endpoint in results else len(results[constants.INSTANCES])} Data downloaded")
    return results



def downloading_relationships_data(endpoint: str, fields: str, page: int, execution_config: DataExchangeExecutionConfig, client: DHIS2Client = None) -> dict:

    # logger = get_logger()
    # logging.info(f"Download TEIs")
    
    results = client.get(f"/api/tracker/{endpoint}.json", params={"program": execution_config.program['id'], "ouMode": "ALL", "page": page, "fields": fields, "pageSize": execution_config.page_size})
    # print(results)

    print(f"✅ {len(results[endpoint]) if endpoint in results else len(results[constants.INSTANCES])} Data downloaded")
    return results
    


def send_data_to_destiny(data: dict, execution_config: DataExchangeExecutionConfig, client: DHIS2Client = None):

    try:
        # print(json.dumps(data))
        results = client.post(f"/api/tracker.json", json=data, params={"async": execution_config.async_import})
        print(results)
        # print(f"✅ Data sent to destiny server with response")
        return results
    
    except DHIS2HTTPError as e:
        # print(e)
        print("❌ Error sending data to destiny server")
        return None
    



def handle_tracked_entity(execution_config: DataExchangeExecutionConfig, origin_client: DHIS2Client, destiny_client: DHIS2Client):

    endpoint_tracker = generate_endpoint(execution_config.program)
    fields_tracker = generate_fields(execution_config.program)
    program_pager_tracker = get_total_data(program=execution_config.program['id'], endpoint=endpoint_tracker, page_size=execution_config.page_size, client=origin_client)

    orgunit_mapping_dict = {ou_mapping_item['sourceOrgUnit']: ou_mapping_item['targetOrgUnit'] for ou_mapping_item in execution_config.orgunit_mapping.get("mappings", [])} if execution_config.orgunit_mapping else None
    relationship_mapping_dict = {mapping_item['source']: mapping_item['target'] for mapping_item in execution_config.relationship_mapping.get("mappings", [])} if execution_config.relationship_mapping else None

    folder_tracker = f"control/data_exchange/{execution_config.program['id']}/tracker/{execution_config.page_size}"
    os.makedirs(folder_tracker, exist_ok=True)

    if program_pager_tracker['pageCount'] > 0:
        for page in range(1, program_pager_tracker['pageCount'] + 1):
            if os.path.exists(f"{folder_tracker}/{page}.txt"):
                print(f"⚠️ Data for {execution_config.program['name']} tracker page {page} already processed, skipping.")
                continue
            print(f"Downloading tracked entities for program {execution_config.program['name']}: page {page} / {program_pager_tracker['pageCount']}")
            data = downloading_data_tracked_entities(endpoint=endpoint_tracker, fields=fields_tracker, page=page, execution_config=execution_config, client=origin_client)
            
            data_to_transform =  data[endpoint_tracker] if endpoint_tracker in data else data[constants.INSTANCES]
            data_to_send = { "trackedEntities": handle_transfomation.transform_tracker_payload(source_payload=data_to_transform, execution_config=execution_config, orgunit_mapping_hash=orgunit_mapping_dict, relationship_mapping_hash=relationship_mapping_dict)}

            print(f"Sending tracked entities to destiny server for program {execution_config.program['name']}: page {page} / {program_pager_tracker['pageCount']}")
            send_result = send_data_to_destiny(data=data_to_send, execution_config=execution_config, client=destiny_client)
            print("\n")
            if send_result is not None:
                with open(f"{folder_tracker}/{page}.txt", "w", encoding="utf8") as f:
                    f.write(json.dumps(send_result))
    
    else:
        print(f"⚠️ No Data available for {execution_config.program['name']} tracker", "\n")
    


def handle_event(execution_config: DataExchangeExecutionConfig, origin_client: DHIS2Client, destiny_client: DHIS2Client):

    endpoint_event = constants.EVENT_ENDPOINT
    fields_event = generate_fields(execution_config.program)
    program_pager_event = get_total_data(program=execution_config.program['id'], endpoint=endpoint_event, page_size=execution_config.page_size, client=origin_client)

    orgunit_mapping_dict = {ou_mapping_item['sourceOrgUnit']: ou_mapping_item['targetOrgUnit'] for ou_mapping_item in execution_config.orgunit_mapping.get("mappings", [])} if execution_config.orgunit_mapping else None

    folder_event = f"control/data_exchange/{execution_config.program['id']}/event/{execution_config.page_size}"
    os.makedirs(folder_event, exist_ok=True)

    if program_pager_event['pageCount'] > 0:
        for page in range(1, program_pager_event['pageCount'] + 1):
            if os.path.exists(f"{folder_event}/{page}.txt"):
                print(f"⚠️ Data for {execution_config.program['name']} event page {page} already processed, skipping.")
                continue
            print(f"Downloading events for program {execution_config.program['name']}: page {page} / {program_pager_event['pageCount']}")
            data = downloading_data_events(endpoint=endpoint_event, fields=fields_event, page=page, execution_config=execution_config, client=origin_client)
            data_to_transform =  data[endpoint_event] if endpoint_event in data else data[constants.INSTANCES]
            data_to_send = { "events": handle_transfomation.transform_event_payload(source_payload=data_to_transform, execution_config=execution_config, orgunit_mapping_hash=orgunit_mapping_dict)}
            
            print(f"Sending events to destiny server for program {execution_config.program['name']}: page {page} / {program_pager_event['pageCount']}")
            send_result = send_data_to_destiny(data=data_to_send, execution_config=execution_config, client=destiny_client)
            print("\n")
            if send_result is not None:
                with open(f"{folder_event}/{page}.txt", "w", encoding="utf8") as f:
                    f.write("true")




def execute(execution_config: DataExchangeExecutionConfig):

    origin_client = create_client(config=utils.get_config_file()['originServer'])

    destiny_client = create_client(config=utils.get_config_file()['destinyServer'])

    if execution_config.program['programType'] == constants.TRACKER_PROGRAM_TYPE:
        # Tracker part
        handle_tracked_entity(execution_config=execution_config, origin_client=origin_client, destiny_client=destiny_client)
        
    if execution_config.program['programType'] == constants.EVENT_PROGRAM_TYPE:
        handle_event(execution_config=execution_config, origin_client=origin_client, destiny_client=destiny_client)

    

if __name__ == "__main__":
    execution_config = DataExchangeExecutionConfig(
        program=utils.get_config_file()['otherPrograms'][0],
        page_size=utils.get_config_file()['teiDownloadPageSize'],
        async_import=True)
    
    execute(execution_config=execution_config)