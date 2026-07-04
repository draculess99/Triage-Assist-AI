# Triage Assist AI

This project is a two-tier application built with **Streamlit** (frontend) and **Flask** (backend), demonstrating a multi-agent decision support system. It utilizes an **XGBoost** model to forecast patient priority based on synthetic vitals data.

## Features
- **Two Decision Engines:** Switch seamlessly between a 0-token Expert System and an LLM-based system.
- **XGBoost Forecaster:** A dummy regression model that predicts patient priority (0-10) using age, heart rate, and pain level.
- **State Memory:** Chat state is persisted using a LangGraph-style JSON memory store.
- **Transaction Logging:** All user interactions and decisions are logged for auditing.
- **Real-Time Token Usage:** Monitors the token expenditure (shows 0 when the Expert System is active).
- **Model Metrics Tab:** View the training metrics ($R^2$, MAE, RMSE) of the XGBoost forecaster directly from the UI.

## Getting Started

### 1. Prerequisites
Ensure you have Python 3.9+ installed. We recommend running this in a virtual environment.

Install the required dependencies by running:
```bash
pip install -r requirements.txt
```

If you are using the LLM functionality, ensure you have set your API key as an environment variable before starting the Flask server:
```bash
# On Windows
set GEMINI_API_KEY=your_api_key_here
```

### 2. Start the Application
Open a terminal window and run:
```powershell
cd d:\Work\Springboard\ANTIGRAVITY-SCRATCH\triage
python app.py
```
*This command will automatically launch the Flask API and Streamlit UI in separate windows, wait a few seconds for initialization, and then open the application in your browser.*

### 3. Use the Application
Once the browser opens to `http://localhost:8501`: 
- Chat with the triage assistant using the chat input.
- Toggle between the **Expert System** and **LLM System** in the sidebar.
- Adjust mock vitals in the sidebar to see how it affects the XGBoost forecaster's priority score.
- View transaction logs and system memory on the right side.
- Click on the **Model Metrics** tab to see the performance of the synthetic data model.
"# Triage-Assist-AI" 
