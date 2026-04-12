from dhis2_client import DHIS2Client
import logging
import urllib3
from common import constants
from common.modules.mixins.DataExchangeExecutionConfig import HarmonizationExecutionConfig
from common.utils import utils
import os
import json



def get_logger():
    logger = utils.set_logger(log_file="extract_data.log")
    return logger


def load_data(orgunit, program):
    # print(orgunit, program)
    folder = f"results/extract_module/{orgunit['id']}/{program['id']}"
    if not os.path.exists(folder):
        print(f"⚠️ No local data found for program {program['name']} and organisation unit {orgunit['name']}. Skipping.")
        return []
    
    data = []
    key = 'trackedEntities' if program['programType'] == constants.TRACKER_PROGRAM_TYPE else 'events'
    instance_key = constants.INSTANCES
    for file_name in sorted(os.listdir(folder)):
        if file_name.endswith('.txt'):
            file_path = os.path.join(folder, file_name)
            with open(file_path, 'r', encoding='utf8') as f:
                page_data = json.load(f)
                if key in page_data:
                    data.extend(page_data[key])
                elif instance_key in page_data:
                    data.extend(page_data[instance_key])

    return data


def generate_endpoint(program:dict):

    if program['programType'] == constants.TRACKER_PROGRAM_TYPE:
      return "trackedEntities"

    if program['programType'] == constants.EVENT_PROGRAM_TYPE:
      return "events"
    
    raise ValueError("Endpoint not correct defiend in config file")


def generate_fields(program:dict):

    if program['programType'] == constants.TRACKER_PROGRAM_TYPE:
      return "*,enrollments[*,!events,!attributes]"

    if program['programType'] == constants.EVENT_PROGRAM_TYPE:
      return "*"
    
    raise ValueError("Endpoint not correct defiend in config file")
      



def get_organisation_units_based_on_level() -> list:

    # logger = get_logger()
    # logging.info(f"Download OUs")

    """
    Get origin server orgunits based on the defined levels in config file.
    If not set it will use the district level (level 3) by default.
    This is to improve the data retriving process
    """

    config = utils.get_config_file()

    client = DHIS2Client(
        base_url=config['originServer']['url'],
        username=config['originServer']['username'],
        password=config['originServer']['pass'],  # Basic auth by default,
        verify_ssl=False
    )

    level = config['downloadLevel'] if 'downloadLevel' in config else 3 
    results = client.get("/api/organisationUnits", params={"level": level, "fields": "id,name", "paging": False})
    # logger.info(f"Downloaded {len(results['organisationUnits'])} organisation units")
    return results['organisationUnits']



def get_total_data(program:str, endpoint:str, orgunit:str, page_size:int, client: DHIS2Client):

    results = client.get(f"/api/tracker/{endpoint}.json", params={"totalPages": True, "program": program, "orgUnit": orgunit, "ouMode": "DESCENDANTS", "pageSize": page_size, "fields": "created"})
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


def downloading_tracked_entities(execution_config: HarmonizationExecutionConfig = None) -> list:

    # logger = get_logger()
    # logging.info(f"Download TEIs")

    """
    Downloading teis and storing local so improve job performance,
    The job downloads the data per organisaiton units.
    """

    # print(execution_config.orgunits)

    orgunits = execution_config.orgunits if execution_config and execution_config.orgunits else get_organisation_units_based_on_level()

    config = utils.get_config_file()
    harmonization_programs = [config['matrixProgram'], {**config['beneficiaryProgram'], 'server': execution_config.beneficiary_program_server}]

    origin_client = create_client(config['originServer'])

    destiny_client = create_client(config['destinyServer'])

    # org_units = get_organisation_units_based_on_level()

    page_size =  execution_config.page_size if execution_config and execution_config.page_size else config['teiDownloadPageSize'] if 'teiDownloadPageSize' in config else 500

    for program in harmonization_programs:

        client = destiny_client if 'server' in program and program['server'] == 'destiny_server' else origin_client

        for orgunit in orgunits: 
            
            # print(f"Retrieving info for program: {program['name']} for organisation unit: {orgunit['name']}")
            endpoint = generate_endpoint(program=program)
            fields = generate_fields(program=program)
            program_pager = get_total_data(program=program['id'], endpoint=endpoint, orgunit=orgunit['id'], page_size=page_size, client=client)

            if program_pager['pageCount'] > 0:

                data_folder = f"results/extract_module/{orgunit['id']}/{program['id']}"
                os.makedirs(data_folder, exist_ok=True)

                for page in range(1, program_pager['pageCount'] + 1):

                    if os.path.exists(f"{data_folder}/{page}.txt"):
                        print(f"⚠️ Data for page {page} already exists, skipping download.")
                        continue

                    print(f"Downloading data for program: {program['name']} for organisation unit: {orgunit['name']} page: {page} / {program_pager['pageCount']}")
                    results = client.get(f"/api/tracker/{endpoint}.json", params={"program": program['id'], "orgUnit": orgunit['id'], "ouMode": "DESCENDANTS", "page": page, "fields": fields, "pageSize": page_size})
                
                    with open(f"{data_folder}/{page}.txt", "w", encoding="utf8") as f:
                        f.write(json.dumps(results))
                    
                    print(f"✅ Data downloaded and saved", "\n")
            
            else:
                print(f"⚠️ No Data available", "\n")




def execute(harmonization_execution_config: HarmonizationExecutionConfig = None):

    if harmonization_execution_config is None:
        harmonization_execution_config = HarmonizationExecutionConfig(page_size=500, beneficiary_program_server="origin_server")

    downloading_tracked_entities(execution_config=harmonization_execution_config)





if __name__ == "__main__":
    pass



    



