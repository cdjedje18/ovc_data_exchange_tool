from common.modules.data_exchange import data_exchange
from common.utils import utils




def execute():

    config = utils.get_config_file()
    harmonize_config = utils.get_harmonization_file()
    # print(harmonize_config['otherPrograms'])

    # print(config)

    data_exchange.clear_data_exchange_folder(program_id=harmonize_config['otherPrograms'][0]['id'])

    execution_config = data_exchange.DataExchangeExecutionConfig(
        program=harmonize_config['otherPrograms'][0],
        page_size=config['teiDownloadPageSize'],
        async_import=False)

    data_exchange.execute(execution_config=execution_config)



if __name__ == "__main__":
    execute()