import json
import asyncio
import websockets
import base64
import audioop
from app.config import get_settings
from app.utils.logger import app_logger
from app.diagnostics import diagnostics

SYSTEM_PROMPT = """ROLE: Elite AI Receptionist Demo.
GOAL: Impress caller. Sell automation benefits.
TONE: Professional, enthusiastic, concise.

GREET: "Hi! I'm an AI receptionist. I capture leads, send texts, and make calls 24/7. How can I elevate your business?"

FEATURES:
1. Instant SMS: "I send booking links instantly."
2. Outbound: "I follow up on leads."
3. Email: "I draft team emails."
4. 24/7: "Never miss a customer."

FAQ:
- Hours/Loc: "I'm a demo. I work 24/7."
- Owner (Lex): Get Name, Phone, Msg. Say: "Passing to Lex."
"""

# Pre-generated Mock Audio (16kHz PCM, 1 second of silence/noise for testing)
def generate_mock_tone(freq=440, duration=1.0, rate=16000):
    import math
    import struct
    data = b""
    for i in range(int(rate * duration)):
        sample = 32767 * math.sin(2 * math.pi * freq * i / rate)
        data += struct.pack('<h', int(sample))
    return base64.b64encode(data).decode('utf-8')

MOCK_AUDIO_ACK = generate_mock_tone(880, 0.5)

