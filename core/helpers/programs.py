import json
import urllib3
from dhis2_client import DHIS2Client

from common.utils import utils

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


DEFAULT_FIELDS = "id,name"


def _build_client(server_key: str = "originServer") -> DHIS2Client:
    """Create a DHIS2 client using the configured server credentials."""
    config = utils.get_config_file()
    server = config.get(server_key, {})

    missing = [key for key in ("url", "username", "pass") if not server.get(key)]
    if missing:
        raise KeyError(
            f"Missing DHIS2 configuration keys in '{server_key}': {', '.join(missing)}"
        )

    return DHIS2Client(
        base_url=server["url"],
        username=server["username"],
        password=server["pass"],
        verify_ssl=False,
    )


def get_program_attributes(program: dict, client: DHIS2Client):

    params = dict()

    params = {"fields": "id,name,programTrackedEntityAttributes[trackedEntityAttribute[id,name,valueType]],programStages[id,name,programStageDataElements[dataElement[id,name,valueType]]]"}
    
    program_data = client.get(f"/api/programs/{program['id']}", params=params)

    return [attribute['trackedEntityAttribute'] for attribute in program_data.get("programTrackedEntityAttributes", [])]


def get_program_data_elements(program: dict, client: DHIS2Client):

    params = dict()

    params = {"fields": "id,name,programStages[id,name,programStageDataElements[dataElement[id,name,valueType]]]"}
    
    program_data = client.get(f"/api/programs/{program['id']}", params=params)

    return [data_element['dataElement'] for stage in program_data.get("programStages", []) for data_element in stage.get("programStageDataElements", [])]



if __name__ == "__main__":
    pass
