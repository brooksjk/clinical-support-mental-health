import uuid
import requests
import streamlit as st
import streamlit.components.v1 as components
import custom_components as cc
import utils as u

# single DB connection
client, db = u.connect()
CDS_URL = "http://127.0.0.1:5000/cds-hooks"
HEADERS = {"Content-Type": "application/json"}

st.title("Patient Dashboard")

# Select any patient
patient_ids = u.load_patient_ids(db)
pat_id = st.selectbox("Select Patient ID", patient_ids)
if not pat_id:
    st.warning("Pick a patient to begin.")
    st.stop()

# 1. Basic info
cc.display_basic_patient_info(db, pat_id)

st.markdown("---")
# 2. Allergies, Meds, Vitals
cc.display_allergies(db, pat_id)
cc.display_medications(db, pat_id)
cc.display_vitals(db, pat_id)

st.markdown("---")
# 3. Mental‐health alert via CDS hook
st.subheader("Mental Health Alert")
payload = {
    "hook": "patient-details-view",
    "context": {"patientId": pat_id},
    "hookInstance": str(uuid.uuid4())
}
resp = requests.post(CDS_URL, json=payload, headers=HEADERS)

if resp.ok:
    for card in resp.json().get("cards", []):
        # render each card’s HTML with full HTML support
        components.html(card["detail"], height=300)
else:
    st.error("CDS service error")
