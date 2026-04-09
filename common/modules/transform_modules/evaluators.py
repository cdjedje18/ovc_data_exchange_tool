import json
import os

import pandas as pd
from common.modules.extract_modules.extract_data import get_organisation_units_based_on_level
from common.utils import utils


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

    evaluator_criterias = utils.get_evaluator_criterias()
    nids_attributes = [criteria['attribute'] for criteria in evaluator_criterias['nid']['target']]


    # data = load_data(orgunit, program)
    grouped_nid_teis = {}
    processed = set()
    # First pass: NID or NID ajuda
    for item in data:
        te_id = item['trackedEntity']
        if te_id in processed:
            continue
        for attr in item['attributes']:
            if attr['attribute'] in nids_attributes and attr.get('value'):
                nid_value = attr['value']
                if nid_value not in grouped_nid_teis:
                    grouped_nid_teis[nid_value] = []
                grouped_nid_teis[nid_value].append(item)
                processed.add(te_id)
                break


    # Second pass: ID family for remaining
    grouped_family_id_teis = {}
    for item in data:
        te_id = item['trackedEntity']
        if te_id in processed:
            continue
        for attr in item['attributes']:
            if attr['attribute'] == evaluator_criterias['familyId']['attribute'] and attr.get('value'):
                family_id_value = attr['value']
                if family_id_value not in grouped_family_id_teis:
                    grouped_family_id_teis[family_id_value] = []
                grouped_family_id_teis[family_id_value].append(item)
                processed.add(te_id)
                break

    return grouped_nid_teis, grouped_family_id_teis



def add_hash_values(data: list[dict], type: str) -> list[dict]:

    """Add a 'hash_values' field to each item in the data list, containing a dictionary of key-value pairs from the specified type."""

    new_data = []
    key = "attributes" if type == "TRACKER" else "dataValues"
    key_data = "attribute" if type == "TRACKER" else "dataElement"
    for item in data:
        new_data.append({
            **item,
            'hash_values': {value[key_data]: value['value'] for value in item[key]}
        })


    return new_data



def nid_evaluation(matrix_data: list, grouped_nid_teis:dict):

    evaluator_criterias = utils.get_evaluator_criterias()
    criteria = evaluator_criterias['nid']

    processed_events = set()

    valid_nid_matchs = []
    non_valid_nid_matchs = []

    for event in matrix_data:
        for criteria_item in criteria['source']:
            if criteria_item['dataElement'] in event['hash_values']:
                nid_value = event['hash_values'][criteria_item['dataElement']]
                if nid_value in grouped_nid_teis:
                    if len(grouped_nid_teis[nid_value]) > 1:
                        non_valid_nid_matchs.append({'matrix_event': event, 'beneficiaries': grouped_nid_teis[nid_value]})
                        processed_events.add(event['event'])
                    if len(grouped_nid_teis[nid_value]) == 1:
                        valid_nid_matchs.append({'matrix_event': event, 'beneficiaries': grouped_nid_teis[nid_value]})
                        processed_events.add(event['event'])
                    break
                else:
                    continue
                

    return valid_nid_matchs, non_valid_nid_matchs, processed_events




def family_id_evaluation(matrix_data: list, grouped_family_id_teis:dict):

    evaluator_criterias = utils.get_evaluator_criterias()
    criteria = evaluator_criterias['familyId']

    processed_events = set()

    valid_matchs = []
    non_valid_matchs = []

    family_id_data_element = criteria.get('dataElement')
    secondary_criterias = [
        item for item in criteria.get('secundaries', [])
        if item.get('attribute') and item.get('dataElement')
    ]

    for event in matrix_data:
        if family_id_data_element not in event['hash_values']:
            continue

        family_id_value = event['hash_values'][family_id_data_element]
        if not family_id_value or family_id_value not in grouped_family_id_teis:
            continue

        beneficiaries = grouped_family_id_teis[family_id_value]

        if len(beneficiaries) == 1:
            valid_matchs.append({'matrix_event': event, 'beneficiaries': beneficiaries})
            processed_events.add(event['event'])
            continue

        filtered_beneficiaries = [
            beneficiary for beneficiary in beneficiaries
            if all(
                event['hash_values'].get(secondary['dataElement'])
                and beneficiary.get('hash_values', {}).get(secondary['attribute']) == event['hash_values'].get(secondary['dataElement'])
                for secondary in secondary_criterias
            )
        ] if secondary_criterias else beneficiaries

        if len(filtered_beneficiaries) == 1:
            valid_matchs.append({'matrix_event': event, 'beneficiaries': filtered_beneficiaries})
            processed_events.add(event['event'])
        else:
            non_valid_matchs.append({'matrix_event': event, 'beneficiaries': filtered_beneficiaries})

    return valid_matchs, non_valid_matchs, processed_events


