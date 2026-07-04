import os
import sys
import json
from dotenv import load_dotenv
from google import genai
try:
    from groq import Groq
except ImportError:
    Groq = None

# Load .env file from the root 'triage' directory
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(root_dir, '.env'))

# Ensure backend modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from backend.memory import add_message, get_messages
from backend.logger import log_transaction
from backend.forecaster import get_disease_probability

def expert_system_decision(notes, vitals, model_name, dataset_name="UCI Cleveland Original"):
    prob = get_disease_probability(**vitals, model_name=model_name, dataset_name=dataset_name)
    priority_score = prob * 10
    
    decision = "Normal"
    if priority_score > 7:
        decision = "High Risk"
    elif priority_score > 4:
        decision = "Medium Risk"
        
    if vitals['trestbps'] > 180 or vitals['thalach'] > 200:
        decision = "Critical"
        priority_score = max(priority_score, 9.0)
        
    response = (
        "**Expert System Clinical Assessment:**\n\n"
        f"- Disease Probability ({model_name}): {prob:.1%}\n"
        f"- Computed Priority Score: {priority_score:.1f}/10\n"
        f"- Risk Level: **{decision}**\n\n"
        f"*Note: This decision was made using deterministic clinical rules and the {model_name} probability, without LLM synthesis.*"
    )
    return response, 0

def run_multi_agent_pipeline(vitals, notes, model_name, prob, priority_score, engine_type, llm_model_name, session_id):
    history = get_messages(session_id)
    historical_context = ""
    if history:
        historical_context = "\n\n--- HISTORICAL CONTEXT ---\nHere are the most recent patient evaluations you completed. Use this to ensure your new assessment is logically consistent with your past decisions.\n\n"
        recent_history = history[-4:] # Last two full interactions
        for msg in recent_history:
            role = "Previous Patient Data" if msg["role"] == "user" else "Your Past Decision"
            historical_context += f"[{role}]:\n{msg['content']}\n\n"
            
    system_prompt = "You are a medical AI decision support system." + historical_context
    analyst_prompt = (
        f"Analyze the following patient data.\n"
        f"Vitals: {vitals}\n"
        f"Clinical Notes: '{notes}'\n"
        f"{model_name} predicts {prob:.1%} probability of heart disease (Priority Score: {priority_score:.1f}/10).\n"
        "Draft a preliminary clinical assessment. State the Risk Level."
    )
    
    total_tokens = 0
    
    def call_llm(prompt, role_system_prompt):
        nonlocal total_tokens
        
        # Dynamically reload the .env file right before calling the API
        # so we don't have to restart the server when keys change
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        load_dotenv(os.path.join(root_dir, '.env'), override=True)
        
        if engine_type == "Google LLM (Gemini)":
            client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))
            response = client.models.generate_content(
                model=llm_model_name,
                contents=role_system_prompt + "\n\n" + prompt
            )
            text = response.text
            tokens = response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') and response.usage_metadata else len(prompt.split()) + len(text.split())
            total_tokens += tokens
            return text
        elif engine_type == "Groq":
            if Groq is None:
                raise ImportError("Groq library is not installed.")
            client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": role_system_prompt},
                    {"role": "user", "content": prompt}
                ],
                model=llm_model_name,
            )
            text = chat_completion.choices[0].message.content
            tokens = chat_completion.usage.total_tokens if chat_completion.usage else len(prompt.split()) + len(text.split())
            total_tokens += tokens
            return text
        else:
            raise ValueError(f"Unknown engine: {engine_type}")

    try:
        # 1. Analyst Drafts Assessment
        yield json.dumps({"step": "🔍 Analyst Agent is drafting preliminary assessment..."}) + "\n"
        analyst_draft = call_llm(analyst_prompt, system_prompt + " You are the Clinical Analyst. Draft a preliminary assessment.")
        
        # 2. Medical Reviewer Checks Draft
        yield json.dumps({"step": "⚕️ Medical Reviewer is cross-checking against safety protocols..."}) + "\n"
        reviewer_prompt = (
            f"Review the Analyst's draft:\n\n{analyst_draft}\n\n"
            "Check against strict medical guidelines (e.g. high BP > 180 or heart rate > 200 is critical). "
            "Ensure no specific medication dosages are recommended. Provide a critique, correct errors, and explicitly approve the final logic."
        )
        reviewer_critique = call_llm(reviewer_prompt, system_prompt + " You are the Medical Reviewer. Ensure safety, strict protocol adherence, and apply guardrails.")
        
        # 3. Chief Editor Formats Report
        yield json.dumps({"step": "📝 Chief Editor is formatting final SOAP Note..."}) + "\n"
        editor_prompt = (
            f"Analyst Draft:\n{analyst_draft}\n\n"
            f"Reviewer Critique & Guardrails:\n{reviewer_critique}\n\n"
            "Incorporate the critique and output a final, highly professional SOAP note (Subjective, Objective, Assessment, Plan). "
            "Ensure the risk level is explicitly stated at the top."
        )
        final_report = call_llm(editor_prompt, system_prompt + " You are the Chief Editor. Format the final output beautifully into a structured SOAP note.")
        
        yield json.dumps({"done": True, "report": final_report, "tokens": total_tokens, "analyst_draft": analyst_draft, "reviewer_critique": reviewer_critique}) + "\n"
    except Exception as e:
        yield json.dumps({"error": f"LLM Error during multi-agent pipeline: {str(e)}", "tokens": total_tokens}) + "\n"

