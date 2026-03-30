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

BENEFICIARY_PROGRAM = {"id": "pVgO58r40Au", "type": "TRACKER"}
MATRIX_PROGRAM = {"id": "coLY2kfLmlC", "type": "EVENT"}

def load_data(orgunit, program):
    folder = f"results/extract_module/{orgunit['id']}/{program['id']}"
    if not os.path.exists(folder):
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


def group_data(orgunit, program):
    data = load_data(orgunit, program)
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
                            valid_data.append({'matrix': event['event'], 'beneficiario': [te['trackedEntity'] for te in teis]})
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
                            valid_data.append({'matrix': event['event'], 'beneficiario': [te['trackedEntity'] for te in teis]})
                        break
    return valid_data



def process_data():

    orgunits = extract_data.get_organisation_units_based_on_level()

    for orgunit in orgunits:

        print("Processing data for organisation unit:", orgunit['name'])
        
        print("Processing data for program")
        valid_nid_teis, valid_family_id_teis = group_data(orgunit, BENEFICIARY_PROGRAM)
        print(f"Valid TEIs with NID or NID Ajuda: {len(valid_nid_teis)}")
        print(f"Valid TEIs with ID Family: {len(valid_family_id_teis)}")
        print("\n")
    
        print("Retrieving data for Matrix program")
        matrix_data = load_data(orgunit, MATRIX_PROGRAM)











def execute():

    pass





if __name__ == "__main__":
    pass



    