def demographic_evaluation(matrix_data: list, beneficiaries: list, processed_teis: set):

    evaluator_criterias = utils.get_evaluator_criterias()
    criterias = [
        item for item in evaluator_criterias.get('demographic', [])
        if item.get('attribute') and item.get('dataElement')
    ]

    processed_events = set()

    valid_matchs = []
    non_valid_matchs = []

    if not criterias:
        return valid_matchs, non_valid_matchs, processed_events

    for event in matrix_data:
        if not all(event['hash_values'].get(criteria['dataElement']) for criteria in criterias):
            continue

        matches = []
        for beneficiary in beneficiaries:
            te_id = beneficiary['trackedEntity']
            if te_id in processed_teis:
                continue

            if all(
                beneficiary.get('hash_values', {}).get(criteria['attribute'])
                and beneficiary['hash_values'][criteria['attribute']] == event['hash_values'][criteria['dataElement']]
                for criteria in criterias
            ):
                matches.append(beneficiary)

        if len(matches) == 1:
            valid_matchs.append({'matrix_event': event, 'beneficiaries': matches})
            processed_events.add(event['event'])
            processed_teis.update(beneficiary['trackedEntity'] for beneficiary in matches)
        elif len(matches) > 1:
            non_valid_matchs.append({'matrix_event': event, 'beneficiaries': matches})

    return valid_matchs, non_valid_matchs, processed_events



def process_evaluation_results(valid_nid_matchs, non_valid_nid_matchs, valid_family_id_matchs, non_valid_family_id_matchs, valid_demographic_matchs, non_valid_demographic_matchs):
    all_valid_matchs = []
    all_non_valid_matchs = []

    all_valid_matchs.extend(valid_nid_matchs)
    all_valid_matchs.extend(valid_family_id_matchs)
    all_valid_matchs.extend(valid_demographic_matchs)

    all_non_valid_matchs.extend(non_valid_nid_matchs)
    all_non_valid_matchs.extend(non_valid_family_id_matchs)
    all_non_valid_matchs.extend(non_valid_demographic_matchs)

    return all_valid_matchs, all_non_valid_matchs


