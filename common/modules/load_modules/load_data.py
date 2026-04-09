from dhis2_client import DHIS2Client
import logging
import urllib3
from common.utils import utils
import os
import json
from common.modules.extract_modules import  extract_data




def create_client(config: dict):

    client = DHIS2Client(
        base_url=config['url'],
        username=config['username'],
        password=config['pass'],
        verify_ssl=False
    )
    return client



def send_data_to_destiny(data: dict, client: DHIS2Client):
    

    try:
        results = client.post(f"/api/tracker.json", json=data, params={"async": False})
        print(results)
        return results

    except Exception as e:
        print(f"Error occurred while sending data: {e}")
        return {"error": str(e)}




def process_data(orgunit: dict):

    client = create_client(config=utils.get_config_file()['destinyServer'])

    if not os.path.exists(f"results/transform_module/{orgunit['id']}/tracked_entities.txt") or not os.path.exists(f"results/transform_module/{orgunit['id']}/events_to_create.txt"):
        # print(f"No data found for orgunit {orgunit['id']}. Skipping.")
        return

    with open(f"results/transform_module/{orgunit['id']}/tracked_entities.txt", "r", encoding="utf8") as f:
        tracked_entities = json.load(f)

    with open(f"results/transform_module/{orgunit['id']}/events_to_create.txt", "r", encoding="utf8") as f:
        events_to_create = json.load(f)

    
    data_to_send = {
        "trackedEntities": tracked_entities,
        "events": events_to_create
    }

    send_data_to_destiny(data=data_to_send, client=client)
    
    


def execute(orgunits:list | None):

    if orgunits is None:
        orgunits = extract_data.get_organisation_units_based_on_level()

    for orgunit in orgunits:
        # print(f"Processing orgunit: {orgunit['id']}")
        process_data(orgunit=orgunit)




if __name__ == "__main__":
    execute()



    



