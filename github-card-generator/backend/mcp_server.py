import os
import json
import httpx
import base64
from mcp.server.fastmcp import FastMCP
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("GitHubDevCardTools")

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash") 

# In-memory cache so tools can share data without relying on the agent
# to perfectly reconstruct complex dict parameters between tool calls
_cache = {}

async def get_base64_image(url: str) -> str:
    """Fetch an image and return it as a base64 data URI."""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                content_type = resp.headers.get("Content-Type", "image/png")
                b64_data = base64.b64encode(resp.content).decode("utf-8")
                return f"data:{content_type};base64,{b64_data}"
    except Exception as e:
        print(f"Error fetching image: {e}")
    return ""

@mcp.tool()
async def scrape_github(username: str) -> str:
    """Fetch GitHub profile and repository statistics for a username. Returns a JSON string summary."""
    headers = {}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=15.0) as client:
        # Get user profile
        user_res = await client.get(f"https://api.github.com/users/{username}")
        if user_res.status_code != 200:
            return json.dumps({"error": f"User {username} not found"})
        user_data = user_res.json()

        # Get repos
        repos_res = await client.get(f"https://api.github.com/users/{username}/repos?sort=updated&per_page=100")
        repos_data = repos_res.json() if repos_res.status_code == 200 else []

    # Process repos
    top_repos = sorted(repos_data, key=lambda x: x.get("stargazers_count", 0), reverse=True)[:6]
    top_repos_list = [{
        "name": r["name"],
        "stars": r["stargazers_count"],
        "language": r["language"],
        "description": r["description"]
    } for r in top_repos]

    # Aggregate languages
    languages = {}
    for r in repos_data:
        lang = r.get("language")
        if lang:
            languages[lang] = languages.get(lang, 0) + 1
    
    sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)
    
    github_data = {
        "name": user_data.get("name") or username,
        "bio": user_data.get("bio"),
        "location": user_data.get("location"),
        "avatar_url": user_data.get("avatar_url"),
        "public_repos": user_data.get("public_repos"),
        "followers": user_data.get("followers"),
        "top_repos": top_repos_list,
        "most_used_languages": [l[0] for l in sorted_langs[:5]]
    }
    
    # Cache the data so other tools can access it by username
    _cache[f"{username}_github"] = github_data
    
    return json.dumps(github_data, indent=2)

@mcp.tool()
async def analyze_profile(username: str) -> str:
    """Analyze the GitHub profile data (previously fetched) with Gemini AI. Takes only the username."""
    # Retrieve cached github data
    github_data = _cache.get(f"{username}_github", {})
    if not github_data:
        return json.dumps({"error": "No GitHub data found. Call scrape_github first."})
    
    prompt = f"""
    Analyze this GitHub profile data and return a JSON object with:
    - developer_vibe: A 1-sentence personality description.
    - top_skills: A list of exactly 3 technical skills.
    - fun_fact: A clever observation inferred from their repositories.
    - card_theme: Choose ONE of: "hacker", "builder", "researcher", "designer", "open-source-hero".

    GitHub Data:
    {json.dumps(github_data, indent=2)}

    Return ONLY valid JSON.
    """
    
    try:
        response = model.generate_content(prompt)
        # Clean response text if it includes markdown blocks
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        analysis = json.loads(clean_text)
    except Exception as e:
        print(f"Gemini API Error: {e}")
        analysis = {
            "developer_vibe": "A dedicated developer exploring the digital frontier.",
            "top_skills": (github_data.get("most_used_languages", []) + ["Coding"])[:3],
            "fun_fact": "Has a knack for building interesting things.",
            "card_theme": "builder"
        }
    
    # Cache the analysis
    _cache[f"{username}_analysis"] = analysis
    
    return json.dumps(analysis, indent=2)

