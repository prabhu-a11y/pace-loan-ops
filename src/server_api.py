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
from supabase_config import supabase, upload_file


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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
