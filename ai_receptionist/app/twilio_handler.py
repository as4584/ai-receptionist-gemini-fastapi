import json
import asyncio
import base64
from fastapi import WebSocket, WebSocketDisconnect
from app.receptionist_agent import ReceptionistAgent
from app.utils.logger import app_logger
from app.diagnostics import diagnostics

async def handle_media_stream(websocket: WebSocket):
    """Handle Twilio Media Stream WebSocket."""
    await websocket.accept()
    app_logger.info("Twilio Media Stream connected")
    
    agent = ReceptionistAgent()
    if not await agent.connect():
        app_logger.error("Failed to connect agent, closing stream")
        await websocket.close()
        return

    diagnostics.active_calls += 1
    diagnostics.total_calls_processed += 1
    stream_sid = None
    
    try:
        # Task to receive from OpenAI and send to Twilio
        async def receive_from_openai():
            nonlocal stream_sid
            async for event in agent.receive_events():
                event_type = event.get("type")
                
                if event_type == "response.audio.delta":
                    audio_payload = event.get("delta")
                    if audio_payload and stream_sid:
                        response = {
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {
                                "payload": audio_payload
                            }
                        }
                        await websocket.send_text(json.dumps(response))
                        
                elif event_type == "input_audio_buffer.speech_started":
                    # Interruption detected: Clear Twilio buffer
                    app_logger.info("Interruption detected, clearing buffer")
                    if stream_sid:
                        clear_msg = {
                            "event": "clear",
                            "streamSid": stream_sid
                        }
                        await websocket.send_text(json.dumps(clear_msg))
                        # Also cancel current response in OpenAI if needed
                        # (OpenAI usually handles this automatically with server_vad)

        openai_task = asyncio.create_task(receive_from_openai())

        # Main loop: Receive from Twilio and send to OpenAI
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            
            if data["event"] == "media":
                chunk = data["media"]["payload"]
                await agent.send_audio(chunk)
                
            elif data["event"] == "start":
                stream_sid = data["start"]["streamSid"]
                app_logger.info(f"Stream started: {stream_sid}")
                diagnostics.last_twilio_status = "streaming"
                
            elif data["event"] == "stop":
                app_logger.info("Stream stopped")
                break
                
    except WebSocketDisconnect:
        app_logger.info("Twilio WebSocket disconnected")
    except Exception as e:
        app_logger.error(f"Error in media stream: {e}")
        diagnostics.record_error(e, "Media Stream")
    finally:
        diagnostics.active_calls -= 1
        await agent.close()
        if not openai_task.done():
            openai_task.cancel()
