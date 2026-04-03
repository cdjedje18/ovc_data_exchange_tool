from dhis2_client import DHIS2Client
import logging
import urllib3
from common.utils import utils
import os
import json
from common.modules.extract_modules import  extract_data


NID_ATTRIBUTE_ID = "ZPKAQj86KBI"
NID_AJUDA_ATTRIBUTE_ID = "coFfWIjsmyL"
ID_FAMILY_ATTRIBUTE_ID = "hXpyioqAugh"


NID_DATA_ELEMENT_ID = "dqrgtT6GVF7"
NEW_NID_DATA_ELEMENT_ID = "mvJZJVVtclN"
NID_CCR_DATA_ELEMENT_ID = "JjYqVlKOhJp"

ID_FAMILY_DATA_ELEMENT_ID = "uWxJlxRdELE"

BENEFICIARY_PROGRAM = {"id": "pVgO58r40Au", "name": "Beneficiary Program", "type": "TRACKER"}
MATRIX_PROGRAM = {"id": "coLY2kfLmlC", "name": "Matrix Program", "type": "EVENT"}



def load_data(orgunit, program):
    # print(orgunit, program)
    folder = f"results/extract_module/{orgunit['id']}/{program['id']}"
    if not os.path.exists(folder):
        print(f"⚠️ No local data found for program {program['name']} and organisation unit {orgunit['name']}. Skipping.")
        return []
    
    data = []
    key = 'trackedEntities' if program['type'] == 'TRACKER' else 'events'
    for file_name in sorted(os.listdir(folder)):
        if file_name.endswith('.txt'):
            file_path = os.path.join(folder, file_name)
            with open(file_path, 'r', encoding='utf8') as f:
                page_data = json.load(f)
                if key in page_data:
                    data.extend(page_data[key])
    return data


def group_data(data):
    # data = load_data(orgunit, program)
    valid_nid_teis = {}
    processed = set()
    # First pass: NID or NID ajuda
    for item in data:
        te_id = item['trackedEntity']
        if te_id in processed:
            continue
        for attr in item['attributes']:
            if attr['attribute'] in [NID_ATTRIBUTE_ID, NID_AJUDA_ATTRIBUTE_ID] and attr.get('value'):
                nid_value = attr['value']
                if nid_value not in valid_nid_teis:
                    valid_nid_teis[nid_value] = []
                valid_nid_teis[nid_value].append(item)
                processed.add(te_id)
                break


    # Second pass: ID family for remaining
    valid_family_id_teis = {}
    for item in data:
        te_id = item['trackedEntity']
        if te_id in processed:
            continue
        for attr in item['attributes']:
            if attr['attribute'] == ID_FAMILY_ATTRIBUTE_ID and attr.get('value'):
                family_id_value = attr['value']
                if family_id_value not in valid_family_id_teis:
                    valid_family_id_teis[family_id_value] = []
                valid_family_id_teis[family_id_value].append(item)
                processed.add(te_id)
                break

    return valid_nid_teis, valid_family_id_teis



def match_data(matrix_data, valid_nid_teis, valid_family_id_teis):
    valid_data = []
    non_valid_data = []
    matched_events = set()
    for event in matrix_data:
        matched = False
        # First, check NID dataElements
        for de in [NID_DATA_ELEMENT_ID, NEW_NID_DATA_ELEMENT_ID, NID_CCR_DATA_ELEMENT_ID]:
            for dv in event.get('dataValues', []):
                if dv['dataElement'] == de and dv.get('value'):
                    nid_val = dv['value']
                    if nid_val in valid_nid_teis:
                        teis = valid_nid_teis[nid_val]
                        if len(teis) == 1:
                            valid_data.append({'matrix': event, 'beneficiario': teis[0]})
                        else:
                            non_valid_data.append({'matrix': event['event'], 'beneficiario': [te['trackedEntity'] for te in teis]})
                        matched_events.add(event['event'])
                        matched = True
                        break
            if matched:
                break
            
        if not matched and event['event'] not in matched_events:
            # Check ID_FAMILY
            for dv in event.get('dataValues', []):
                if dv['dataElement'] == ID_FAMILY_DATA_ELEMENT_ID and dv.get('value'):
                    family_val = dv['value']
                    if family_val in valid_family_id_teis:
                        teis = valid_family_id_teis[family_val]
                        if len(teis) == 1:
                            valid_data.append({'matrix': event, 'beneficiario': teis[0]})
                        else:
                            non_valid_data.append({'matrix': event['event'], 'beneficiario': [te['trackedEntity'] for te in teis]})
                        break

    return valid_data, non_valid_data



