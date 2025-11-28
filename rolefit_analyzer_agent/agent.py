import os
import asyncio
import PyPDF2  #Use PyPDF2 to read PDF files
from dotenv import load_dotenv 
from typing import Any, Dict, Optional
from google.adk.agents import Agent, LlmAgent, SequentialAgent, ParallelAgent
from google.adk.models.google_llm import Gemini
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.tools.tool_context import ToolContext
from google.genai import types   # e.g., for model/config types if needed
from google.adk.tools import google_search,  AgentTool, FunctionTool

# Load environment variables from .env file
load_dotenv()

#Retry configuratio for Agentic calls
retry_config = types.HttpRetryOptions(
    attempts=5,  # Maximum retry attempts
    exp_base=7,  # Delay multiplier
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],  # Retry on these HTTP errors
)

# --- Sanity check for the API key ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError(
        "GOOGLE_API_KEY is missing. Set it in your .env or environment."
    )

#PDF Reader Tool
def read_pdf(
    file_path: str, 
    memory_key: str, 
    max_chars: int = 120_000, 
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Retrieves and cleans the text content from a PDF file.
    The extracted content is saved to the session's memory using the specified key.
    
    Args:
        file_path (str): The full path to the PDF file (e.g., 'document.pdf').
        memory_key (str): The specific session state key (e.g., 'job_description_text') 
                          under which the extracted text should be stored.
        max_chars (int): Maximum number of characters to return before truncation.
        tool_context (ToolContext): Automatically injected context to access session state.
        
    Returns:
        dict: A status dictionary confirming the operation and the memory key used.
    """
    
    if not os.path.exists(file_path):
        return {
            "status": "error",
            "error_message": f"File not found at path: {file_path}"
        }

    try:
        # --- 1. Extract Text ---
        chunks = []
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text = (page.extract_text() or "")
                chunks.append(" ".join(text.split()))
        
        full_content = "\n".join(chunks).strip()
        truncated_content = (full_content[:max_chars] + "\n...[TRUNCATED]") if len(full_content) > max_chars else full_content
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to read PDF. Internal error: {type(e).__name__}"
        }

    # --- 2. Save Text to Session State using the provided memory_key ---
    if tool_context:
        # Save content using the dynamic key provided by the agent calling the tool
        tool_context.state[memory_key] = truncated_content
        # Also write to canonical keys if the memory_key indicates it is a resume or JD
        mk = (memory_key or "").lower()
        if any(k in mk for k in ("cv", "resume", "candidate")):
            tool_context.state[CV_MEMORY_KEY] = truncated_content
        if any(k in mk for k in ("job", "jd", "description")):
            tool_context.state[JD_MEMORY_KEY] = truncated_content
        
        print(f"[read_pdf] saved {len(truncated_content)} chars to '{memory_key}'")
        return {
            "status": "success",
            "message": f"PDF text extracted successfully and saved to session memory under key: '{memory_key}'.",
            "extracted_length": len(truncated_content)
        }
    
    return {
        "status": "error",
        "message": "Session context missing, content not saved to memory.",
    }


#WRAP FUNCTIONS AS FUNCTION TOOL
pdf_reader_tool = FunctionTool(read_pdf)
print

# Setup search_memory tool
def search_memory(
    query: str,
    memory_keys: Optional[list[str]] = None,
    max_snippets: int = 5,
    snippet_radius: int = 80,
    tool_context: ToolContext = None,
) -> Dict[str, Any]:
    """
    Searches session state for text matching `query` and returns snippets with context.

    Args:
        query (str): A substring or regex to search for (simple substring search used for safety).
        memory_keys (list[str], optional): List of keys in session state to search. If None, searches all text keys.
        max_snippets (int): Maximum number of matches per memory key to return.
        snippet_radius (int): Number of characters around the match to include in the snippet.
        tool_context (ToolContext): Provided by ADK to access session state.

    Returns:
        dict: { 'matches': [ { 'memory_key': str, 'snippets': [ { 'text': str, 'start': int, 'end': int } ] } ] }
    """

    if tool_context is None:
        return {"status": "error", "error_message": "Session context missing"}

    matches = []
    q = (query or "").strip()
    if not q:
        return {"status": "error", "error_message": "Query string is empty"}

    keys_to_search = memory_keys or [k for k, v in (tool_context.state or {}).items() if isinstance(v, str)]

    print(f"[search_memory] Searching keys: {keys_to_search} for query: '{q}'")
    for key in keys_to_search:
        text = tool_context.state.get(key, "")
        if not isinstance(text, str) or not text:
            continue
        snippets = []
        start = 0
        found_count = 0
        while True:
            idx = text.find(q, start)
            if idx == -1:
                break
            s = max(0, idx - snippet_radius)
            e = min(len(text), idx + len(q) + snippet_radius)
            snippet = text[s:e]
            snippets.append({"text": snippet, "start": idx, "end": idx + len(q)})
            found_count += 1
            if found_count >= max_snippets:
                break
            start = idx + len(q)
        if snippets:
            matches.append({"memory_key": key, "snippets": snippets})

    return {"status": "success", "query": q, "matches": matches}

search_memory_tool = FunctionTool(search_memory)
#print("✅ pdf_reader_tool created.")

class CapstoneAgent(Agent):
    pass

class CapstoneSubAgent(LlmAgent):
    pass



# --- Define memory keys for clarity ---
CV_MEMORY_KEY = "pdf_resume_text" 
JD_MEMORY_KEY = "job_description_text" 

# --- Define agents ---
# --- CV Loader Agent (Saves to CV_MEMORY_KEY) ---
cv_loader_agent = CapstoneSubAgent(
    name="cv_loader_agent",
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    instruction=f"""
    Your job is to read the applicant's resume (PDF) by calling the `pdf_reader_tool` 
    to extract text from the resume and save it to session memory under the key '{CV_MEMORY_KEY}'. 
    Use the tool with an argument like:
        pdf_reader_tool(file_path="<path-to-cv-pdf>", memory_key="{CV_MEMORY_KEY}")
    
    #BOUNDARY:  Don't do any analysis.

    #OUTPUT:
    1.  Mention in your output that you have successfully stored the resume text 
    to session memory.
    2.  Display a summary of what you have saved in session memory.
    """,
    tools=[pdf_reader_tool],
    output_key="cv_loader_result",
)

# --- JD Loader Agent (Saves to JD_MEMORY_KEY) ---
jd_loader_agent = CapstoneSubAgent(
    name="jd_loader_agent",
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    instruction=f"""
    Your job is to read the job description (PDF) by calling the `pdf_reader_tool` 
    to extract text and save it under the memory key '{JD_MEMORY_KEY}'.
    Use the tool with an argument like:
        pdf_reader_tool(file_path="<path-to-jd-pdf>", memory_key="{JD_MEMORY_KEY}")
    
    #BOUNDARY:  Don't do any analysis.

    #OUTPUT:
    1.  Mention in your output that you have successfully stored the resume text 
    to session memory.
    2.  Display a summary of what you have saved in session memory.
    """,
    tools=[pdf_reader_tool],
    output_key="jd_loader_result",
)

# --- CV Screening Agent (Reads from CV_MEMORY_KEY) ---
cv_screening_agent = CapstoneSubAgent(
    name="cv_screening_agent",
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
     instruction=f"""
     You are an HR screening agent. Your job is to determine whether the candidate's resume
     (available in session memory under the key '{CV_MEMORY_KEY}') contains sufficient and
     consistent information.

     RULES:
     1. You MUST NOT hallucinate: every factual claim you make must be supported by evidence
         from session memory. For each factual claim, call the tool `search_memory(query, memory_keys=["{CV_MEMORY_KEY}"])` and include the returned snippet as evidence.
     2. If the memory under '{CV_MEMORY_KEY}' is missing or empty, DO NOT guess; respond with:
         {{"status": "INSUFFICIENT_DOCUMENT", "message": "Resume not found in session memory; please provide CV file path or call the loader."}}
     3. Only use the pre-approved tool `search_memory` when retrieving evidence; do not call any other tools.

     OUTPUT FORMAT (json):
     {{
        "status": "SUCCESS" | "INSUFFICIENT_DOCUMENT",
        "decision": "APPROVE" | "REJECT" | "APPROVE_WITH_RECOMMENDATIONS",
        "evidence": [{{"memory_key": str, "snippet": str, "start": int, "end": int}}],
        "explanation": str,
        "name": str | null
     }}

    Steps to follow:
     - Call search_memory(query=...) to find name, employment dates, roles and keywords.
     - Use only evidence discovered via search_memory to form the decision and explanation.
     - When citing evidence in the `evidence` array, include snippets exactly as returned by search_memory.
    IMPORTANT: **Return a plain JSON object only**. Do NOT wrap the JSON output 
    in markdown, code fences, or extra text. This MUST be valid JSON parsable by 
    the caller.

     """,
     tools=[search_memory_tool],
    output_key="cv_screening_result",
)
print("✅ cv_screening_agent created.")


# --- Define Talent Matching Agent ---
talent_matching_agent = CapstoneSubAgent(
    name="talent_matching_agent",
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    instruction=f"""
    You are an expert Talent Matching Agent. Your task is to match the candidate's resume 
    against the job description. You must analyze the candidate's qualifications, skills, 
    and experience against the requirements.

    To do your job:  
    - Retrieve the results of the previous analyses of cv_screening_agent using the memory key 'cv_screening_result'
    If the CV was REJECTED, you must also REJECT the candidate without further analysis.
    - If the CV was APPROVED, you must match the resume text in the memory key '{CV_MEMORY_KEY}'
        against the job description text in the memory key '{JD_MEMORY_KEY}'.
    
    CRITICAL ANALYSIS CRITERIA:
    - You must ensure that most of the necessary qualifications, skills, and experience 
      listed in the job description are present in the candidate's resume for a successful match.
    - You must ensure that most of the technologies listed in the job description are present
      in the candidate's resume for a successful match.
    
    RULES:
    1. Use only information from session memory keys '{CV_MEMORY_KEY}' and '{JD_MEMORY_KEY}'.
    2. For each claim regarding matching between CV and JD, call search_memory(query=..., memory_keys=["{CV_MEMORY_KEY}", "{JD_MEMORY_KEY}"]) and include snippets in evidence.
    3. If either document is missing in memory, respond with status INSUFFICIENT_DOCUMENT and request the file path or ask the loader to run.

    OUTPUT (json):
    1. Short Summary of Resume you extracted from memory.  Include the name of the candidate.
    2. Short Summary of Job Description from memory.
    3. Key Matches and Gaps.
    4. Decision whether to "PROCEED TO INTERVIEW" or "REJECT".
    5. Reason of your decision.
    6. `evidence`: list of matches with snippet, memory_key, and positions.
    7. Mention in your output that you have successfully saved your decision to the session memory.
    IMPORTANT: **Return plain JSON only**. Do not wrap the JSON in markdown or code fences.
    """,
    tools=[search_memory_tool],  # Allow calling search_memory to verify claims
    output_key="talent_matching_result",  # Stores decision and reasoning
)
print("✅ talent_matching_agent created.")

write_parallel_agent = ParallelAgent(
    name="write_parallel_agent",
    description="Saves both the CV and JD to memory simultaneously.",
    sub_agents=[cv_loader_agent, jd_loader_agent], # These run concurrently
)

# Root Coordinator: Orchestrates the workflow by calling the sub-agents as tools.
root_agent = SequentialAgent(
    name="root_agent",
    description="Coordinates the full talent acquisition process: reading documents, then matching.",
    # The sub_agents are run in the explicit order defined here:
    sub_agents=[
        write_parallel_agent,  # Step 1: Save documents to memory
        cv_screening_agent,     # Step 2: Read the CV from memory and screen 
        talent_matching_agent    # Step 3: Access memory keys and perform matching
    ]
)

# --- Session Service: In-memory for development ---
# InMemorySessionService stores conversations in RAM (temporary)
session_service = InMemorySessionService()

# --- Runner: In-memory execution for development ---
APP_NAME = "rolefit_analyzer_agent"
runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)

async def main():
    
    # Example paths—adjust for your repo structure
    file_path_cv = os.path.join("Fictional_CVs", "CV2_DevOps Engr.pdf")
    file_path_jd = os.path.join("Job_Description", "AI_Engineer_JD.pdf")

  
    prompt = (
        f"Please check if this CV doesn't have inconsistencies. If it passes your review, "
        f"read the Job Description and analyze if the candidate's CV matches the role. "
        f"The file_path_cv is {file_path_cv} and the file_path_jd is {file_path_jd}."
    )

    # Inject file paths into the invocation context state so any instruction
    # templates relying on `{file_path_cv}` or `{file_path_jd}` work correctly.
    state_delta = {
        "file_path_cv": file_path_cv,
        "file_path_jd": file_path_jd,
    }

    # Create/ensure the debug session exists so run_async can find the session
    session = await runner.session_service.get_session(
        app_name=runner.app_name, user_id="debug_user_id", session_id="debug_session_id"
    )
    if not session:
        session = await runner.session_service.create_session(
            app_name=runner.app_name, user_id="debug_user_id", session_id="debug_session_id"
        )

    events = []
    async for e in runner.run_async(
        user_id="debug_user_id",
        session_id="debug_session_id",
        new_message=types.UserContent(parts=[types.Part(text=prompt)]),
        state_delta=state_delta,
    ):
        events.append(e)

    print("\n \n \n === Orchestrator Events (last 10) ===")
    # Show some summarised event output for debugging
    for ev in events[-10:]:
        print(ev)

if __name__ == "__main__":
    asyncio.run(main())
