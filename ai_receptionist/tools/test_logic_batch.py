import sys
import os
import time

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.simulator import Simulator

def run_batch_test():
    print("--- Starting Logic Batch Test (Cheap-Test Mode) ---\n")
    simulator = Simulator()
    
    # Simulated Conversation Flow
    test_inputs = [
        "Hello, is anyone there?",
        "I'd like to leave a message for the owner.",
        "My name is John Doe and my number is 555-0199.",
        "Tell him his order is ready for pickup."
    ]
    
    for user_text in test_inputs:
        print(f"User: {user_text}")
        
        start = time.time()
        result = simulator.simulate_turn(user_text)
        latency = (time.time() - start) * 1000
        
        print(f"AI:   {result['response']}")
        print(f"      [Model: {result['model']} | Latency: {latency:.0f}ms]\n")

if __name__ == "__main__":
    run_batch_test()