@mcp.tool()
async def generate_card_html(username: str) -> str:
    """Generate a self-contained SVG dev card for the username. Uses cached GitHub data and analysis."""
    # Retrieve cached data
    github_data = _cache.get(f"{username}_github", {})
    analysis = _cache.get(f"{username}_analysis", {})
    
    if not github_data:
        return "Error: No GitHub data found. Call scrape_github first."
    if not analysis:
        return "Error: No analysis found. Call analyze_profile first."
    
    theme = analysis.get("card_theme", "builder")
    
    # Theme colors (BG, Text, Accent)
    themes = {
        "hacker": ("#000000", "#00FF00", "#003300"),
        "builder": ("#F0F7FF", "#1E3A8A", "#DBEAFE"),
        "researcher": ("#F5F3FF", "#4C1D95", "#EDE9FE"),
        "designer": ("#FDF2F8", "#831843", "#FCE7F3"),
        "open-source-hero": ("#FFF7ED", "#7C2D12", "#FFEDD5")
    }
    
    bg, text, accent = themes.get(theme, themes["builder"])
    
    name = github_data.get("name", username)
    vibe = analysis.get("developer_vibe", "")
    repos = github_data.get("public_repos", 0)
    followers = github_data.get("followers", 0)
    fun_fact = analysis.get("fun_fact", "")
    
    # Get base64 avatar
    avatar_url = github_data.get("avatar_url", "")
    avatar_b64 = await get_base64_image(avatar_url) if avatar_url else ""

    skills = analysis.get("top_skills", [])
    skills_svg = ""
    for i, s in enumerate(skills[:3]):
        skills_svg += f'<rect x="{20 + i*100}" y="140" width="90" height="24" rx="12" fill="{accent}"/><text x="{65 + i*100}" y="156" font-family="Arial" font-size="12" fill="{text}" text-anchor="middle" font-weight="bold">{s}</text>'

    top_repos = github_data.get("top_repos", [])[:3]
    repos_svg = ""
    for i, r in enumerate(top_repos):
        repos_svg += f"""
            <rect x="20" y="{230 + i*60}" width="360" height="50" rx="8" fill="{accent}" opacity="0.5"/>
            <text x="35" y="{250 + i*60}" font-family="Arial" font-size="14" font-weight="bold" fill="{text}">{r['name']}</text>
            <text x="35" y="{270 + i*60}" font-family="Arial" font-size="11" fill="{text}" opacity="0.8">⭐ {r['stars']} | {r['language'] or 'Code'}</text>
        """

    svg = f"""<svg width="400" height="500" viewBox="0 0 400 500" fill="none" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
        <rect width="400" height="500" rx="20" fill="{bg}" stroke="{text}" stroke-width="2"/>
        
        <!-- Header -->
        <defs>
            <clipPath id="avatarClip">
                <circle cx="60" cy="60" r="30" />
            </clipPath>
        </defs>
        
        <circle cx="60" cy="60" r="30" fill="{accent}"/> 
        <image x="30" y="30" width="60" height="60" href="{avatar_b64}" xlink:href="{avatar_b64}" clip-path="url(#avatarClip)" preserveAspectRatio="xMidYMid slice" />
        <circle cx="60" cy="60" r="30" fill="none" stroke="{text}" stroke-width="2"/> <!-- Border -->
        
        <text x="105" y="55" font-family="Arial" font-size="20" font-weight="bold" fill="{text}">{name}</text>
        <text x="105" y="75" font-family="Arial" font-size="14" fill="{text}" opacity="0.7">@{username}</text>
        
        <!-- Vibe -->
        <text x="20" y="115" font-family="Arial" font-size="13" font-style="italic" fill="{text}">"{vibe}"</text>
        
        <!-- Skills -->
        {skills_svg}
        
        <!-- Stats -->
        <rect x="20" y="180" width="170" height="40" rx="8" fill="{accent}" opacity="0.3"/>
        <text x="105" y="198" font-family="Arial" font-size="16" font-weight="bold" fill="{text}" text-anchor="middle">{repos}</text>
        <text x="105" y="212" font-family="Arial" font-size="10" fill="{text}" text-anchor="middle">REPOSITORIES</text>
        
        <rect x="210" y="180" width="170" height="40" rx="8" fill="{accent}" opacity="0.3"/>
        <text x="295" y="198" font-family="Arial" font-size="16" font-weight="bold" fill="{text}" text-anchor="middle">{followers}</text>
        <text x="295" y="212" font-family="Arial" font-size="10" fill="{text}" text-anchor="middle">FOLLOWERS</text>
        
        <!-- Repos -->
        {repos_svg}
        
        <!-- Footer -->
        <text x="200" y="470" font-family="Arial" font-size="10" fill="{text}" text-anchor="middle" opacity="0.6">✨ {fun_fact}</text>
    </svg>"""
    return svg

@mcp.tool()
async def save_card(username: str, html: str) -> str:
    """Save the SVG card and return its relative URL path."""
    static_dir = Path("static/cards")
    static_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = static_dir / f"{username}.svg"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    return f"/static/cards/{username}.svg"

if __name__ == "__main__":
    mcp.run()
