from pymongo.database import Database
from pymongo import MongoClient

API_KEY='16c1715f-8328-4b16-8a4b-f977e35458d2'

def connect():
    client = MongoClient()
    return client, client['ehr_db']


def load_patient_ids(db:Database):
    return [pat['id'] for pat in db['Patient'].find()]


def load_patient(db:Database, pat_id:str) -> dict:
    return db['Patient'].find_one({"id": pat_id})


def load_patient_extensions(db:Database, pat_id:str):
    return load_patient(db, pat_id).get('extension', [])


PatientIdQueryConfig = {
    'AllergyIntolerance': 'patient.reference',
    'Condition': 'subject.reference',
    'Device': 'patient.reference',
    'DiagnosticReport': 'subject.reference',
    'DocumentReference': 'subject.reference',
    'Encounter': 'subject.reference',
    'Immunization': 'subject.reference',
    'MedicationRequest': 'subject.reference',
    'Observation': 'subject.reference',
    'Procedure': 'subject.reference',
}


def load_collection_data(db:Database, pat_id:str, collection:str):
    query = {PatientIdQueryConfig[collection]: f'Patient/{pat_id}'}
    result = db[collection].find(query)
    return list(result) if result is not None else []


def collection_has_pat(db:Database, pat_id:str, collection:str):
    if collection == 'Patient': 
        return load_patient(db, pat_id) is not None
    query = {PatientIdQueryConfig[collection]: f'Patient/{pat_id}'}
    return db[collection].find_one(query) is not None


def generate_umls_relations_get_url(src_id:str, source:str='SNOMEDCT_US'):
    assert API_KEY is not None
    return (
        'https://uts-ws.nlm.nih.gov/rest/content/current/source/'
        f'{source}/{src_id}/relations?apiKey={API_KEY}'
    )


def generate_rxnorm_get_all_properties(rxcui:str):
    return f'https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/allProperties.json?prop=names+codes'
