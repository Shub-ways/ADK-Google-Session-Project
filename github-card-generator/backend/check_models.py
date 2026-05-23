import os
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path

# Load env from parent dir of backend
load_dotenv(Path(__file__).parent.parent / ".env")

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def check_models():
    print("Listing available models...")
    try:
        models = genai.list_models()
        found = False
        for m in models:
            print(f"- {m.name} (Supports: {m.supported_generation_methods})")
            if "gemini-2.5-flash" in m.name:
                found = True
        
        if found:
            print("\n✅ model 'gemini-2.5-flash' IS AVAILABLE!")
        else:
            print("\n❌ model 'gemini-2.5-flash' NOT FOUND.")
            
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    check_models()
