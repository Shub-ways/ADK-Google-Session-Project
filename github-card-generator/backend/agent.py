import os
import sys
from pathlib import Path
from google.adk import Agent
from google.adk.tools import FunctionTool
from dotenv import load_dotenv

# Add current directory to path to import mcp_server
sys.path.append(str(Path(__file__).parent))
from mcp_server import scrape_github, analyze_profile, generate_card_html, save_card

load_dotenv()

# Initialize the Agent
github_card_agent = Agent(
    name="github_card_agent",
    model="gemini-2.5-flash",
    instruction="""
    You are a GitHub profile analyst and dev card generator. 
    When a user gives you a GitHub username, you ALWAYS follow this exact sequence: 
    1. Call 'scrape_github' with the username.
    2. Call 'analyze_profile' with the same username.
    3. Call 'generate_card_html' with the same username.
    4. Call 'save_card' with the username and the SVG HTML string returned from step 3.
    
    IMPORTANT: For steps 1-3, you only need to pass the username string.
    For step 4, pass both the username and the full SVG HTML string from step 3.
    
    Never skip steps. Be enthusiastic about developers' work. 
    If the profile is private or doesn't exist, say so clearly.
    
    CRITICAL: ALWAYS return the EXACT string returned by the 'save_card' tool as your final response. Do not add any conversational text.
    """,
    tools=[
        FunctionTool(scrape_github),
        FunctionTool(analyze_profile),
        FunctionTool(generate_card_html),
        FunctionTool(save_card)
    ]
)
