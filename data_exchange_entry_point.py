import json

from common.modules.data_exchange import data_exchange
from common.utils import utils




def execute():

    harmonize_config = utils.get_harmonization_file()
  
    data_exchange.clear_data_exchange_folder(program_id=harmonize_config['otherPrograms'][0]['id'])

    with open("mappings/data_mappings/Mapemanto_test.json", "r", encoding="utf8") as f:
        data_mapping = json.loads(f.read())

    execution_config = data_exchange.DataExchangeExecutionConfig(
        program=harmonize_config['otherPrograms'][0],
        page_size=10,
        variable_mapping=data_mapping,
        orgunit_mapping=None,
        relationship_mapping=None,
        async_import=False,
        include_relationships=False,
        orgunits=[{'id': 'HMx8Rj0TyNh', 'name': 'CIDADE DE INHAMBANE'}]
    )

    data_exchange.execute(execution_config=execution_config)



if __name__ == "__main__":
    execute()