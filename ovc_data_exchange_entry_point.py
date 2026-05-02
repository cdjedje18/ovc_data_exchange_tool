import json

from common.modules.mixins.DataExchangeExecutionConfig import OvcDataExchangeExecutionConfig
from common.modules.ovc_data_exchange import family_exchange
from common.utils import utils




def execute():


    execution_config = OvcDataExchangeExecutionConfig(
        family_program={"name":"Registo e seguimento de FAMÍLIAS","programType":"WITH_REGISTRATION","id":"iSPc45re0MZ"},
        beneficiary_program={"name":"Registo e seguimento de FAMÍLIAS","programType":"WITH_REGISTRATION","id":"iSPc45re0MZ"},
        family_waiver_attribute="ntogDt6vKk5",
        beneficiary_waiver_attribute="ntogDt6vKk5",
        page_size=10,
        variable_mapping=None,
        orgunit_mapping=None,
        relationship_mapping=None,
        async_import=False,
        orgunits=[{"id": "xQhK3CB3nVw", "name": "CIDADE DE INHAMBANE"}],
    )

    family_exchange.execute(execution_config=execution_config)



if __name__ == "__main__":
    execute()