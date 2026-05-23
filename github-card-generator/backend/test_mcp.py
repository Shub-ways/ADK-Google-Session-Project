import asyncio
import os
import sys
from pathlib import Path

# Add the current directory to sys.path to import mcp_server
sys.path.append(str(Path(__file__).parent))

# Set environment variables for the test if .env is in parent dir
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from mcp_server import scrape_github, analyze_profile, generate_card_html

async def test_workflow():
    username = "torvalds"
    print(f"--- Starting Test for {username} ---")
    
    # 1. Scrape GitHub
    print("Step 1: Scraping GitHub...")
    github_data = await scrape_github(username)
    if "error" in github_data:
        print(f"FAILED: scrape_github - {github_data['error']}")
        return
    print("SUCCESS: scrape_github")
    
    # 2. Analyze Profile
    print("Step 2: Analyzing Profile with Gemini...")
    analysis = await analyze_profile(github_data)
    if not analysis or "card_theme" not in analysis:
        print("FAILED: analyze_profile - Invalid response")
        return
    print("SUCCESS: analyze_profile")
    
    # 3. Generate HTML Card
    print("Step 3: Generating HTML Card...")
    html = await generate_card_html(username, github_data, analysis)
    if not html or "<html" not in html.lower():
        print("FAILED: generate_card_html - No HTML generated")
        return
    print("SUCCESS: generate_card_html")
    
    # 4. Results
    print("\n--- TEST RESULTS ---")
    print(f"Card Theme: {analysis.get('card_theme')}")
    print(f"Developer Vibe: {analysis.get('developer_vibe')}")
    print(f"HTML Length: {len(html)} characters")
    print("--------------------")

if __name__ == "__main__":
    asyncio.run(test_workflow())
