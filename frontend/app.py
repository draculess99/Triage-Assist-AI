import streamlit as st
import requests

API_URL = "http://localhost:5000/api"

st.set_page_config(page_title="Triage Assist AI", layout="wide")

st.title("🏥 Triage Assist AI - Clinical Dashboard")
st.markdown("---")

# Control Center Sidebar
with st.sidebar:
    st.header("⚙️ Control Center")
    engine_type = st.radio("Decision Engine", [
        "Local Expert System (0 Tokens)",
        "Google LLM (Gemini)",
        "Groq"
    ])
    
    if engine_type == "Local Expert System (0 Tokens)":
        st.info("Using **Expert System (Rule-based)**")
        selected_llm = "None"
    elif engine_type == "Google LLM (Gemini)":
        st.warning("Using **Google LLM System**")
        selected_llm = st.selectbox("LLM Model for Assessment", [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash"
        ])
    else:
        st.success("Using **Groq (Fast Inference)**")
        selected_llm = st.selectbox("LLM Model for Assessment", [
            "llama-3.3-70b-versatile",
            "mixtral-8x7b-32768"
        ])
        
    st.markdown("---")
    st.subheader("Machine Learning")
    selected_model = st.selectbox("ML Model for Prediction", ["XGBoost", "Random Forest", "Logistic Regression"])
    st.caption("This model generates the underlying Priority Score based on the UCI Heart Disease dataset.")

    st.markdown("---")
    st.subheader("Data Management")
    dataset_options = [
        "UCI Cleveland Original", 
        "Synthetic Global Cohort (10,000 Patients)",
        "High-Risk Elderly Cohort (2,000 Patients)",
        "Global General Population (50,000 Patients)"
    ]
    
    current_dataset = dataset_options[0]
    try:
        metrics_resp = requests.get(f"{API_URL}/metrics")
        if metrics_resp.status_code == 200:
            current_dataset = metrics_resp.json().get("dataset", dataset_options[0])
    except:
        pass
        
    idx = dataset_options.index(current_dataset) if current_dataset in dataset_options else 0
    selected_dataset = st.selectbox("Dataset Source", dataset_options, index=idx)
    
    if selected_dataset != current_dataset:
        with st.spinner(f"Swapping to {selected_dataset} and retraining all models..."):
            requests.post(f"{API_URL}/train", json={"dataset_name": selected_dataset})
        st.rerun()

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 Patient Evaluation", "📈 Model Metrics", "🗣️ AI Committee Debate", "🗄️ Data Sources", "🧠 Explainable AI"])

