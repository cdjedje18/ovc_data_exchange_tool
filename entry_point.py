import json
import logging
import os
import threading
import customtkinter as ctk
import sys
from common.modules.extract_modules import extract_data
from common.modules.mixins.DataExchangeExecutionConfig import HarmonizationExecutionConfig
from common.modules.transform_modules import transform_data, evaluators, transform_and_load
from common.modules.load_modules import load_data
from common.utils import utils




def execute():


    utils.create_default_folders()
    
    execution_config = HarmonizationExecutionConfig(
        page_size=10,
        beneficiary_program_server="origin_server",
        orgunits=[{'id': 'HMx8Rj0TyNh', 'name': 'CIDADE DE INHAMBANE'}]
    )


    extract_data.execute(harmonization_execution_config=execution_config)

    # evaluators.execute(harmonization_execution_config=execution_config)
    
    # transform_and_load.execute(harmonization_execution_config=execution_config)

    # load_data.execute(harmonization_execution_config=execution_config)
    


if __name__ == "__main__":
    execute()