def evaluate_patient(session_id, notes, engine_type, vitals, model_name, llm_model_name, dataset_name="UCI Cleveland Original"):
    prob = get_disease_probability(**vitals, model_name=model_name, dataset_name=dataset_name)
    priority_score = prob * 10
    
    if engine_type == "Local Expert System (0 Tokens)":
        yield json.dumps({"step": "⚙️ Applying deterministic clinical rules..."}) + "\n"
        response_text, tokens = expert_system_decision(notes, vitals, model_name, dataset_name)
        engine_used = "Expert System"
        
        add_message(session_id, "user", f"Evaluated patient with vitals: {vitals}. ML Model: {model_name}. Engine: {engine_type} ({llm_model_name}). Notes: {notes}")
        add_message(session_id, "assistant", response_text)
        log_transaction("patient_evaluation", {
            "session_id": session_id,
            "engine": engine_used,
            "ml_model": model_name,
            "llm_model": llm_model_name,
            "tokens_used": tokens,
            "vitals": vitals,
            "notes": notes,
            "response": response_text
        })
        yield json.dumps({"done": True, "report": response_text, "tokens": tokens, "engine": engine_used, "ml_model": model_name, "llm_model": llm_model_name}) + "\n"
    else:
        engine_used = engine_type
        provider = "Groq" if engine_type == "Groq" else "Google LLM"
        
        for chunk in run_multi_agent_pipeline(vitals, notes, model_name, prob, priority_score, engine_type, llm_model_name, session_id):
            data = json.loads(chunk)
            if "done" in data:
                raw_report = data["report"]
                total_tokens = data["tokens"]
                
                response_text = (
                    f"**Multi-Agent Committee Assessment ({provider} - {llm_model_name}):**\n\n"
                    f"- Disease Probability ({model_name}): {prob:.1%}\n"
                    f"- Computed Priority Score: {priority_score:.1f}/10\n\n"
                    f"---\n\n{raw_report}"
                )
                
                add_message(session_id, "user", f"Evaluated patient with vitals: {vitals}. ML Model: {model_name}. Engine: {engine_type} ({llm_model_name}). Notes: {notes}")
                add_message(session_id, "assistant", response_text)
                
                log_transaction("patient_evaluation", {
                    "session_id": session_id,
                    "engine": engine_used,
                    "ml_model": model_name,
                    "llm_model": llm_model_name,
                    "tokens_used": total_tokens,
                    "vitals": vitals,
                    "notes": notes,
                    "response": response_text
                })
                
                yield json.dumps({"done": True, "report": response_text, "tokens": total_tokens, "engine": engine_used, "ml_model": model_name, "llm_model": llm_model_name, "analyst_draft": data.get("analyst_draft", ""), "reviewer_critique": data.get("reviewer_critique", "")}) + "\n"
            else:
                yield chunk
