import sys
import os
import json
import requests

# Add parent dir to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.receptionist_agent import SYSTEM_PROMPT
from app.config import get_settings

def map_routes():
    settings = get_settings()
    api_key = settings.GEMINI_API_KEY
    
    print("Analyzing System Prompt with Gemini...")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    analysis_prompt = f"""
    Analyze the following System Prompt for an AI Receptionist.
    Create a JSON structure representing the conversation flow.
    Include:
    - "greeting": The initial greeting.
    - "intents": A list of possible user intents (e.g., "ask_hours", "leave_message").
    - "flow": A tree or list of steps for complex flows (like message taking).
    - "fallback": Behavior for unknown requests.
    
    System Prompt:
    {SYSTEM_PROMPT}
    
    Output ONLY the JSON.
    """
    
    data = {
        "contents": [{
            "parts": [{"text": analysis_prompt}]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            print(f"Error: {response.text}")
            return
            
        result = response.json()
        text_content = result['candidates'][0]['content']['parts'][0]['text']
        
        # Strip markdown code blocks if present
        if "```json" in text_content:
            text_content = text_content.split("```json")[1].split("```")[0].strip()
        elif "```" in text_content:
            text_content = text_content.split("```")[1].split("```")[0].strip()
            
        route_map = json.loads(text_content)
        
        # Save JSON
        with open("conversation_map.json", "w") as f:
            json.dump(route_map, f, indent=2)
        print("Saved conversation_map.json")
        
        # Save Markdown
        with open("conversation_map.md", "w") as f:
            f.write("# Conversation Route Map\n\n")
            f.write(f"**Greeting:** {route_map.get('greeting')}\n\n")
            f.write("## Intents\n")
            for intent in route_map.get('intents', []):
                f.write(f"- {intent}\n")
            f.write("\n## Flow Logic\n")
            f.write("```json\n")
            f.write(json.dumps(route_map.get('flow'), indent=2))
            f.write("\n```\n")
            
        print("Saved conversation_map.md")
        
    except Exception as e:
        print(f"Mapping failed: {e}")

if __name__ == "__main__":
    map_routes()
