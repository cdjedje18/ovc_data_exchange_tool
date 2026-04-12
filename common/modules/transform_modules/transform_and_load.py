from dhis2_client import DHIS2Client
import logging
import pandas
import urllib3
from common import constants
from common.modules.mixins.DataExchangeExecutionConfig import HarmonizationExecutionConfig
from common.utils import utils
import os
import json
from common.modules.extract_modules import  extract_data
from common.modules.load_modules import load_data
from datetime import datetime



def generating_attributes(matrix_event_data_value_dict:dict, mapping:dict):

    attributes = []

    mapping_attributes = mapping.get("attributes", [])
    for mapping_attr in mapping_attributes:

        attr_id = mapping_attr['attributeId']

        if "defaultValue" in mapping_attr:
            attributes.append({
                "attribute": attr_id,
                "value": mapping_attr['defaultValue']
            })
            continue

        de_id = mapping_attr['dataElementId']
        

        if de_id in matrix_event_data_value_dict:
            attributes.append({
                "attribute": attr_id,
                "value": matrix_event_data_value_dict[de_id]['value']
            })

    return attributes



def generating_data_values(matrix_event_data_value_dict:dict, data_values_mapping:dict):

    data_values = []

    for data_value_mapping_item in data_values_mapping:

        
        target_de_id = data_value_mapping_item['targetDataElementId']

        if "defaultValue" in data_value_mapping_item:
            data_values.append({
                "dataElement": target_de_id,
                "value": data_value_mapping_item['defaultValue']
            })
            continue

        source_de_id = data_value_mapping_item['sourceDataElementId']

        if source_de_id in matrix_event_data_value_dict:
            data_values.append({
                "dataElement": target_de_id,
                "value": matrix_event_data_value_dict[source_de_id]['value'],
                'createdAt': matrix_event_data_value_dict[source_de_id].get('createdAt'),
                'updatedAt': matrix_event_data_value_dict[source_de_id].get('updatedAt'),
            })

    return data_values

    

def is_mapping_event_valid(matrix_event_data_value_dict:dict, event_mapping:dict):

    
    for event_mapping_item in event_mapping['mapping']:
        if "defaultValue" in event_mapping_item:
            continue
        de_id = event_mapping_item['sourceDataElementId']
        if de_id in matrix_event_data_value_dict and matrix_event_data_value_dict[de_id].get('value'):
            return True

    return False



def generated_event_date(data_values: list):

    for dv in data_values:
        if "createdAt" in dv and dv['createdAt']:
            return dv['createdAt']

    return -1


def get_latest_enrollment(enrollments):
    return max(
        enrollments,
        key=lambda e: datetime.fromisoformat(e["enrolledAt"].replace("Z", "+00:00"))
    )

def find_valid_event_enrollment(enrollments: list):

    if len(enrollments) == 0:
        return -1

    for enrollment in enrollments:
        if enrollment.get('status') == constants.ENROLLMENT_ACTIVE_STATUS:
            return enrollment['enrollment']
    
    latest_enrollment = get_latest_enrollment(enrollments)

    return latest_enrollment['enrollment']


def generate_events(matrix_event_data_value_dict:dict, mapping:dict, beneficiario:dict, original_event:dict=None):

    events = []

    program_stages_mapping = mapping.get("programStages", [])
    for program_stage_mapping in program_stages_mapping:
        # print(program_stage_mapping)
        for mapping_event in program_stage_mapping['eventsMapping']:

            is_valid = is_mapping_event_valid(matrix_event_data_value_dict=matrix_event_data_value_dict, event_mapping=mapping_event)
            if is_valid:
                new_event = {
                    "program": program_stage_mapping['programId'],
                    "programStage": program_stage_mapping['programStageId'],
                    "orgUnit": original_event['orgUnit'],
                    "trackedEntity": beneficiario['trackedEntity'],
                    "enrollment": find_valid_event_enrollment(beneficiario.get('enrollments', [])),
                    "dataValues": generating_data_values(matrix_event_data_value_dict=matrix_event_data_value_dict, data_values_mapping=mapping_event.get('mapping', [])),
                }
                new_event['occurredAt'] = generated_event_date(data_values=new_event['dataValues'])
                events.append(new_event)
                

    return events




