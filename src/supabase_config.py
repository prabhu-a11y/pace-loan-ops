import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_SERVICE_ROLE_KEY") or os.getenv("VITE_SUPABASE_PUBLISHABLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    # Fallback to reading from .env if not set via environment (for local dev)
    try:
        from dotenv import load_dotenv
        load_dotenv()
        SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
        SUPABASE_KEY = os.getenv("VITE_SUPABASE_SERVICE_ROLE_KEY") or os.getenv("VITE_SUPABASE_PUBLISHABLE_KEY")
    except ImportError:
        pass

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

def upload_file(file_path: str, bucket: str, destination_path: str):
    """Uploads a file to Supabase storage and returns the public URL."""
    if not supabase:
        return None
    
    with open(file_path, "rb") as f:
        res = supabase.storage.from_(bucket).upload(destination_path, f, {"upsert": "true"})
    
    return supabase.storage.from_(bucket).get_public_url(destination_path)
