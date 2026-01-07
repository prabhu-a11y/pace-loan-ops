import sys
# Python 3.9 compatibility patch for google-generativeai
if sys.version_info < (3, 10):
    try:
        import importlib.metadata
        import importlib_metadata
        if not hasattr(importlib.metadata, "packages_distributions"):
            importlib.metadata.packages_distributions = importlib_metadata.packages_distributions
            importlib.metadata.version = importlib_metadata.version
            importlib.metadata.PackageNotFoundError = importlib_metadata.PackageNotFoundError
    except ImportError:
        pass

from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import os
import json
import difflib
import shutil
from datetime import datetime
from browser import extract_license_info
from browser_lei import extract_lei_info
from browser2 import extract_website_data
import google.generativeai as genai
from supabase_config import supabase, upload_file, SUPABASE_URL


# Configure Gemini
GENAI_API_KEY = os.getenv("VITE_GEMINI_API_KEY") 

if not GENAI_API_KEY:
    # Try reading from .env manually if not in environment
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'), 'r') as f:
            for line in f:
                if line.startswith("VITE_GEMINI_API_KEY="):
                    GENAI_API_KEY = line.split("=", 1)[1].strip().strip('"')
                    break
    except:
        pass

if GENAI_API_KEY:
    genai.configure(api_key=GENAI_API_KEY)

app = FastAPI()

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev simplicity
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LEIRequest(BaseModel):
    leiCode: str

