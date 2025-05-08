# custom_components.py
from pymongo.database import Database
import streamlit as st
import utils as u

def display_basic_patient_info(db: Database, pat_id: str):
    st.subheader("Basic Patient Information")
    patient = u.load_patient(db, pat_id)
    name = patient['name'][0]
    st.write(f"**Name:** {name['family']}, {name['given'][0]}")
    st.write(f"**DOB:** {patient['birthDate']}")
    st.write(f"**Gender:** {patient['gender']}")

# custom_components.py

from pymongo.database import Database
import streamlit as st
import utils as u

def display_allergies(db: Database, pat_id: str):
    allergies = u.load_collection_data(db, pat_id, "AllergyIntolerance")
    st.subheader("Allergy Alerts")
    if not allergies:
        st.info("No allergy alerts found.")
        return

    for a in allergies:
        # pull out the common fields, with safe defaults
        substance = a.get("code", {}).get("text", "Unknown")
        status    = a.get("clinicalStatus", {}).get("coding", [{}])[0].get("display", "Unknown")
        onset     = a.get("onsetDateTime", "N/A")
        note      = (a.get("note") or [{}])[0].get("text", "")

        with st.expander(f"🛑 {substance}"):
            cols = st.columns([2, 1, 1])
            cols[0].markdown(f"**Substance:** {substance}")
            cols[1].markdown(f"**Status:** {status}")
            cols[2].markdown(f"**Onset:** {onset[:10]}")
            if note:
                st.markdown(f"> _Note_: {note}")

def display_medications(db: Database, pat_id: str):
    meds = u.load_collection_data(db, pat_id, "MedicationRequest")
    st.subheader("Current Medications")

    # Only keep active meds
    active_meds = [
        m for m in meds
        if m.get("status", "").lower() == "active"
    ]

    if not active_meds:
        st.info("No active medications.")
        return

    for m in active_meds:
        med_text = m.get("medicationCodeableConcept", {}) \
                    .get("text", "Unknown medication")
        date     = m.get("authoredOn", "")[:10] or "N/A"
        prescriber = m.get("requester", {}).get("display", "N/A")
        reason     = (m.get("reasonReference") or [{}])[0].get("display", "")
        dosage     = ""
        di = m.get("dosageInstruction")
        if di:
            dosage = di[0].get("text", "")

        with st.expander(f"💊 {med_text}"):
            cols = st.columns(2)
            cols[0].markdown(f"**Prescribed on:** {date}")
            cols[1].markdown(f"**Prescriber:** {prescriber}")
            if dosage:
                st.markdown(f"**Dosage:** {dosage}")

def display_vitals(db: Database, pat_id: str):
    # Map LOINC → label
    VITAL_LOINC = {
        "8867-4":   "Heart rate",
        "9279-1":   "Respiratory rate",
        "8480-6":   "Systolic BP",
        "8462-4":   "Diastolic BP",
        "8310-5":   "Temperature",
        "59408-5":  "SpO₂",
        "29463-7":  "Body weight",
        "8302-2":   "Body height",
        "39156-5":  "BMI",
        "8478-0":   "Mean arterial pressure",
        "2339-0":   "Blood glucose",
        # Optional / patient-reported
        "56842-1":  "Pain severity",
        "89226-8":  "Capillary refill time",
    }
    st.subheader("Vital Signs")
    obs = u.load_collection_data(db, pat_id, "Observation")

    # build a dict: code → list of (datetime, value, unit)
    vitals: dict[str, list[tuple[str, float, str]]] = {}
    for o in obs:
        for c in o.get("code", {}).get("coding", []):
            code = c.get("code")
            if code in VITAL_LOINC and "valueQuantity" in o:
                qty = o["valueQuantity"]
                dt  = o["effectiveDateTime"]
                vitals.setdefault(code, []).append(
                    (dt, qty["value"], qty.get("unit",""))
                )

    if not vitals:
        st.info("No vital sign observations.")
        return

    # lay them out in a 3-column grid with units
    cols = st.columns(3)
    for i, (code, entries) in enumerate(vitals.items()):
        col = cols[i % 3]
        # pick the most recent
        _, val, unit = sorted(entries, key=lambda x: x[0])[-1]
        col.metric(
            label = f"{VITAL_LOINC[code]}",
            value = f"{val} {unit}"
        )
