# RoleFit Analyzer (ADK Capstone)

## Overview
RoleFit Analyzer is a local, developer-focused multi-agent pipeline built with Google ADK. It extracts PDF content from candidate CVs and job descriptions, stores text in session memory, performs evidence-based CV screening, and produces a talent matching decision between a CV and a JD.

Highlights:
- Evidence-backed outputs using a `search_memory` FunctionTool to avoid hallucination
- `pdf_reader_tool` to extract PDF text into session memory
- Clean, JSON-formatted outputs from analysis agents for programmatic consumption
- Debug & validation scripts to run and validate workflows locally

---

## Features
- PDF text extraction (via PyPDF2) into session memory keys
- Substring-based evidence retrieval via `search_memory` tool
- Dedicated agents for: CV loader, JD loader, CV screening, Talent matching
- Orchestration with a sequential + parallel agent pattern
- Local `adk web` dev UI for interactive runs and tracing

---

## Architecture
- Agents:
  - `cv_loader_agent`: Reads CV, writes `pdf_resume_text`
  - `jd_loader_agent`: Reads JD, writes `job_description_text`
  - `cv_screening_agent`: Uses `search_memory` to ensure claims are evidence-backed and writes `cv_screening_result`
  - `talent_matching_agent`: Matches resume vs JD and writes `talent_matching_result`
- Tools:
  - `pdf_reader_tool`: Extracts and saves PDF text to session memory
  - `search_memory_tool`: Returns snippet matches for queries
- Session: `InMemorySessionService` (local development; replace for production)
- Runner: `Runner` with consistent `app_name` to avoid mismatch warnings

---

## Prerequisites
- Python 3.11+ (project uses a venv: `myenv`)
- `myenv` configured and activated
- Install packages in `myenv` (see Installation)
- A configured `GOOGLE_API_KEY` in `.env` file for LLM access

> NOTE: The LLM usage is subject to quotas. If you run into `429 RESOURCE_EXHAUSTED`, check your gen.ai quota and billing or reduce concurrency.

---

## Installation
Open PowerShell and run:

```powershell
# Activate the venv
.\myenv\scripts\activate.ps1

# Install dependencies
pip install -r requirements.txt
# If you don't have a requirements file, at least ensure these libs are installed
pip install "PyPDF2" "python-dotenv" "google-adk" "google-genai"
```

Create a `.env` with the `GOOGLE_API_KEY`:

```
GOOGLE_API_KEY=your_api_key_here
```

---

## Running Locally
### Start ADK web UI (dev server + local debugging)

```powershell
.\myenv\scripts\activate.ps1
& "myenv\Scripts\adk.exe" web . --port 8001 --reload
```

Open your browser at http://127.0.0.1:8001 and select the app `rolefit_analyzer_agent`.

### Run the orchestrator locally (scripted)

Use the provided script (which uses the runner and session service) to start a local test run:

```powershell
$env:PYTHONPATH='.'; & "myenv\Scripts\python.exe" scripts\run_test.py
```

This triggers:
- The loaders to save the CV and JD into session memory
- The screening and talent matching agents to run and save JSON outputs

### Validate the results (evidence verification)

```powershell
$env:PYTHONPATH='.'; & "myenv\Scripts\python.exe" scripts\validate_results.py
```

This script will:
- Run the orchestrator with the same `state_delta`
- Parse the `cv_screening_result` returned in session memory (strips code fences first if present)
- Validate that each `evidence.snippet` is actually present in the stored CV text

---

## Troubleshooting
- PyPDF2 not recognized: make sure the `myenv` Python interpreter is active (use `myenv\Scripts\python.exe`), then `pip install PyPDF2` in the venv.
- KeyError context variables (e.g., `file_path_cv`): pass file paths via `state_delta` to `runner.run_async`. `scripts/run_test.py` and `main()` show how to set these keys.
- App name mismatch: ensure `APP_NAME` in `agent.py` matches the package name and run `adk web` from the package root.
- UNEXPECTED_TOOL_CALL: ensure the tool is included in the agent's `tools` list or removed from agents that shouldn't call it.
- Quotas & 429 errors: the ADK API uses external LLM APIs and they are subject to quotas and rate limits. Reduce concurrent calls or upgrade quotas.

---

## FAQ
Q: Why plain JSON output?  
A: Returning plain JSON makes it deterministic and machine-parseable for CI and downstream programs; LLMs may sometimes add markdown wrappers, so we strip code fences in `scripts/validate_results.py`.

Q: How can I add semantic search for `search_memory`?  
A: Replace or augment the substring search in `search_memory` with a vector store or a semantic compare tool (beware of cost & privacy). Keep `search_memory` deterministic to ensure evidence can be traced.

Q: Can I use a persistent session?  
A: Yes — replace `InMemorySessionService` with a DB-backed or file-based session service for production.

Q: Why are there `App name mismatch` warnings?  
A: Runs often originate from system-installed ADK or a different module path, which results in an `app_name` mismatch. Align `runner.app_name` with the package name to avoid this.

---

## Contributing & Extensibility
- If you add new tools, limit tool scope to only agents that require them to minimize surface area.
- Use `scripts/validate_results.py` in CI to ensure agent outputs stay evidence-backed.
- Add unit tests to validate PDF extraction and `search_memory` behavior.

---

## Contact / Support
If you need help with `adk web`, sessions, or quotas, share the relevant logs (including the exact error text and any tracebacks). I'm happy to help walk through them.

---

Happy building! 
