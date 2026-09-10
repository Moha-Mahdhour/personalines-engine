from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=".env")
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_SECRET")
if not (url and key):
    raise RuntimeError("Set SUPABASE_URL and SUPABASE_SECRET (see .env.example)")
supa: Client = create_client(url, key)