with tab1:
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.subheader("System Dashboard")
        
        try:
            logs_resp = requests.get(f"{API_URL}/logs")
            if logs_resp.status_code == 200:
                logs = logs_resp.json()
                total_tokens = sum(
                    log.get('details', {}).get('tokens_used', 0) 
                    for log in logs 
                    if log.get('details', {}).get('engine') == engine_type
                )
            else:
                total_tokens = 0
                logs = []
        except:
            total_tokens = 0
            logs = []
            
        st.metric(label="Total Tokens Used", value=total_tokens)
        
        with st.expander("Transaction Logs"):
            if logs:
                for log in reversed(logs[-10:]):
                    st.text(f"[{log['timestamp']}]")
                    st.text(f"Engine: {log['details'].get('engine')}")
                    st.text(f"Model: {log['details'].get('ml_model')}")
                    st.text(f"Tokens: {log['details'].get('tokens_used')}")
                    st.markdown("---")
            else:
                st.text("No transactions yet.")
                
        with st.expander("System Memory (JSON)"):
            try:
                mem_resp = requests.get(f"{API_URL}/memory")
                if mem_resp.status_code == 200:
                    st.json(mem_resp.json())
            except:
                st.text("Could not load memory.")
                
        st.markdown("---")
        st.subheader("Agent Execution Pipeline")
        pipeline_placeholder = st.empty()
        pipeline_placeholder.markdown("<h5>⚫ Analyst ➔ ⚫ Reviewer ➔ ⚫ Editor</h5>", unsafe_allow_html=True)
        
    with col1:
        st.subheader("Patient Vitals & Features")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            age = st.number_input("Age", min_value=1, max_value=120, value=50)
            sex_input = st.selectbox("Sex", ["Male", "Female"])
            sex = 1 if sex_input == "Male" else 0
        with c2:
            trestbps = st.number_input("Resting BP (mm Hg)", min_value=50, max_value=250, value=120)
            chol = st.number_input("Cholesterol (mg/dl)", min_value=100, max_value=600, value=200)
        with c3:
            thalach = st.number_input("Max Heart Rate", min_value=50, max_value=250, value=150)
            fbs_input = st.selectbox("Fasting Blood Sugar > 120", ["No", "Yes"])
            fbs = 1 if fbs_input == "Yes" else 0
            
        cp_input = st.selectbox("Chest Pain Type", [
            "1: Typical Angina", 
            "2: Atypical Angina", 
            "3: Non-anginal Pain", 
            "4: Asymptomatic"
        ])
        cp = int(cp_input[0])
        
        notes = st.text_area("Clinical Notes (Optional)", height=100, placeholder="Enter any additional unstructured observations here...")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button(f"Evaluate Patient using {selected_model}", type="primary", use_container_width=True):
            vitals = {
                "age": age, "sex": sex, "cp": cp, "trestbps": trestbps,
                "chol": chol, "fbs": fbs, "thalach": thalach
            }
            
            final_data = None
            
            try:
                response = requests.post(f"{API_URL}/evaluate", json={
                    "session_id": "demo_session",
                    "notes": notes,
                    "engine_type": engine_type,
                    "vitals": vitals,
                    "model_name": selected_model,
                    "llm_model_name": selected_llm,
                    "dataset_name": selected_dataset
                }, stream=True)
                
                if response.status_code == 200:
                    import json
                    final_data = {}
                    for line in response.iter_lines():
                        if line:
                            data = json.loads(line.decode('utf-8'))
                            if 'step' in data:
                                step_text = data['step']
                                if "Analyst" in step_text or "deterministic" in step_text:
                                    pipeline_placeholder.markdown("<h5>🟢 Analyst ➔ ⚫ Reviewer ➔ ⚫ Editor</h5>", unsafe_allow_html=True)
                                elif "Reviewer" in step_text:
                                    pipeline_placeholder.markdown("<h5>🟢 Analyst ➔ 🟢 Reviewer ➔ ⚫ Editor</h5>", unsafe_allow_html=True)
                                elif "Editor" in step_text:
                                    pipeline_placeholder.markdown("<h5>🟢 Analyst ➔ 🟢 Reviewer ➔ 🟢 Editor</h5>", unsafe_allow_html=True)
                            elif 'error' in data:
                                st.error(data['error'])
                                pipeline_placeholder.markdown("<h5>🔴 Error in Pipeline</h5>", unsafe_allow_html=True)
                                break
                            elif 'done' in data:
                                pipeline_placeholder.markdown("<h5>🟢 Analyst ➔ 🟢 Reviewer ➔ 🟢 Editor</h5>", unsafe_allow_html=True)
                                final_data = data
                                break
                                
                    if final_data:
                        st.success("Evaluation Complete!")
                        st.session_state['analyst_draft'] = final_data.get('analyst_draft')
                        st.session_state['reviewer_critique'] = final_data.get('reviewer_critique')
                else:
                    st.error("Error communicating with backend.")
                    pipeline_placeholder.markdown("<h5>🔴 Backend Error</h5>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Could not reach backend: {e}")
                pipeline_placeholder.markdown("<h5>🔴 Connection Error</h5>", unsafe_allow_html=True)
            
            if final_data:
                st.markdown("### Assessment Report")
                st.info(final_data.get("report", ""))

with tab2:
    st.header("Model Performance Comparison")
    
    st.markdown("""
    ### Evaluation Methodology
    - **Dataset:** UCI Heart Disease Dataset (Processed Cleveland Data).
    - **Data Split:** The dataset is split into an **80% Training Set** and a **20% Test (Holdout) Set**.
    - **Training:** The models (XGBoost, Random Forest, Logistic Regression) are trained exclusively on the 80% Training Set.
    - **Evaluation:** To determine each model's ability to learn and generalize, we ask them to predict the outcomes of the unseen 20% Test Set. The table below shows the performance of those predictions across four standard metrics: Accuracy, Precision, Recall, and F1 Score.
    """)
    
    try:
        metrics_resp = requests.get(f"{API_URL}/metrics")
        if metrics_resp.status_code == 200:
            resp_data = metrics_resp.json()
            metrics = resp_data.get("metrics", {})
            st.info(f"Models currently trained on: **{resp_data.get('dataset', 'Unknown')}**")
            if metrics:
                import pandas as pd
                df = pd.DataFrame.from_dict(metrics, orient='index')
                st.dataframe(df.style.format("{:.2%}"), use_container_width=True)
            else:
                st.info("Metrics not available yet. Model may need to be trained.")
    except Exception as e:
        st.error(f"Could not load metrics: {e}")

with tab3:
    st.header("🗣️ Internal AI Committee Debate")
    if 'analyst_draft' in st.session_state and st.session_state['analyst_draft']:
        st.markdown("### 1. The Analyst's Initial Draft")
        st.info(st.session_state['analyst_draft'])
        
        st.markdown("### 2. The Medical Reviewer's Critique")
        st.warning(st.session_state['reviewer_critique'])
        
        st.markdown("### 3. Chief Editor")
        st.success("The Chief Editor synthesized the above into the final Assessment Report found on the first tab.")
    else:
        st.text("Run a patient evaluation using an LLM to see the internal debate here.")

