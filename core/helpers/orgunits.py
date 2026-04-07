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


def get_organisation_units_by_parent_id(
    parent_id: str,
    fields: str = DEFAULT_FIELDS,
    include_descendants: bool = False,
    server_key: str = "originServer",
) -> list:
    """
    Retrieve organisation units using a parent id.

    Args:
        parent_id: DHIS2 parent organisation unit id.
        fields: Comma-separated DHIS2 fields to return.
        include_descendants: If True, returns all descendants; otherwise only direct children.
        server_key: Config section to use from config.json.
    """
    if not parent_id:
        raise ValueError("parent_id is required")

    client = _build_client(server_key=server_key)
    filter_value = (
        f"path:like:{parent_id}" if include_descendants else f"parent.id:eq:{parent_id}"
    )

    response = client.get(
        "/api/organisationUnits",
        params={
            "filter": filter_value,
            "fields": fields,
            "paging": False,
            "order": "name:asc",
        },
    )

    return response.get("organisationUnits", [])



def get_organisation_units_by_level(
    level: int,
    fields: str = DEFAULT_FIELDS,
    server_key: str = "originServer",
) -> list:
    """
    Retrieve organisation units using a level.

    Args:
        level: DHIS2 organisation unit level.
        fields: Comma-separated DHIS2 fields to return.
        server_key: Config section to use from config.json.
    """
    if not level:
        raise ValueError("level is required")

    client = _build_client(server_key=server_key)
    filter_value = f"level:eq:{level}"

    response = client.get(
        "/api/organisationUnits",
        params={
            "filter": filter_value,
            "fields": fields,
            "paging": False,
            "order": "name:asc",
        },
    )

    return response.get("organisationUnits", [])


if __name__ == "__main__":
    pass
