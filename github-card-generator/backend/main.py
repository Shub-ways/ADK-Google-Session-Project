import os
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
import json

# Import the tool functions directly for the reliable pipeline
from mcp_server import scrape_github, analyze_profile, generate_card_html, save_card

app = FastAPI(title="GitHub Dev Card API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static directories exist
STATIC_DIR = Path(__file__).parent / "static"
CARDS_DIR = STATIC_DIR / "cards"
CARDS_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

class GenerateRequest(BaseModel):
    username: str

@app.get("/health")
async def health():
    """Health check endpoint for Cloud Run."""
    return {"status": "ok"}

@app.get("/", response_class=FileResponse)
async def serve_frontend():
    """Serve the frontend HTML."""
    frontend_path = Path(__file__).parent / "frontend" / "index.html"
    if frontend_path.exists():
        return FileResponse(frontend_path, media_type="text/html")
    return {"error": "Frontend not found"}

@app.post("/generate")
async def generate(request: GenerateRequest):
    """Run the card generation pipeline directly for reliability and speed."""
    try:
        username = request.username.strip()
        
        # Step 1: Scrape GitHub profile
        print(f"[Pipeline] Step 1: Scraping GitHub for {username}...")
        github_result = await scrape_github(username)
        github_data = json.loads(github_result) if isinstance(github_result, str) else github_result
        print(f"[Pipeline] Step 1 done: {github_data.get('name', 'unknown')}")
        
        # Check for errors from GitHub
        if "error" in github_data:
            raise HTTPException(status_code=404, detail=github_data["error"])
        
        # Step 2: Analyze profile with Gemini
        print(f"[Pipeline] Step 2: Analyzing profile for {username}...")
        analysis_result = await analyze_profile(username)
        print(f"[Pipeline] Step 2 done.")
        
        # Step 3: Generate SVG card
        print(f"[Pipeline] Step 3: Generating card for {username}...")
        svg_content = await generate_card_html(username)
        print(f"[Pipeline] Step 3 done.")
        
        if svg_content.startswith("Error:"):
            raise HTTPException(status_code=500, detail=svg_content)
        
        # Step 4: Save card
        print(f"[Pipeline] Step 4: Saving card for {username}...")
        card_path = await save_card(username, svg_content)
        print(f"[Pipeline] Step 4 done. Saved to {card_path}")
        
        return {
            "username": username,
            "card_url": f"/card/{username}",
            "html": svg_content
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in /generate: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/card/{username}")
async def serve_card(username: str):
    """Serves the saved SVG card directly."""
    file_path = CARDS_DIR / f"{username}.svg"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Card not found. Please generate it first.")
    return FileResponse(file_path, media_type="image/svg+xml")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