def _normalize_report_value(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value



def _build_report_column_mappings(report_structure: dict, matchs: list):
    matrix_columns = []
    beneficiary_columns = []

    matrix_column_map = {}
    beneficiary_column_map = {}

    for item in report_structure.get('headers', []):
        data_element = item.get('dataElement')
        data_element_name = item.get('dataElementName') or data_element
        attribute = item.get('attribute')
        attribute_name = item.get('attributeName') or attribute

        if data_element and data_element not in matrix_column_map:
            matrix_column_map[data_element] = data_element_name
            matrix_columns.append(data_element_name)

        if attribute and attribute not in beneficiary_column_map:
            beneficiary_column_map[attribute] = attribute_name
            beneficiary_columns.append(attribute_name)

    return matrix_columns, beneficiary_columns, matrix_column_map, beneficiary_column_map



def _build_report_rows(
    matchs: list,
    status: str,
    orgunit: dict,
    fieldnames: list[str],
    matrix_column_map: dict,
    beneficiary_column_map: dict,
):
    rows = []

    for match in matchs:
        event = match.get('matrix_event', {})
        beneficiaries = match.get('beneficiaries') or [{}]

        for beneficiary in beneficiaries:
            row = {field: "" for field in fieldnames}
            row.update({
                'matrix_event_id': event.get('event', ''),
                'beneficiary_id': beneficiary.get('trackedEntity', ''),
                'status': status,
                'orgunit_id': orgunit.get('id', ''),
                'orgunit_name': orgunit.get('name', ''),
                'beneficiary_count': len(match.get('beneficiaries', []))
            })

            for key, value in event.get('hash_values', {}).items():
                column_name = matrix_column_map.get(key)
                if column_name in row:
                    row[column_name] = _normalize_report_value(value)

            for key, value in beneficiary.get('hash_values', {}).items():
                column_name = beneficiary_column_map.get(key)
                if column_name in row:
                    row[column_name] = _normalize_report_value(value)

            rows.append(row)

    return rows



def generate_report(orgunit: dict, all_valid_matchs, all_non_valid_matchs):
    with open("harmonization_report_strucure.json", "r", encoding="utf8") as f:
        report_structure = json.load(f)

    data_folder = f"results/evaluator_module/{orgunit['id']}"
    pending_folder = os.path.join(data_folder, "pending")

    os.makedirs(data_folder, exist_ok=True)
    os.makedirs(pending_folder, exist_ok=True)

    matrix_columns, beneficiary_columns, matrix_column_map, beneficiary_column_map = _build_report_column_mappings(
        report_structure,
        all_valid_matchs + all_non_valid_matchs,
    )

    fieldnames = [
        'matrix_event_id',
        'beneficiary_id',
        'status',
        'orgunit_id',
        'orgunit_name',
        'beneficiary_count',
    ]
    fieldnames.extend(matrix_columns)
    fieldnames.extend(beneficiary_columns)
    # fieldnames.extend(['matrix_event_payload', 'beneficiary_payload'])

    valid_rows = _build_report_rows(
        all_valid_matchs,
        'valid',
        orgunit,
        fieldnames,
        matrix_column_map,
        beneficiary_column_map,
    )
    non_valid_rows = _build_report_rows(
        all_non_valid_matchs,
        'non_valid',
        orgunit,
        fieldnames,
        matrix_column_map,
        beneficiary_column_map,
    )

    valid_report_path = os.path.join(pending_folder, 'valid_matches_report.csv')
    non_valid_report_path = os.path.join(pending_folder, 'non_valid_matches_report.csv')

    valid_df = pd.DataFrame(valid_rows, columns=fieldnames)
    non_valid_df = pd.DataFrame(non_valid_rows, columns=fieldnames)

    valid_df.to_csv(valid_report_path, index=False, encoding='utf8')
    non_valid_df.to_csv(non_valid_report_path, index=False, encoding='utf8')




def execute(orgunits: list | None):

    if orgunits is None:
        orgunits = get_organisation_units_based_on_level()

    for index, orgunit in enumerate(orgunits):
        print(f"Doing for organisation unit {orgunit['name']} ({index + 1}/{len(orgunits)})")
    
        processed_beneficiary_te_ids = set()
        processed_matrix_te_ids = set()

        beneficiary_data = load_data(orgunit=orgunit, program=BENEFICIARY_PROGRAM)

        if not beneficiary_data:
            continue

        beneficiary_data = add_hash_values(beneficiary_data, BENEFICIARY_PROGRAM['type'])
        grouped_nid_teis, grouped_family_id_teis = group_data(beneficiary_data)
        
        matrix_data = load_data(orgunit=orgunit, program=MATRIX_PROGRAM)
        matrix_data = add_hash_values(matrix_data, MATRIX_PROGRAM['type'])

        valid_nid_matchs, non_valid_nid_matchs, processed_events = nid_evaluation(matrix_data, grouped_nid_teis)

        remaining_matrix_data = [event for event in matrix_data if event['event'] not in processed_events]
        valid_family_id_matchs, non_valid_family_id_matchs, family_processed_events = family_id_evaluation(remaining_matrix_data, grouped_family_id_teis)
        processed_events.update(family_processed_events)

        #extracting processed TE ids from the above valid matches
        processed_beneficiary_te_ids.update(te['trackedEntity'] for match in valid_nid_matchs for te in match['beneficiaries'])
        processed_beneficiary_te_ids.update(te['trackedEntity'] for match in valid_family_id_matchs for te in match['beneficiaries'])

        remaining_matrix_data = [event for event in matrix_data if event['event'] not in processed_events]
        valid_demographic_matchs, non_valid_demographic_matchs, demographic_processed_events = demographic_evaluation(remaining_matrix_data, beneficiary_data, processed_beneficiary_te_ids)
        processed_events.update(demographic_processed_events)

        all_valid_matchs, all_non_valid_matchs = process_evaluation_results(
            valid_nid_matchs,
            non_valid_nid_matchs,
            valid_family_id_matchs,
            non_valid_family_id_matchs,
            valid_demographic_matchs,
            non_valid_demographic_matchs,
        )

        generate_report(orgunit, all_valid_matchs, all_non_valid_matchs)




if __name__ == "__main__":
    print("This module is not meant to be run directly.")