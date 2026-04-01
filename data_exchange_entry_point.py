from common.modules.data_exchange import data_exchange
from common.utils import utils




def execute():

    config = utils.get_config_file()

    # print(config)

    data_exchange.clear_data_exchange_folder(program_id=config['otherPrograms'][0]['id'])

    execution_config = data_exchange.DataExchangeExecutionConfig(
        program=config['otherPrograms'][0],
        page_size=config['teiDownloadPageSize'],
        async_import=False)

    data_exchange.execute(execution_config=execution_config)



if __name__ == "__main__":
    execute()