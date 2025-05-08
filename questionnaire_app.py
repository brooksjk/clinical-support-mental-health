# questionnaire_app.py

import uuid
import datetime
import streamlit as st
import custom_components as cc
import utils as u
import pandas as pd
from bson import ObjectId

# Connect to MongoDB
client, db = u.connect()

# --- Read patient_id from URL query params ---
params = st.experimental_get_query_params()
pat_id = params.get("patient_id", [""])[0]

st.title("Patient Questionnaires")

if not pat_id:
    st.warning("No patient specified. Use ?patient_id=<ID> in the URL")
    st.stop()

# --- Display basic demographics ---
cc.display_basic_patient_info(db, pat_id)

st.markdown("---")

# ─── Form Selector ──────────────────────────────────────────────────────────
if "current_form" not in st.session_state:
    st.session_state.current_form = "PHQ-9"

col1, col2 = st.columns(2)
if col1.button("📝 PHQ-9"):
    st.session_state.current_form = "PHQ-9"
if col2.button("📝 GAD-7"):
    st.session_state.current_form = "GAD-7"

st.markdown(f"## {st.session_state.current_form} Screening")
st.markdown("---")

# ─── PHQ-9 Form & History ──────────────────────────────────────────────────
if st.session_state.current_form == "PHQ-9":
    with st.form("phq9_form"):
        phq9_questions = [
            "Little interest or pleasure in doing things?",
            "Feeling down, depressed, or hopeless?",
            "Trouble falling or staying asleep, or sleeping too much?",
            "Feeling tired or having little energy?",
            "Poor appetite or overeating?",
            "Feeling bad about yourself — or that you are a failure or have let yourself or your family down?",
            "Trouble concentrating on things, such as reading or watching television?",
            "Moving or speaking so slowly that other people could have noticed? Or the opposite — being fidgety or restless?",
            "Thoughts that you would be better off dead or of hurting yourself in some way?"
        ]
        phq9_responses = [
            st.selectbox(q, [0, 1, 2, 3], key=f"phq9_{i}")
            for i, q in enumerate(phq9_questions)
        ]
        if st.form_submit_button("Submit PHQ-9"):
            total_phq = sum(phq9_responses)
            if total_phq <= 4:
                level = "Minimal"
            elif total_phq <= 9:
                level = "Mild"
            elif total_phq <= 14:
                level = "Moderate"
            elif total_phq <= 19:
                level = "Moderately Severe"
            else:
                level = "Severe"

            db["PHQ9"].insert_one({
                "patientId": pat_id,
                "date": str(datetime.datetime.now().date()),
                "responses": phq9_responses,
                "total_score": total_phq,
                "depression_level": level
            })
            st.success(f"PHQ-9 submitted: {total_phq} ({level})")

    st.header("PHQ-9 History")

    # 1) Fetch & sort descending by date
    phq9_records = list(db["PHQ9"].find({"patientId": pat_id}))
    phq9_records.sort(
        key=lambda r: datetime.datetime.strptime(r["date"], "%Y-%m-%d"),
        reverse=True
    )

    # 2) Render
    if phq9_records:
        with st.expander("View Past PHQ-9 Evaluations"):
            for r in phq9_records:
                st.write(
                    f"**Date:** {r['date']}  |  "
                    f"**Score:** {r['total_score']} ({r['depression_level']})"
                )
    else:
        st.info("No PHQ-9 evaluations found for this patient.")

# ─── GAD-7 Form & History ──────────────────────────────────────────────────
else:  # GAD-7
    with st.form("gad7_form"):
        gad7_questions = [
            "Feeling nervous, anxious or on edge?",
            "Not being able to stop or control worrying?",
            "Worrying too much about different things?",
            "Trouble relaxing?",
            "Being so restless that it's hard to sit still?",
            "Becoming easily annoyed or irritable?",
            "Feeling afraid as if something awful might happen?"
        ]
        gad7_responses = [
            st.selectbox(q, [0, 1, 2, 3], key=f"gad7_{i}")
            for i, q in enumerate(gad7_questions)
        ]
        if st.form_submit_button("Submit GAD-7"):
            total_gad = sum(gad7_responses)
            if total_gad <= 4:
                glevel = "Minimal"
            elif total_gad <= 9:
                glevel = "Mild"
            elif total_gad <= 14:
                glevel = "Moderate"
            else:
                glevel = "Severe"

            db["GAD7"].insert_one({
                "patientId": pat_id,
                "date": str(datetime.datetime.now().date()),
                "responses": gad7_responses,
                "total_score": total_gad,
                "anxiety_level": glevel
            })
            st.success(f"GAD-7 submitted: {total_gad} ({glevel})")

    st.header("GAD-7 History")

    # 1) Fetch & sort descending by date
    gad7_records = list(db["GAD7"].find({"patientId": pat_id}))
    gad7_records.sort(
        key=lambda r: datetime.datetime.strptime(r["date"], "%Y-%m-%d"),
        reverse=True
    )

    # 2) Render
    if gad7_records:
        with st.expander("View Past GAD-7 Evaluations"):
            for r in gad7_records:
                st.write(
                    f"**Date:** {r['date']}  |  "
                    f"**Score:** {r['total_score']} ({r['anxiety_level']})"
                )
    else:
        st.info("No GAD-7 evaluations found for this patient.")

    st.markdown("---")

