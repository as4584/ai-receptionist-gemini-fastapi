import sys
import os
import asyncio
import time

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.simulator import Simulator
from app.services.elevenlabs_service import ElevenLabsService

def main():
    print("Initializing Voice Pipeline Tester...")
    simulator = Simulator()
    voice_service = ElevenLabsService()
    
    print("\n--- Cheap-Test Mode Active ---")
    print("Type your message to simulate a conversation.")
    print("Type 'voice_test <text>' to test ElevenLabs TTS.")
    print("Type 'quit' to exit.\n")
    
    while True:
        try:
            user_input = input("User: ").strip()
            if not user_input:
                continue
                
            if user_input.lower() in ['quit', 'exit']:
                break
                
            if user_input.startswith("voice_test "):
                text_to_speak = user_input[11:]
                print(f"Testing Voice with text: '{text_to_speak}'...")
                start_time = time.time()
                try:
                    audio = voice_service.generate_audio(text_to_speak)
                    latency = (time.time() - start_time) * 1000
                    print(f"Success! Audio generated ({len(audio)} bytes) in {latency:.0f}ms")
                    # Optionally save to file
                    with open("test_voice.mp3", "wb") as f:
                        f.write(audio)
                    print("Saved to test_voice.mp3")
                except Exception as e:
                    print(f"Voice Test Failed: {e}")
                continue

            # Simulation
            start_time = time.time()
            result = simulator.simulate_turn(user_input)
            latency = (time.time() - start_time) * 1000
            
            print(f"AI ({result['model']}): {result['response']}")
            print(f"[Latency: {latency:.0f}ms | Simulated: {result['simulated']}]\n")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
