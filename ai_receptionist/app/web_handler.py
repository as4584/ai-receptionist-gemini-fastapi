import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from app.receptionist_agent import ReceptionistAgent
from app.utils.logger import app_logger

async def handle_web_stream(websocket: WebSocket):
    """Handle Web Client WebSocket."""
    await websocket.accept()
    app_logger.info("Web Client connected")
    
    agent = ReceptionistAgent()
    if not await agent.connect():
        app_logger.error("Failed to connect agent, closing stream")
        await websocket.close()
        return

    try:
        # Task to receive from OpenAI/Gemini and send to Web Client
        async def receive_from_agent():
            async for event in agent.receive_events():
                event_type = event.get("type")
                
                if event_type == "response.audio.delta":
                    # Send raw PCM to browser
                    audio_payload = event.get("delta_pcm")
                    if audio_payload:
                        response = {
                            "event": "media",
                            "media": audio_payload
                        }
                        await websocket.send_text(json.dumps(response))
                        
        agent_task = asyncio.create_task(receive_from_agent())

        # Main loop: Receive from Web Client and send to Agent
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            
            if data.get("event") == "media":
                # Browser sends PCM base64
                chunk = data.get("media")
                if chunk:
                    await agent.send_audio_pcm(chunk)
                
    except WebSocketDisconnect:
        app_logger.info("Web Client disconnected")
    except Exception as e:
        app_logger.error(f"Error in web stream: {e}")
    finally:
        await agent.close()
        if not agent_task.done():
            agent_task.cancel()
