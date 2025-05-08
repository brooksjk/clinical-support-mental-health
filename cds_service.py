import requests
from flask import Flask, request, jsonify, render_template
import utils as u

app = Flask(__name__)

# single DB connection
client, db = u.connect()


@app.route('/')
def patient_details_view():
    pat_id = request.args.get('patient_id')
    if not pat_id:
        return render_template('no_patient.html'), 400

    # load patient demographics/info
    pat_data = u.load_patient(db, pat_id)
    collections = u.PatientIdQueryConfig.keys()
    pat_collections = [c for c in collections if u.collection_has_pat(db, pat_id, c)]
    empty_collections = [c for c in collections if c not in pat_collections]

    # PHQ-9 evaluation records
    phq9_records = list(db["PHQ9"].find({"patientId": pat_id}))

    return render_template(
        'patient_details.html',
        pat_id=pat_id,
        pat_data=pat_data,
        pat_collections=pat_collections,
        empty_collections=empty_collections,
        phq9_records=phq9_records
    )


@app.route('/cds-services', methods=['GET'])
def get_cds_services():
    services = [
        {
            'hook': 'patient-details-view',
            'title': 'Mental Health Alert Service',
            'description': 'A CDS service that flags multiple mental health conditions.',
            'id': 'mental-health-alert',
            'prefetch': {'patient': 'Patient/{{context.patientId}}'},
        }
    ]
    return jsonify(services)


@app.route('/cds-hooks', methods=['POST'])
def get_cds_hooks():
    data = request.json
    hook = data.get('hook')
    patient_id = data['context'].get('patientId')

    if hook != 'patient-details-view':
        return jsonify({"error": f'hook not supported: {hook}'}), 404

    # fetch conditions
    conditions = list(db['Condition'].find({'subject.reference': f'Patient/{patient_id}'}))

    # SNOMED codes for mental health (expanded map)
    mental_code_map = {
        '35489007': 'Depressive disorder',
        '310495003': 'Mild Depression',
        '370143000': 'Major Depressive Disorder',
        '310497006': 'Severe Depression',
        '21897009': 'Generalized anxiety disorder',
        '197480006': 'Anxiety disorder',
        '231504006': 'Mixed Anxiety/Depression Disorder',
        '70997004': 'Mild Anxiety',
        '13746004': 'Bipolar disorder',
        '6471006': 'Suicidal ideation',
        '66214007': 'Substance abuse',
        '371631005': 'Panic disorder',
        '386810004': 'Phobic disorder',
        '25501002': 'Social phobia',
        '47505003': 'Posttraumatic stress disorder',
        '17226007': 'Adjustment disorder',
        '73595000': 'Stress (finding)',
        '20010003': 'Borderline personality disorder',
        '191736004': 'Obsessive-compulsive disorder',
        '58214004': 'Schizophrenia',
        '409911007': 'Schizoaffective disorder',
        '414285001': 'Psychotic disorder',
        '11965000': 'Manic episode',
        '192127007': 'Attention deficit hyperactivity disorder',
        '22557007': 'Eating disorder',
        '165086002': 'Anorexia nervosa',
        '25084005': 'Bulimia nervosa',
        '165869001': 'Alcohol use disorder',
        '193462001': 'Insomnia disorder',
        '724748004': 'Chronic Insomnia',
        '422650009': 'Social isolation',
        '8950005': 'Social withdrawal',
        '443883004': 'Self-harm behavior',
        '423315002': 'Limited Social Contact'
    }

    # keywords fallback
    mental_keywords = [
        'depression', 'bipolar',  
        'anxiety', 'panic', 'phobia', 'social anxiety',  
        'ptsd', 'adjustment disorder', 'stress',
        'bpd', 'ocd',  
        'schizophrenia', 'schizoaffective', 'psychosis', 'manic', 
        'adhd',  
        'eating disorder', 'anorexia', 'bulimia',  
        'substance use', 'addiction', 'alcohol use',  
        'insomnia', 'social isolation', 'limited social contact'
    ]

    detected = {}
    for cond in conditions:
        codings = cond.get('code', {}).get('coding', [])
        text_val = cond.get('code', {}).get('text', '').lower()
        for coding in codings:
            code = coding.get('code', '').upper()
            display = coding.get('display', '').strip()
            if code in mental_code_map:
                detected[code] = mental_code_map[code]
            elif any(kw in display.lower() or kw in text_val for kw in mental_keywords):
                detected[code] = display or text_val
    
    detected.pop('271825005', None)

    # Check for any past moderate+ scores
    phq9_flag = db["PHQ9"].find_one({
        "patientId": patient_id,
        "total_score": {"$gte": 10}
    })
    gad7_flag = db["GAD7"].find_one({
        "patientId": patient_id,
        "total_score": {"$gte": 10}
    })

    # Build the HTML content per branch
    if detected:
        # Build one <li> per detected SNOMED code
        items = [
            f"<li>🔍 {label} <code>({code})</code></li>"
            for code, label in detected.items()
        ]
        content_html = f"""
        <p style="
            padding-left: 20px;
            margin-bottom: 8px;
        ">
            Patient has active mental-health condition(s) or symptoms concerning mental well-being:
        </p>
        <ul style="
            list-style-type: disc;
            margin-left: 40px;
            padding-left: 0;
            margin-bottom: 16px;
            line-height: 1.5;
        ">
            {''.join(items)}
        </ul>
        <p style="
            padding-left: 20px;
            margin-top: 0;
        ">
            Please conduct a screening.
        </p>
        """

    elif phq9_flag or gad7_flag:
        # Single-item list for past elevated score
        content_html = """
        <ul style="
            list-style-type: disc;
            padding-left: 20px;
            margin-bottom: 16px;
            line-height: 1.5;
        ">Past PHQ-9/GAD-7 total score ≥ 10. Consider re-screening.
        </ul>
        """

    else:
        # No concerns
        content_html = """
        <p style="margin-bottom: 16px;">
            ✅ No past elevated scores or active conditions detected. 
            
            Evaluations can be conducted at you discretion.
        </p>
        """

    html_detail = f"""
    <div style="
        border: 2px solid #f5a731;
        border-radius: 8px;
        padding: 16px;
        background-color: #fff8e1;
    ">
      {content_html}
      <a href="http://localhost:8501/?patient_id={patient_id}" 
          target="_blank"
          rel="noopener noreferrer"
          style="
          display: inline-block;
          padding: 14px 28px;
          background-color: #ecdd76;
          color: #333333;
          text-decoration: none;
          font-weight: bold;
          border-radius: 4px;
          font-size: 16px;
      ">
        ▶ Take PHQ-9 / GAD-7
      </a>
    </div>
    """

    cards = [{
        "summary": "⚠️ Mental Health Concern" if (detected or phq9_flag or gad7_flag)
                   else "ℹ️ Mental Health Status",
        "indicator": "warning" if (detected or phq9_flag or gad7_flag)
                     else "info",
        "detail": html_detail,
        "source": {"label": "Mental Health CDS"},
    }]

    return jsonify({"cards": cards})


if __name__ == "__main__":
    print("🚀 Starting CDS Hook Service on http://localhost:5000")
    app.run(port=5000, debug=True)
