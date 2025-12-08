import sys
import os
import glob
import json
from datetime import datetime

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
from app.services.elevenlabs_service import ElevenLabsService

def generate_status():
    settings = get_settings()
    voice_service = ElevenLabsService()
    
    # Check Voice
    voice_status = voice_service.validate_voice()
    
    # Check Sim Logs
    sim_files = glob.glob("testing/sim/*.json")
    sim_files.sort(key=os.path.getmtime, reverse=True)
    recent_sims = sim_files[:5]
    
    # Check Map
    has_map = os.path.exists("conversation_map.json")
    
    md = "# Voice Pipeline Status\n\n"
    md += f"**Generated:** {datetime.now().isoformat()}\n\n"
    
    md += "## Configuration\n"
    md += f"- **Cheap-Test Mode:** {'✅ Active' if settings.CHEAP_TEST_MODE else '❌ Inactive'}\n"
    md += f"- **OpenAI Safe Mode:** {'✅ Locked' if settings.CHEAP_TEST_MODE else '⚠️ Unlocked'}\n"
    md += f"- **ElevenLabs Voice:** {settings.ELEVENLABS_VOICE_ID} ({settings.ELEVENLABS_MODEL})\n"
    md += f"- **Voice Status:** {voice_status.get('status')} (Latency: {voice_status.get('latency', 'N/A')})\n\n"
    
    md += "## Conversation Logic\n"
    md += f"- **Route Map:** {'✅ Generated' if has_map else '❌ Missing'}\n"
    if has_map:
        md += "  (See `conversation_map.md` for details)\n"
    
    md += "\n## Recent Simulations\n"
    if not recent_sims:
        md += "_No recent simulations found._\n"
    else:
        for f in recent_sims:
            try:
                with open(f, "r") as json_file:
                    data = json.load(json_file)
                    md += f"- **{data['timestamp']}**: User: '{data['user_input']}' -> AI: '{data['ai_response'][:50]}...'\n"
            except:
                pass
                
    md += "\n## Estimated Savings\n"
    # Rough estimate: $0.06/min for OpenAI Realtime vs Free for Gemini Flash
    # Assume each sim turn saves ~15 seconds of audio processing
    savings = len(sim_files) * (0.06 * 0.25) 
    md += f"**Total Saved:** ${savings:.4f} (approx)\n"
    
    with open("pipeline_status.md", "w") as f:
        f.write(md)
    
    print("Generated pipeline_status.md")

if __name__ == "__main__":
    generate_status()