class ReceptionistAgent:
    def __init__(self):
        self.settings = get_settings()
        self.ws = None
        self.url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
        self.mock_mode = self.settings.MOCK_MODE
        self.mock_queue = asyncio.Queue()
        
    async def connect(self):
        """Connect to OpenAI Realtime API or switch to Mock Mode."""
        if self.mock_mode:
            app_logger.info("Starting in MOCK MODE (Config)")
            # Queue Mock Greeting
            try:
                pcm_data = base64.b64decode(MOCK_AUDIO_ACK)
                mulaw_data = audioop.lin2ulaw(pcm_data, 2)
                mulaw_b64 = base64.b64encode(mulaw_data).decode('utf-8')
                
                await self.mock_queue.put({
                    "type": "response.audio.delta",
                    "delta": mulaw_b64,
                    "delta_pcm": MOCK_AUDIO_ACK
                })
            except Exception as e:
                app_logger.error(f"Failed to generate mock greeting: {e}")
                
            return True

        try:
            headers = {
                "Authorization": f"Bearer {self.settings.OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1"
            }
            self.ws = await websockets.connect(self.url, extra_headers=headers)
            app_logger.info("Connected to OpenAI Realtime API")
            
            # await self.initialize_session() # Moved to twilio_handler to ensure listener is active
            return True
        except Exception as e:
            app_logger.error(f"Failed to connect to OpenAI: {e}. Switching to MOCK MODE.")
            self.mock_mode = True
            diagnostics.record_error(e, "OpenAI Connection")
            return True

    async def initialize_session(self):
        if self.mock_mode:
            return

        # Configure session with Tools
        session_update = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": SYSTEM_PROMPT,
                "voice": "shimmer",
                "input_audio_format": "g711_ulaw",
                "output_audio_format": "g711_ulaw",
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 200
                },
                "tools": [
                    {
                        "type": "function",
                        "name": "send_sms",
                        "description": "Send an SMS text message to a phone number.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "phone_number": {
                                    "type": "string",
                                    "description": "The recipient's phone number (e.g., +15550001234)."
                                },
                                "message": {
                                    "type": "string",
                                    "description": "The content of the SMS message."
                                }
                            },
                            "required": ["phone_number", "message"]
                        }
                    }
                ],
                "tool_choice": "auto"
            }
        }
        await self.ws.send(json.dumps(session_update))
        
        # Trigger initial greeting
        trigger_msg = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": "The user has connected. Please say your greeting."
                    }
                ]
            }
        }
        await self.ws.send(json.dumps(trigger_msg))
        await self.ws.send(json.dumps({"type": "response.create"}))

    async def _handle_tool_call(self, call_id: str, name: str, args: dict):
        """Execute tool calls."""
        app_logger.info(f"Executing tool: {name} with args: {args}")
        
        result = "Error: Tool not found"
        
        if name == "send_sms":
            try:
                from twilio.rest import Client
                client = Client(self.settings.TWILIO_ACCOUNT_SID, self.settings.TWILIO_AUTH_TOKEN)
                
                message = client.messages.create(
                    body=args.get("message"),
                    from_=self.settings.TWILIO_PHONE_NUMBER,
                    to=args.get("phone_number")
                )
                result = f"SMS sent successfully! SID: {message.sid}"
            except Exception as e:
                app_logger.error(f"Failed to send SMS: {e}")
                result = f"Failed to send SMS: {str(e)}"
        
        # Send result back to OpenAI
        tool_output = {
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": result
            }
        }
        await self.ws.send(json.dumps(tool_output))
        
        # Trigger response to acknowledge
        await self.ws.send(json.dumps({"type": "response.create"}))

    async def send_audio(self, audio_chunk_b64: str):
        """Send mulaw audio (Twilio) directly to OpenAI."""
        if self.mock_mode:
            # Simple mock logic: echo a tone
            # We need to simulate a delay and then send a response
            # For simplicity, we just queue a tone occasionally
            # But to avoid spamming tones, we'd need VAD logic here.
            # For now, Mock Mode just acknowledges connection.
            return

        if not self.ws:
            return
            
        try:
            # OpenAI accepts base64 audio in 'input_audio_buffer.append'
            msg = {
                "type": "input_audio_buffer.append",
                "audio": audio_chunk_b64
            }
            await self.ws.send(json.dumps(msg))
        except Exception as e:
            app_logger.error(f"Error sending audio to OpenAI: {e}")
            self.mock_mode = True

    async def send_audio_pcm(self, audio_chunk_b64: str):
        """
        Send PCM audio (Web Test).
        OpenAI configured for G.711 u-law.
        We need to convert PCM -> u-law.
        """
        if self.mock_mode:
            await self.mock_queue.put({
                "type": "response.audio.delta",
                "delta_pcm": MOCK_AUDIO_ACK
            })
            return

        if not self.ws:
            return
            
        try:
            # Convert PCM -> u-law
            pcm_data = base64.b64decode(audio_chunk_b64)
            # Assume 16kHz input from web client
            mulaw_data = audioop.lin2ulaw(pcm_data, 2)
            mulaw_b64 = base64.b64encode(mulaw_data).decode('utf-8')
            
            await self.send_audio(mulaw_b64)
            
        except Exception as e:
            app_logger.error(f"Error sending PCM audio: {e}")

    async def close(self):
        if self.ws:
            await self.ws.close()

    async def receive_events(self):
        """Yield events from OpenAI or Mock Queue."""
        while True:
            if self.mock_mode:
                event = await self.mock_queue.get()
                yield event
                continue

            if not self.ws:
                await asyncio.sleep(0.1)
                continue

            try:
                app_logger.info("Waiting for WS message...")
                try:
                    # Initial timeout 5s, subsequent could be longer? 
                    # Actually realtime API sends keepalives? No.
                    # But we expect greeting immediately.
                    msg = await asyncio.wait_for(self.ws.recv(), timeout=5.0)
                except asyncio.TimeoutError:
                    if not self.mock_mode:
                        app_logger.warning("OpenAI Realtime API timed out (5s). Switching to MOCK MODE.")
                        self.mock_mode = True
                        try:
                            pcm_data = base64.b64decode(MOCK_AUDIO_ACK)
                            mulaw_data = audioop.lin2ulaw(pcm_data, 2)
                            mulaw_b64 = base64.b64encode(mulaw_data).decode('utf-8')
                            
                            await self.mock_queue.put({
                                "type": "response.audio.delta",
                                "delta": mulaw_b64,
                                "delta_pcm": MOCK_AUDIO_ACK
                            })
                        except Exception as e:
                            app_logger.error(f"Failed to queue mock greeting: {e}")
                    continue

                app_logger.info(f"Raw WS msg: {msg[:50]}...")
                event = json.loads(msg)
                
                if event["type"] == "response.audio.delta":
                    # OpenAI sends u-law (as configured)
                    mulaw_b64 = event["delta"]
                    
                    # For Web Client, we need PCM
                    mulaw_data = base64.b64decode(mulaw_b64)
                    pcm_data = audioop.ulaw2lin(mulaw_data, 2)
                    pcm_b64 = base64.b64encode(pcm_data).decode('utf-8')
                    
                    yield {
                        "type": "response.audio.delta",
                        "delta": mulaw_b64,     # For Twilio
                        "delta_pcm": pcm_b64    # For Web
                    }
                
                elif event["type"] == "response.function_call_arguments.done":
                    call_id = event["call_id"]
                    name = event["name"]
                    args = json.loads(event["arguments"])
                    
                    # Execute tool in background task to not block receiving loop
                    asyncio.create_task(self._handle_tool_call(call_id, name, args))
                
                elif event["type"] == "error":
                    app_logger.error(f"OpenAI Error: {event}")
                    
                elif event["type"] == "response.done":
                    app_logger.info(f"Response Done. Status: {event.get('response', {}).get('status')}")
                    app_logger.info(f"Response Details: {event}")
                
            except websockets.exceptions.ConnectionClosed as e:
                app_logger.warning(f"WebSocket closed: {e}. Switching to Mock Mode.")
                self.mock_mode = True
            except Exception as e:
                app_logger.error(f"Error receiving event: {e}")
                await asyncio.sleep(0.1)
