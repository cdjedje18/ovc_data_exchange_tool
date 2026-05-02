import json

from common.modules.mixins.DataExchangeExecutionConfig import OvcDataExchangeExecutionConfig
from common.modules.ovc_data_exchange import beneficiary_exchange, family_exchange
from common.utils import utils




def execute():

    f = open("mappings/relationship_mappings/relationship_mapping.json", "r", encoding="utf8")
    relationship_mapping = json.loads(f.read())
    f.close()

    execution_config = OvcDataExchangeExecutionConfig(
        family_program={"name":"Registo e seguimento de FAMÍLIAS","programType":"WITH_REGISTRATION","id":"iSPc45re0MZ"},
        beneficiary_program={"name":"Registo e seguimento de FAMÍLIAS","programType":"WITH_REGISTRATION","id":"iSPc45re0MZ"},
        family_waiver_attribute="ntogDt6vKk5",
        beneficiary_waiver_attribute="ntogDt6vKk5",
        page_size=1,
        variable_mapping=None,
        orgunit_mapping=None,
        relationship_mapping=relationship_mapping,
        async_import=False,
        orgunits=[{"id": "xQhK3CB3nVw", "name": "CIDADE DE INHAMBANE"}],
    )

    # family_exchange.execute(execution_config=execution_config)
    beneficiary_exchange.execute(execution_config=execution_config)



if __name__ == "__main__":
    execute()