with tab4:
    st.header("🗄️ Data Sources")
    st.markdown("""
    ### 1. UCI Cleveland Original (300 Patients)
    - **Source:** [UCI Machine Learning Repository](https://archive.ics.uci.edu/ml/datasets/Heart+Disease)
    - **Description:** The classic Cleveland heart disease dataset. It contains 303 original patient records, with missing rows filtered out. It is the gold standard for introductory cardiac machine learning.
    
    ### 2. Synthetic Global Cohort (10,000 Patients)
    - **Source:** Dynamically generated locally via statistical modeling.
    - **Description:** This massive dataset is generated on the fly. It uses the statistical distributions (means and standard deviations) of the UCI dataset to construct 10,000 highly realistic synthetic patient records. This allows the system to demonstrate large-scale data ingestion and automated model retraining.

    ### 3. High-Risk Elderly Cohort (2,000 Patients)
    - **Source:** Dynamically generated via targeted statistical modeling.
    - **Description:** A simulated dataset representing an older demographic (average age 75) with inherently higher baseline blood pressure and cholesterol, leading to a significantly higher prevalence of heart disease in the training data.

    ### 4. Global General Population (50,000 Patients)
    - **Source:** Dynamically generated via broad statistical modeling.
    - **Description:** A massive simulated dataset representing a younger, healthier general population (average age 45), resulting in a lower baseline disease prevalence for the models to learn from.
    """)

with tab5:
    st.header("🧠 Explainable AI (XAI)")
    st.markdown("Understand *why* the models make their predictions and see how this patient compares to the dataset.")
    
    with st.spinner("Loading XAI data..."):
        try:
            xai_resp = requests.post(f"{API_URL}/xai", json={
                "model_name": selected_model,
                "dataset_name": selected_dataset
            })
            if xai_resp.status_code == 200:
                xai_data = xai_resp.json()
                
                st.subheader(f"1. Feature Importance ({selected_model})")
                st.markdown("This chart shows exactly which vitals the Machine Learning model is weighting most heavily.")
                importances = xai_data.get("importances", {})
                if importances:
                    import pandas as pd
                    df_imp = pd.DataFrame.from_dict(importances, orient='index', columns=['Importance'])
                    # Sort for better visual
                    df_imp = df_imp.sort_values(by='Importance', ascending=True)
                    st.bar_chart(df_imp, horizontal=True)
                else:
                    st.info("Feature importance not available for this model.")
                
                st.markdown("---")
                st.subheader("2. Patient vs. Population (Disease Means)")
                st.markdown("How does the current patient (left sidebar) compare to the average patient *who actually has heart disease* in this dataset?")
                
                means_disease = xai_data.get("means_disease", {})
                if means_disease:
                    c1, c2, c3, c4 = st.columns(4)
                    
                    # Age
                    avg_age = means_disease.get('age', 0)
                    delta_age = age - avg_age
                    c1.metric("Age", f"{age}", delta=f"{delta_age:.1f} vs Avg ({avg_age:.1f})", delta_color="inverse")
                    
                    # BP
                    avg_bp = means_disease.get('trestbps', 0)
                    delta_bp = trestbps - avg_bp
                    c2.metric("Resting BP", f"{trestbps}", delta=f"{delta_bp:.1f} vs Avg ({avg_bp:.1f})", delta_color="inverse")
                    
                    # Chol
                    avg_chol = means_disease.get('chol', 0)
                    delta_chol = chol - avg_chol
                    c3.metric("Cholesterol", f"{chol}", delta=f"{delta_chol:.1f} vs Avg ({avg_chol:.1f})", delta_color="inverse")
                    
                    # HR
                    avg_hr = means_disease.get('thalach', 0)
                    delta_hr = thalach - avg_hr
                    c4.metric("Max Heart Rate", f"{thalach}", delta=f"{delta_hr:.1f} vs Avg ({avg_hr:.1f})")
                    
                st.markdown("---")
                st.subheader("3. Dataset Correlation Matrix")
                st.markdown("This heatmap shows how different vitals are correlated across the entire dataset. A value of 1.0 means perfect correlation.")
                correlations = xai_data.get("correlations", {})
                if correlations:
                    import pandas as pd
                    df_corr = pd.DataFrame.from_dict(correlations)
                    # Anchor the color scale from -1 to 1 so 0 is perfectly neutral
                    st.dataframe(
                        df_corr.style.background_gradient(cmap='RdBu_r', axis=None, vmin=-1, vmax=1).format("{:.2f}"), 
                        use_container_width=True
                    )
                    
        except Exception as e:
            st.error(f"Could not load XAI data: {e}")