def transform_data(orgunits: list | None):

    if orgunits is None:
        orgunits = extract_data.get_organisation_units_based_on_level()

    mapping = utils.get_mapping_file()
    programs = utils.get_harmonization_file().get("programs", [])

    beneficiary_program = [program for program in programs if program['programType'] == constants.TRACKER_PROGRAM_TYPE][0]
    matrix_program = [program for program in programs if program['programType'] == constants.EVENT_PROGRAM_TYPE][0]

    print("Starting data transformation process...")
    for orgunit in orgunits:
        print(f"Processing organisation unit: {orgunit['name']} (ID: {orgunit['id']})")

        if not os.path.exists(f"results/evaluator_module/{orgunit['id']}/validated"):
            print(f"⚠️ No validated data found for organisation unit {orgunit['name']}. Please run the evaluators module first. Skipping.")
            continue

        beneficiarios_original_data = extract_data.load_data(orgunit=orgunit, program=beneficiary_program)
        matrix_original_data = extract_data.load_data(orgunit=orgunit, program=matrix_program)

        beneficiarios_dict = {beneficiario['trackedEntity']: beneficiario for beneficiario in beneficiarios_original_data}
        matrix_dict = {event['event']: event for event in matrix_original_data}
        

        print("Loading valid data for transformation...")
        validated_files = os.listdir(f"results/evaluator_module/{orgunit['id']}/validated")
        
        valid_data = []
        for file in validated_files:
            if not file.endswith('.csv'):
                print(f"⚠️  File {file} in validated folder is not a csv file. Skipping.")
                continue

            valid_data_csv = pandas.read_csv(f"results/evaluator_module/{orgunit['id']}/validated/{file}")
            for index, record in valid_data_csv.iterrows():
                valid_data.append({
                   'matrix_event_id':record['matrix_event_id'],
                   'beneficiary_id':record['beneficiary_id']
                })


        print(f"Transforming data...")
        tracked_entities = []
        events_to_create = []
        for index, record in enumerate(valid_data):  
            matrix_event_id = record['matrix_event_id']
            beneficiary_id = record['beneficiary_id']

            if beneficiary_id not in beneficiarios_dict or matrix_event_id not in matrix_dict:
                print(f"⚠️  Record with beneficiary_id {beneficiary_id} and matrix_event_id {matrix_event_id} not found in original data. Skipping.")
                raise ValueError(f"Record with beneficiary_id {beneficiary_id} and matrix_event_id {matrix_event_id} not found in original data. Please download the data again")

            matrix_event = matrix_dict[matrix_event_id]
            beneficiario = beneficiarios_dict[beneficiary_id]

            matrix_event_data_value_dict = {dv['dataElement']: dv for dv in matrix_event.get('dataValues', [])}
            beneficiario['attributes'].extend(generating_attributes(matrix_event_data_value_dict=matrix_event_data_value_dict, mapping=mapping))

            beneficiario_events = generate_events(matrix_event_data_value_dict=matrix_event_data_value_dict, mapping=mapping, beneficiario=beneficiario, original_event=matrix_event)
            
            tracked_entities.append(beneficiario)
            events_to_create.extend(beneficiario_events)
    
        data_folder = f"results/transform_module/{orgunit['id']}"
        os.makedirs(data_folder, exist_ok=True)

        with open(f"{data_folder}/tracked_entities.txt", "w", encoding="utf8") as f:
            json.dump(tracked_entities, f)

        with open(f"{data_folder}/events_to_create.txt", "w", encoding="utf8") as f:
            json.dump(events_to_create, f)

        
        print(f"Total tracked entities to create/update: {len(tracked_entities)} for organisation unit {orgunit['name']}")
        print(f"Total events to create: {len(events_to_create)} for organisation unit {orgunit['name']}")

        print(f"Data transformation completed for organisation unit {orgunit['name']}.", "\n")

    print("Data transformation completed.")



def execute(harmonization_execution_config:HarmonizationExecutionConfig):

    # orgunits = extract_data.get_organisatsion_units_based_on_level()

    # print(orgunits)

    orgunits = harmonization_execution_config.orgunits if harmonization_execution_config and harmonization_execution_config.orgunits else extract_data.get_organisation_units_based_on_level()

    transform_data(orgunits=orgunits)

    load_data.execute(harmonization_execution_config=harmonization_execution_config)

    









if __name__ == "__main__":
    execute()



    



