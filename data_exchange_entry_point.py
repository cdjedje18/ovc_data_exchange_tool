from common.modules.data_exchange import data_exchange
from common.utils import utils




def execute():

    harmonize_config = utils.get_harmonization_file()
  
    data_exchange.clear_data_exchange_folder(program_id=harmonize_config['otherPrograms'][0]['id'])

    execution_config = data_exchange.DataExchangeExecutionConfig(
        program=harmonize_config['otherPrograms'][0],
        page_size=1,
        variable_mapping=None,
        orgunit_mapping=None,
        relationship_mapping=None,
        async_import=False,
        include_relationships=False
    )

    data_exchange.execute(execution_config=execution_config)



if __name__ == "__main__":
    execute()