# ─── Insert Past Evaluation ─────────────────────────────────────────────────
st.markdown("---")
st.subheader("Insert Past Evaluation")
with st.expander("➕ Add Old PHQ-9 / GAD-7 Score"):
    ev_type  = st.selectbox("Questionnaire Type", ["PHQ-9", "GAD-7"], key="insert_type")
    ev_date  = st.date_input(
        "Date of Evaluation",
        value=datetime.date.today(),
        max_value=datetime.date.today(),
        key="insert_date"
    )
    ev_score = st.number_input(
        "Total Score",
        min_value=0,
        max_value=27 if ev_type=="PHQ-9" else 21,
        step=1,
        key="insert_score"
    )
    if st.button("Save Past Evaluation", key="insert_submit"):
        if ev_date > datetime.date.today():
            st.error("Date cannot be in the future.")
        else:
            # derive level
            if ev_type == "PHQ-9":
                if   ev_score <= 4:  level = "Minimal"
                elif ev_score <= 9:  level = "Mild"
                elif ev_score <=14:  level = "Moderate"
                elif ev_score <=19:  level = "Mod. Severe"
                else:                level = "Severe"
                coll = "PHQ9"
                lvl_field = "depression_level"
            else:
                if   ev_score <= 4:  level = "Minimal"
                elif ev_score <= 9:  level = "Mild"
                elif ev_score <=14:  level = "Moderate"
                else:                level = "Severe"
                coll = "GAD7"
                lvl_field = "anxiety_level"

            db[coll].insert_one({
                "patientId":      pat_id,
                "date":           ev_date.strftime("%Y-%m-%d"),
                "responses":      [],
                "total_score":    ev_score,
                lvl_field:        level
            })
            st.success(f"{ev_type} on {ev_date} saved: {ev_score} ({level})")

st.markdown("---")
st.subheader("Evaluation Scores Over Time")

# 1) Fetch raw records
records = []
for coll_name, label in [("PHQ9","PHQ-9"), ("GAD7","GAD-7")]:
    for r in db[coll_name].find(
        {"patientId": pat_id},
        {"date":1, "total_score":1}
    ):
        records.append({
            "date":  r["date"],
            "type":  label,
            "score": r["total_score"]
        })

df = pd.DataFrame(records)

if not df.empty:
    # 2) Convert dates & index
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    
    # 3) Filter to last 3 years
    cutoff = pd.Timestamp.now() - pd.DateOffset(years=3)
    df = df.loc[df.index >= cutoff]
    
    if df.empty:
        st.info("No scores in the past 3 years to plot.")
    else:
        # 4) Pivot with aggregation to collapse duplicates  
        chart_df = df.pivot_table(
            index=df.index,      # uses your DateTimeIndex
            columns="type",
            values="score",
            aggfunc="mean"       # or 'max' / 'first'
        )
        
        st.line_chart(chart_df)
else:
    st.info("No scores to plot yet.")

# ─── Manage Past Evaluations (Collapsible) ─────────────────────────────────
st.markdown("---")
import datetime
import pandas as pd
from bson import ObjectId

with st.expander("Manage Past Evaluations"):
    # 1) Fetch fresh list of records
    records = []
    for coll_name, label in [("PHQ9","PHQ-9"), ("GAD7","GAD-7")]:
        for r in db[coll_name].find(
            {"patientId": pat_id},
            {"_id":1, "date":1, "total_score":1}
        ):
            records.append({
                "id":     r["_id"],
                "date":   r["date"],
                "type":   label,
                "score":  r["total_score"],
                "coll":   coll_name
            })

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.drop_duplicates(subset=["date","type","score"])
        df["date"] = pd.to_datetime(df["date"])
    else:
        st.info("No past evaluations to manage.")
        st.stop()

    # 2) Delete callback
    def delete_eval(record_id, coll_name):
        db[coll_name].delete_one({"_id": ObjectId(record_id)})
        st.success("Deleted!")

    # 3) Render table with Delete buttons
    for _, row in df.sort_values("date", ascending=False).iterrows():
        cols = st.columns([2,1,1,1])
        cols[0].write(row["date"].date())
        cols[1].write(row["type"])
        cols[2].write(row["score"])
        cols[3].button(
            "Delete",
            key=f"del_{row['id']}",
            on_click=delete_eval,
            args=(str(row["id"]), row["coll"])
        )

#app run request is not really needed
#streamlit run questionnaire_app.py --server.port 8501