def process_data(orgunits: list):

    for orgunit in orgunits:

        print("Initializing transformation for organisation unit:", orgunit['name'])
        
        beneficiary_data = load_data(orgunit, BENEFICIARY_PROGRAM)

        if len(beneficiary_data) == 0:
            print("\n")
            continue

        valid_nid_teis, valid_family_id_teis = group_data(beneficiary_data)
        print(f"Valid TEIs with NID or NID Ajuda: {len(valid_nid_teis)}")
        print(f"Valid TEIs with ID Family: {len(valid_family_id_teis)}")
        print("\n")
    
        print("Retrieving data for Matrix program")
        matrix_data = load_data(orgunit, MATRIX_PROGRAM)

        match_data_result, non_valid_data = match_data(matrix_data=matrix_data, valid_nid_teis=valid_nid_teis, valid_family_id_teis=valid_family_id_teis)

        data_folder = f"results/transform_module/{orgunit['id']}"
        os.makedirs(data_folder, exist_ok=True)

        with open(f"results/transform_module/{orgunit['id']}/valid_data.txt", "w", encoding="utf8") as f:
            json.dump(match_data_result, f)




def generating_attributes(matrix_event_data_value_dict:dict, mapping:dict):

    attributes = []

    mapping_attributes = mapping.get("attributes", [])
    for mapping_attr in mapping_attributes:

        if "defaultValue" in mapping_attr:
            attributes.append({
                "attribute": attr_id,
                "value": mapping_attr['defaultValue']
            })
            continue

        de_id = mapping_attr['dataElementId']
        attr_id = mapping_attr['attributeId']

        if de_id in matrix_event_data_value_dict:
            attributes.append({
                "attribute": attr_id,
                "value": matrix_event_data_value_dict[de_id]['value']
            })

    return attributes



def generating_data_values(matrix_event_data_value_dict:dict, data_values_mapping:dict):

    data_values = []

    for data_value_mapping_item in data_values_mapping:

        if "defaultValue" in data_value_mapping_item:
            data_values.append({
                "dataElement": target_de_id,
                "value": data_value_mapping_item['defaultValue']
            })
            continue

        source_de_id = data_value_mapping_item['sourceDataElementId']
        target_de_id = data_value_mapping_item['targetDataElementId']

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
                    "dataValues": generating_data_values(matrix_event_data_value_dict=matrix_event_data_value_dict, data_values_mapping=mapping_event.get('mapping', [])),
                }
                new_event['occureddAt'] = generated_event_date(data_values=new_event['dataValues'])
                events.append(new_event)
                

    return events




def transform_data(orgunits: list):

    mapping = utils.get_mapping_file()

    print("Starting data transformation process...")
    for orgunit in orgunits:
        print(f"Processing organisation unit: {orgunit['name']} (ID: {orgunit['id']})")

        if os.path.exists(f"results/transform_module/{orgunit['id']}/valid_data.txt") is False:
            print(f"⚠️ No valid data for organisation unit {orgunit['name']}. Skipping transformation.")
            continue

        print("Loading valid data for transformation...")
        with open(f"results/transform_module/{orgunit['id']}/valid_data.txt", "r", encoding="utf8") as f:
            valid_data = json.load(f)
        print(f"Valid data loaded: {len(valid_data)} records")

        print(f"Transforming data...")
        tracked_entities = []
        events_to_create = []
        for record in valid_data:
            matrix_event = record['matrix']
            beneficiario = record['beneficiario']

            matrix_event_data_value_dict = {dv['dataElement']: dv for dv in matrix_event.get('dataValues', [])}
            beneficiario['attributes'].extend(generating_attributes(matrix_event_data_value_dict=matrix_event_data_value_dict, mapping=mapping))

            beneficiario_events = generate_events(matrix_event_data_value_dict=matrix_event_data_value_dict, mapping=mapping, beneficiario=beneficiario, original_event=matrix_event)
            
            tracked_entities.append(beneficiario)
            events_to_create.extend(beneficiario_events)
    
        with open(f"results/transform_module/{orgunit['id']}/tracked_entities.txt", "w", encoding="utf8") as f:
            json.dump(tracked_entities, f)

        with open(f"results/transform_module/{orgunit['id']}/events_to_create.txt", "w", encoding="utf8") as f:
            json.dump(events_to_create, f)

        
        print(f"Total tracked entities to create/update: {len(tracked_entities)} for organisation unit {orgunit['name']}")
        print(f"Total events to create: {len(events_to_create)} for organisation unit {orgunit['name']}")

        print(f"Data transformation completed for organisation unit {orgunit['name']}.", "\n")




    process_data(orgunits=orgunits)
    print("Data transformation completed.")



def execute():

    orgunits = extract_data.get_organisation_units_based_on_level()

    process_data(orgunits=orgunits)

    transform_data(orgunits=orgunits)





if __name__ == "__main__":
    execute()



    