@app.post("/verify-lei")
async def verify_lei(request: LEIRequest):
    try:
        print(f"Received request for LEI: {request.leiCode}")
        
        # Run extraction
        data = await extract_lei_info(request.leiCode)
        
        # Handle Video
        video_path = data.get("video_path")
        public_video_path = None
        
        if video_path and os.path.exists(video_path):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_filename = f"lei_check_{request.leiCode}_{timestamp}.webm"
            public_video_path = upload_file(video_path, "zamp-uploads", f"videos/{video_filename}")
            data["public_video_path"] = public_video_path
            print(f"Video uploaded to Supabase: {public_video_path}")
            
        return data

    except Exception as e:
        print(f"Error verifying LEI: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Zamp Dashboard Configuration ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Legacy directories removed as we use Supabase now

class LicenseRequest(BaseModel):
    licenseNumber: str

class WebsiteRequest(BaseModel):
    url: str

class ZampInitRequest(BaseModel):
    processName: str
    team: str

class ZampLogRequest(BaseModel):
    processId: str # Now assumes UUID from Supabase
    log: dict # { title, status, time, artifacts, ... }
    stepId: str = None # Optional ID to identify unique steps for updates
    keyDetails: dict = None # Optional updates to key details
    metadata: dict = None # Optional updates to top-level process metadata (e.g. status, applicantName)

class HelpChatRequest(BaseModel):
    query: str
    contextData: dict = {}
    stepInfo: str = ""

def get_knowledge_base():
    try:
        kb_path = os.path.join(PROJECT_ROOT, "src", "docs", "knowledge-base.md")
        if os.path.exists(kb_path):
            with open(kb_path, 'r') as f:
                return f.read()
    except Exception as e:
        print(f"Error reading knowledge base: {e}")
    return ""

@app.post("/extract-license")
async def extract_license(request: LicenseRequest):
    try:
        print(f"Received request for license: {request.licenseNumber}")
        
        # Run the extraction logic
        data = await extract_license_info(request.licenseNumber)
        
        # Handle Video
        video_path = data.get("video_path")
        public_video_path = None
        
        if video_path and os.path.exists(video_path):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_filename = f"license_check_{request.licenseNumber}_{timestamp}.webm"
            public_video_path = upload_file(video_path, "zamp-uploads", f"videos/{video_filename}")
            data["public_video_path"] = public_video_path
            print(f"Video uploaded to Supabase: {public_video_path}")
        
        return data
        
    except Exception as e:
        print(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def extract_qr_url(file_path: str):
    try:
        if not GENAI_API_KEY:
            print("Gemini API Key missing")
            return None

        sample_file = genai.upload_file(file_path)
        print(f"Uploaded file to Gemini: {sample_file.uri}")

        model = genai.GenerativeModel("gemini-2.5-flash-lite")
        
        prompt = """
        Extract the URL encoded in the QR code within this image. 
        Also extract the "License Number" from the text.
        
        You MUST return the result in valid JSON format only. Do not add any conversational text.
        format:
        { 
            "url": "https://...", 
            "licenseNumber": "123..." 
        }
        """
        
        response = model.generate_content([sample_file, prompt])
        text = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(text)
        return data
    except Exception as e:
        print(f"Error extracting QR URL with Gemini: {e}")
        return None

@app.post("/verify-trade-license-file")
async def verify_trade_license_file(file: UploadFile = File(...)):
    try:
        temp_filename = f"temp_upload_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
        temp_path = os.path.join("/tmp", temp_filename)
        
        with open(temp_path, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
            
        qr_data = await extract_qr_url(temp_path)
        url = qr_data.get("url") if qr_data else None

        if not url:
            return {"error": "Could not identify a QR code in the document."}
            
        data = await extract_license_info(direct_url=url)
        
        # Handle Video
        video_path = data.get("video_path")
        if video_path and os.path.exists(video_path):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_filename = f"license_check_qr_{timestamp}.webm"
            data["public_video_path"] = upload_file(video_path, "zamp-uploads", f"videos/{video_filename}")
            
        # Upload original file as artifact reference
        data["uploaded_file_path"] = upload_file(temp_path, "zamp-uploads", f"uploads/{temp_filename}")
        
        return data
    except Exception as e:
        print(f"Error verifying trade license file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/verify-website")
async def verify_website(request: WebsiteRequest):
    try:
        data = await extract_website_data(request.url)
        video_path = data.get("video_path")
        if video_path and os.path.exists(video_path):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_filename = f"website_check_{timestamp}.webm"
            data["public_video_path"] = upload_file(video_path, "zamp-uploads", f"videos/{video_filename}")
        return data
    except Exception as e:
        print(f"Error verifying website: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Address and Name Matching Endpoints (Gemini-powered, no persistence changes needed) ---

class AddressMatchRequest(BaseModel):
    address1: str
    address2: str

@app.post("/match-addresses")
async def match_addresses(request: AddressMatchRequest):
    try:
        if not GENAI_API_KEY:
             return {"match": False, "reason": "No Gemini API Key"}

        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        prompt = f"""Compare these two addresses... Address 1: "{request.address1}" Address 2: "{request.address2}"... Return JSON {{ "match": boolean, "reason": "string" }}"""
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except Exception as e:
        return {"match": False, "reason": str(e)}

class NameMatchRequest(BaseModel):
    name1: str
    name2: str

@app.post("/match-names")
async def match_names(request: NameMatchRequest):
    try:
        n1 = request.name1.lower().strip()
        n2 = request.name2.lower().strip()
        if n1 == n2: return {"match": True, "confidence": 1.0, "reason": "Exact match"}
        
        similarity = difflib.SequenceMatcher(None, n1, n2).ratio()
        if similarity > 0.85: return {"match": True, "confidence": similarity, "reason": "High confidence fuzzy match"}

        if not GENAI_API_KEY: return {"match": False, "confidence": similarity}

        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        prompt = f"""Compare these two names: "{request.name1}" and "{request.name2}"... Return JSON {{ "match": boolean, "confidence": float, "reason": "string" }}"""
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except Exception as e:
        return {"match": False, "confidence": 0.0, "reason": str(e)}

# --- Zamp Integration Endpoints (SUPABASE VERSION) ---

@app.post("/zamp/init")
async def zamp_init(request: ZampInitRequest):
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Insert into Processes table
        res = supabase.table("processes").insert({
            "process_name": request.processName,
            "team": request.team,
            "year": today,
            "status": "In Progress"
        }).execute()
        
        process_data = res.data[0]
        process_id = process_data["id"]
        
        # Initialize sections
        sections = [
            {"process_id": process_id, "section_name": "overview", "title": "Overview", "content": json.dumps("Process Overview")},
            {"process_id": process_id, "section_name": "activityLogs", "title": "Activity Logs", "content": json.dumps([])},
            {"process_id": process_id, "section_name": "keyDetails", "title": "Key Details", "content": json.dumps([])}
        ]
        supabase.table("process_sections").insert(sections).execute()
        
        # Update stockId with UUID fragment
        supabase.table("processes").update({"stock_id": f"{request.processName} #{process_id[:8]}"}).eq("id", process_id).execute()
            
        return {"processId": process_id}
    except Exception as e:
        print(f"Error initializing Zamp process: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/zamp/log")
async def zamp_log(request: ZampLogRequest):
    try:
        # Fetch activityLogs section
        res = supabase.table("process_sections").select("content").eq("process_id", request.processId).eq("section_name", "activityLogs").execute()
        items = json.loads(res.data[0]["content"]) if res.data else []
            
        if "time" not in request.log:
            request.log["time"] = datetime.now().strftime("%I:%M %p")
        if request.stepId:
            request.log["stepId"] = request.stepId

        # Update or Append
        updated = False
        if request.stepId:
            for i, item in enumerate(items):
                if item.get("stepId") == request.stepId:
                    items[i].update(request.log)
                    updated = True
                    break
        if not updated:
            items.append(request.log)

        # Save activityLogs
        supabase.table("process_sections").update({"content": json.dumps(items)}).eq("process_id", request.processId).eq("section_name", "activityLogs").execute()

        # Artifact Sync
        if "artifacts" in request.log and request.log["artifacts"]:
            res_art = supabase.table("process_sections").select("content").eq("process_id", request.processId).eq("section_name", "sidebarArtifacts").execute()
            art_items = json.loads(res_art.data[0]["content"]) if res_art.data else []
            existing_ids = set(a.get("id") for a in art_items)
            for artifact in request.log["artifacts"]:
                if artifact.get("id") not in existing_ids:
                    art_items.append(artifact)
            supabase.table("process_sections").upsert({"process_id": request.processId, "section_name": "sidebarArtifacts", "title": "Artifacts", "content": json.dumps(art_items)}).execute()

        # Update Key Details
        if request.keyDetails:
            res_kd = supabase.table("process_sections").select("content").eq("process_id", request.processId).eq("section_name", "keyDetails").execute()
            kd_items = json.loads(res_kd.data[0]["content"]) if res_kd.data else []
            if isinstance(request.keyDetails, dict): kd_items.append(request.keyDetails)
            elif isinstance(request.keyDetails, list): kd_items.extend(request.keyDetails)
            supabase.table("process_sections").update({"content": json.dumps(kd_items)}).eq("process_id", request.processId).eq("section_name", "keyDetails").execute()

        # Update Metadata
        if request.metadata:
            update_fields = {}
            if "applicantName" in request.metadata: update_fields["applicant_name"] = request.metadata["applicantName"]
            if "status" in request.metadata: update_fields["status"] = request.metadata["status"]
            if update_fields:
                supabase.table("processes").update(update_fields).eq("id", request.processId).execute()
            
        return {"status": "success"}
    except Exception as e:
        print(f"Error logging to Zamp: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/zamp/upload")
async def zamp_upload(file: UploadFile = File(...)):
    try:
        temp_path = os.path.join("/tmp", file.filename)
        with open(temp_path, "wb+") as f:
            shutil.copyfileobj(file.file, f)
        public_url = upload_file(temp_path, "zamp-uploads", f"uploads/{file.filename}")
        return {"path": public_url}
    except Exception as e:
        print(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/help")
async def chat_help(request: HelpChatRequest):
    try:
        if not GENAI_API_KEY: raise HTTPException(status_code=500, detail="Gemini Missing")
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        knowledge_base_content = get_knowledge_base()
        system_instruction = f"Context: {request.stepInfo}. Knowledge: {knowledge_base_content}"
        chat = model.start_chat(history=[{"role": "user", "parts": [system_instruction + f"\n\nQUERY: {request.query}"]}])
        response = chat.send_message(request.query)
        return {"response": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class MessageRequest(BaseModel):
    processId: str
    sender: str
    content: str

@app.post("/zamp/message")
async def send_message(request: MessageRequest):
    try:
        res = supabase.table("process_sections").select("content").eq("process_id", request.processId).eq("section_name", "messages").execute()
        messages = json.loads(res.data[0]["content"]) if res.data else []
        
        new_msg = {
            "id": f"msg-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "sender": request.sender,
            "content": request.content,
            "time": datetime.now().strftime("%I:%M %p"),
            "timestamp": datetime.now().isoformat()
        }
        messages.append(new_msg)
        supabase.table("process_sections").upsert({"process_id": request.processId, "section_name": "messages", "title": "Messages", "content": json.dumps(messages)}).execute()
        return {"status": "success", "message": new_msg}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/zamp/messages/{processId}")
async def get_messages(processId: str):
    try:
        res = supabase.table("process_sections").select("content").eq("process_id", processId).eq("section_name", "messages").execute()
        return {"messages": json.loads(res.data[0]["content"]) if res.data else []}
    except Exception as e:
        return {"messages": []}

@app.get("/zamp/status/{processId}")
async def get_process_status(processId: str):
    res = supabase.table("processes").select("status").eq("id", processId).execute()
    return {"status": res.data[0]["status"] if res.data else "Unknown"}

@app.post("/zamp/approve/{processId}")
async def approve_application(processId: str):
    try:
        supabase.table("processes").update({"status": "Done"}).eq("id", processId).execute()
        
        # Log approval
        res_log = supabase.table("process_sections").select("content").eq("process_id", processId).eq("section_name", "activityLogs").execute()
        logs = json.loads(res_log.data[0]["content"]) if res_log.data else []
        logs.append({"title": "Application Approved", "status": "success", "type": "success", "time": datetime.now().strftime("%I:%M %p")})
        supabase.table("process_sections").update({"content": json.dumps(logs)}).eq("process_id", processId).eq("section_name", "activityLogs").execute()
        
        # Key Details update
        res_kd = supabase.table("process_sections").select("content").eq("process_id", processId).eq("section_name", "keyDetails").execute()
        kd = json.loads(res_kd.data[0]["content"]) if res_kd.data else []
        if kd: kd[-1]["status"] = "Done"
        else: kd.append({"status": "Done"})
        supabase.table("process_sections").update({"content": json.dumps(kd)}).eq("process_id", processId).eq("section_name", "keyDetails").execute()
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/zamp/processes")
async def get_all_processes():
    try:
        res = supabase.table("processes").select("*").order("created_at", desc=True).execute()
        # Map camelCase for frontend compatibility if needed
        # In processes table we have applicant_name, stock_id etc.
        processes = []
        for p in res.data:
            processes.append({
                "id": p["id"],
                "stockId": p.get("stock_id"),
                "applicantName": p.get("applicant_name"),
                "name": p.get("applicant_name"), # fallback
                "year": p.get("year"),
                "status": p.get("status")
            })
        return processes
    except Exception as e:
        print(f"Error fetching processes: {e}")
        return []

@app.get("/zamp/process/{processId}")
async def get_process_detail(processId: str):
    try:
        # Fetch metadata
        res_meta = supabase.table("processes").select("*").eq("id", processId).execute()
        if not res_meta.data:
             raise HTTPException(status_code=404, detail="Process not found")
        
        meta = res_meta.data[0]
        
        # Fetch sections
        res_sections = supabase.table("process_sections").select("*").eq("process_id", processId).execute()
        
        sections = {}
        for s in res_sections.data:
            sections[s["section_name"]] = {
                "title": s["title"],
                "items": json.loads(s["content"]) if s["section_name"] != "overview" else s["content"]
            }
            # Special handling for overview if it's stored differently
            if s["section_name"] == "overview":
                 try:
                     sections[s["section_name"]]["content"] = json.loads(s["content"])
                 except:
                     sections[s["section_name"]]["content"] = s["content"]

        return {
            "id": meta["id"],
            "applicantName": meta.get("applicant_name"),
            "status": meta.get("status"),
            "sections": sections
        }
    except Exception as e:
        print(f"Error fetching process detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class HITLActionRequest(BaseModel):
    processId: str
    actionId: str
    logId: str

@app.post("/zamp/hitl-action")
async def hitl_action(request: HITLActionRequest):
    try:
        # Fetch activity logs
        res = supabase.table("process_sections").select("content").eq("process_id", request.processId).eq("section_name", "activityLogs").execute()
        logs = json.loads(res.data[0]["content"]) if res.data else []
        
        # Find the log and update its status
        for log in logs:
            if log.get("id") == request.logId:
                log["status"] = "success"
                log["title"] = f"Action Completed: {request.actionId.replace('-', ' ').title()}"
                # Remove HITL actions after completion
                if "hitlActions" in log:
                    del log["hitlActions"]
                break
        
        # Save updated logs
        supabase.table("process_sections").update({"content": json.dumps(logs)}).eq("process_id", request.processId).eq("section_name", "activityLogs").execute()
        
        return {"status": "success"}
    except Exception as e:
        print(f"Error handling HITL action: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/zamp/seed-auto-loan/{processId}")
async def seed_auto_loan(processId: str):
    try:
        # Define high-fidelity logs for Auto Loan Ops Journey
        logs = [
            {
                "id": "log-1",
                "title": "Borrower Identity & KYC Verified",
                "status": "success",
                "time": "10:00 AM",
                "reasoning": ["Emirates ID scan matches facial biometrics", "No AML hits found in World-Check"],
                "artifacts": [{"id": "art-eid", "label": "Emirates ID Scan", "icon": "file", "type": "image", "imagePath": "https://placehold.co/400x300?text=Emirates+ID"}]
            },
            {
                "id": "log-2",
                "title": "Vehicle Collateral Valuation",
                "status": "success",
                "time": "11:30 AM",
                "reasoning": ["Market value AED 120,000", "LTV ratio (80%) is within policy limits"],
                "artifacts": [{"id": "art-val", "label": "Valuation Report", "icon": "file", "type": "file", "pdfPath": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"}]
            },
            {
                "id": "log-3",
                "title": "Collateral Inspection in Progress",
                "status": "processing",
                "time": "01:45 PM",
                "reasoning": ["Physical inspection scheduled at Tasjeel"],
                "artifacts": []
            },
            {
                "id": "log-4",
                "title": "Income & Employment Verification",
                "status": "processing",
                "time": "02:00 PM",
                "reasoning": ["Fetching salary certificates from UAE PASS"],
                "artifacts": []
            },
            {
                "id": "log-5",
                "title": "Interest Rate Approval Required",
                "status": "needs_attention",
                "time": "02:30 PM",
                "reasoning": ["Requested rate (3.5%) is below standard tier (3.9%)", "Customer has high credit score of 780"],
                "hitlActions": [
                    {"id": "approve-rate", "label": "Approve 3.5% Rate", "primary": True},
                    {"id": "counter-offer", "label": "Counter with 3.7%", "primary": False}
                ],
                "artifacts": [{"id": "art-credit", "label": "AECB Credit Report", "icon": "table", "type": "table", "data": {"Score": 780, "Defaults": 0}}]
            },
            {
                "id": "log-6",
                "title": "Potential AML Conflict: Secondary Hit",
                "status": "needs_attention",
                "time": "02:45 PM",
                "reasoning": ["Name match on 'John Doe' in restricted list", "Date of birth mismatch (1985 vs 1990)"],
                "hitlActions": [
                    {"id": "dismiss-hit", "label": "Dismiss False Positive", "primary": True},
                    {"id": "escalate", "label": "Escalate to Compliance", "primary": False}
                ],
                "artifacts": [{"id": "art-aml", "label": "AML Matching Details", "icon": "table", "type": "table", "data": {"Match Confidence": "85%", "List Name": "OFAC SDN"}}]
            }
        ]
        
        # Save logs to process_sections
        supabase.table("process_sections").update({"content": json.dumps(logs)}).eq("process_id", processId).eq("section_name", "activityLogs").execute()
        
        # Update metadata
        supabase.table("processes").update({"status": "Needs Review", "applicant_name": "Hamdan Rashid"}).eq("id", processId).execute()
        
        return {"status": "seeded"}
    except Exception as e:
        print(f"Error seeding data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/zamp/processes")
async def zamp_processes():
    try:
        res = supabase.table("processes").select("*").order("created_at", desc=True).execute()
        return res.data
    except Exception as e:
        print(f"Error fetching processes: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/zamp/seed-demo-data")
async def seed_demo_data():
    try:
        from uuid import uuid4
        print(f"DEBUG: Seeding to Supabase URL: {SUPABASE_URL}")
        
        # 1. Hamdan Rashid - Needs Attention (Red)
        hamdan_id = str(uuid4())
        supabase.table("processes").insert({
            "id": hamdan_id,
            "process_name": "Auto Loan Application",
            "applicant_name": "Hamdan Rashid",
            "status": "Needs Review",
            "year": "2024-01-07"
        }).execute()
        
        hamdan_logs = [
            {"id": str(uuid4()), "title": "Application Started", "status": "success", "time": "09:00 AM", "reasoning": ["User selected Auto Loan Ops flow"]},
            {"id": str(uuid4()), "title": "Identity Verification", "status": "success", "time": "09:15 AM", "reasoning": ["EID Verified"], "artifacts": [{"id": "h-art1", "label": "EID Scan", "icon": "file", "type": "image", "imagePath": "https://placehold.co/400x300?text=Hamdan+EID"}]},
            {"id": str(uuid4()), "title": "Interest Rate Review", "status": "needs_attention", "time": "10:30 AM", "reasoning": ["Flagged: Manual override requested for 3.2% rate"], "hitlActions": [{"id": "app-rate", "label": "Approve 3.2%", "primary": True}, {"id": "reject-rate", "label": "Stick to 3.5%", "primary": False}]}
        ]
        supabase.table("process_sections").insert([
            {"process_id": hamdan_id, "section_name": "activityLogs", "content": json.dumps(hamdan_logs)},
            {"process_id": hamdan_id, "section_name": "keyDetails", "content": json.dumps({"Loan Amount": "AED 250,000", "Credit Score": "740"})}
        ]).execute()

        # 2. Fatima Al Mansouri - In Progress (Blue)
        fatima_id = str(uuid4())
        supabase.table("processes").insert({
            "id": fatima_id,
            "process_name": "Auto Loan Application",
            "applicant_name": "Fatima Al Mansouri",
            "status": "In Progress",
            "year": "2024-01-07"
        }).execute()
        
        fatima_logs = [
            {"id": str(uuid4()), "title": "KYC Verified", "status": "success", "time": "11:00 AM", "reasoning": ["Biometrics match"]},
            {"id": str(uuid4()), "title": "Collateral Valuation", "status": "processing", "time": "01:00 PM", "reasoning": ["Agent dispatched to dealer location"], "artifacts": []}
        ]
        supabase.table("process_sections").insert([
            {"process_id": fatima_id, "section_name": "activityLogs", "content": json.dumps(fatima_logs)}
        ]).execute()

        # 3. Omar Hassan - Done (Green)
        omar_id = str(uuid4())
        supabase.table("processes").insert({
            "id": omar_id,
            "process_name": "Auto Loan Application",
            "applicant_name": "Omar Hassan",
            "status": "Done",
            "year": "2024-01-06"
        }).execute()
        
        omar_logs = [
            {"id": str(uuid4()), "title": "Valuation Complete", "status": "success", "time": "Yesterday", "reasoning": ["Vehicle value: AED 180k"], "artifacts": [{"id": "o-art1", "label": "Valuation Report", "icon": "file", "type": "file", "pdfPath": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"}]},
            {"id": str(uuid4()), "title": "Funds Disbursed", "status": "success", "time": "Yesterday", "reasoning": ["AED 150,000 sent to Tesla Motors UAE"]}
        ]
        supabase.table("process_sections").insert([
            {"process_id": omar_id, "section_name": "activityLogs", "content": json.dumps(omar_logs)}
        ]).execute()

        return {"status": "Demo data seeded successfully"}
    except Exception as e:
        print(f"Error seeding demo data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
