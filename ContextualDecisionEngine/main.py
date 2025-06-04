"""
Multi-Format Autonomous AI System with Contextual Decisioning & Chained Actions
FastAPI application that processes Email, JSON, and PDF inputs through specialized agents.
"""

import os
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import json
from typing import Optional

from agents.classifier import ClassifierAgent
from agents.email_agent import EmailAgent
from agents.json_agent import JSONAgent
from agents.pdf_agent import PDFAgent
from memory.store import MemoryStore
from routers.action_router import ActionRouter

app = FastAPI(
    title="Multi-Format Autonomous AI System",
    description="Processes inputs from Email, JSON, and PDF with contextual decisioning and chained actions",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/samples", StaticFiles(directory="samples"), name="samples")

# Initialize components
memory_store = MemoryStore()
classifier_agent = ClassifierAgent(memory_store)
email_agent = EmailAgent(memory_store)
json_agent = JSONAgent(memory_store)
pdf_agent = PDFAgent(memory_store)
action_router = ActionRouter(memory_store)

@app.on_event("startup")
async def startup_event():
    """Initialize the database on startup"""
    memory_store.init_db()

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page"""
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.post("/process")
async def process_input(
    file: Optional[UploadFile] = File(None),
    text_input: Optional[str] = Form(None),
    input_type: Optional[str] = Form(None)
):
    """
    Process input through the multi-agent system
    Accepts file uploads or text input
    """
    try:
        print(f"DEBUG: Received request - file: {file is not None}, text_input length: {len(text_input) if text_input else 0}, input_type: {input_type}")
        if text_input:
            print(f"DEBUG: Text preview: {repr(text_input[:100])}")
        # Determine input content and type
        content = None
        detected_format = None
        
        if file and file.filename:
            # Handle file upload
            content = await file.read()
            if file.content_type == "application/pdf":
                # For PDF, save temporarily for processing
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(content)
                    content = tmp_file.name
                    detected_format = "PDF"
            else:
                # For text files, decode content
                content = content.decode('utf-8')
                if file.filename and file.filename.endswith('.json'):
                    detected_format = "JSON"
        elif text_input and text_input.strip():
            content = text_input.strip()
        else:
            raise HTTPException(status_code=400, detail="No input provided")
        
        if not content:
            raise HTTPException(status_code=400, detail="Empty input provided")
        
        # Ensure content is a string and has meaningful length
        content_str = str(content).strip()
        if len(content_str) < 3:
            raise HTTPException(status_code=400, detail="Input too short")
        
        # Step 1: Classify the input
        classification_result = await classifier_agent.classify(content, detected_format)
        
        # Step 2: Route to appropriate agent based on classification
        agent_result = None
        if classification_result['format'] == 'Email':
            agent_result = await email_agent.process(content, classification_result)
        elif classification_result['format'] == 'JSON':
            agent_result = await json_agent.process(content, classification_result)
        elif classification_result['format'] == 'PDF':
            agent_result = await pdf_agent.process(content, classification_result)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {classification_result['format']}")
        
        # Step 3: Trigger follow-up actions based on agent output
        action_result = await action_router.route_action(agent_result, classification_result)
        
        # Step 4: Log the complete trace
        trace_id = memory_store.log_complete_trace(
            classification_result, agent_result, action_result
        )
        
        # Clean up temporary PDF file if created
        if detected_format == "PDF" and isinstance(content, str) and content.startswith('/tmp'):
            try:
                os.unlink(content)
            except:
                pass
        
        return JSONResponse({
            "success": True,
            "trace_id": trace_id,
            "classification": classification_result,
            "agent_result": agent_result,
            "actions_triggered": action_result,
            "message": "Input processed successfully through multi-agent system"
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR: Processing failed - {str(e)}")
        print(f"TRACEBACK: {error_details}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "Failed to process input through multi-agent system"
            }
        )

@app.get("/memory/traces")
async def get_traces():
    """Get all processing traces from memory"""
    try:
        traces = memory_store.get_all_traces()
        return JSONResponse({
            "success": True,
            "traces": traces
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@app.get("/memory/trace/{trace_id}")
async def get_trace(trace_id: str):
    """Get specific trace by ID"""
    try:
        trace = memory_store.get_trace(trace_id)
        if not trace:
            raise HTTPException(status_code=404, detail="Trace not found")
        
        return JSONResponse({
            "success": True,
            "trace": trace
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Multi-agent system is running"}

# Simulate external endpoints for action router
@app.post("/crm/escalate")
async def simulate_crm_escalate(data: dict):
    """Simulate CRM escalation endpoint"""
    return {
        "success": True,
        "ticket_id": f"CRM-{hash(str(data)) % 10000}",
        "message": "Issue escalated to CRM system"
    }

@app.post("/crm/log")
async def simulate_crm_log(data: dict):
    """Simulate CRM logging endpoint"""
    return {
        "success": True,
        "log_id": f"LOG-{hash(str(data)) % 10000}",
        "message": "Issue logged in CRM system"
    }

@app.post("/risk_alert")
async def simulate_risk_alert(data: dict):
    """Simulate risk alert endpoint"""
    return {
        "success": True,
        "alert_id": f"RISK-{hash(str(data)) % 10000}",
        "message": "Risk alert created"
    }

@app.post("/compliance/flag")
async def simulate_compliance_flag(data: dict):
    """Simulate compliance flagging endpoint"""
    return {
        "success": True,
        "flag_id": f"COMP-{hash(str(data)) % 10000}",
        "message": "Compliance issue flagged"
    }

if __name__ == "__main__":
    # Bind to 0.0.0.0:5000 for external access
    uvicorn.run(app, host="0.0.0.0", port=5000)
