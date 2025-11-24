import json
import requests
import subprocess
import os
from datetime import datetime

# ------------------------------------------------------
# Configuration: Google AI Studio Endpoint + API Key
# ------------------------------------------------------

GOOGLE_AI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # export GOOGLE_API_KEY="xxxxx"

# ------------------------------------------------------
# Helper: Run Your Existing Analyzer
# ------------------------------------------------------

def run_merge_and_analyze():
    print("Running merge_and_analyze.py ...")
    result = subprocess.run(
        ["python3", "merge_and_analyze.py"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("Error running merge_and_analyze.py")
        print(result.stderr)
        return None
    
    try:
        return json.loads(result.stdout)
    except Exception as e:
        print("JSON parse error:", e)
        return None

# ------------------------------------------------------
# Helper: Load Illinois + Florida Full History
# ------------------------------------------------------

def load_history():
    if not os.path.exists("lottery_net_history.json"):
        print("History file not found: lottery_net_history.json")
        return {}

    with open("lottery_net_history.json", "r") as f:
        return json.load(f)

# ------------------------------------------------------
# Helper: Send to Google AI Studio
# ------------------------------------------------------

def send_to_google_studio(data):
    print("Sending data to Google AI Studio...")

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": "Incoming data package from Lotto System:\n\n" +
                                json.dumps(data, indent=2)
                    }
                ]
            }
        ]
    }

    url = f"{GOOGLE_AI_URL}?key={GOOGLE_API_KEY}"
    response = requests.post(url, headers=headers, json=payload)
AIzaSyAK8aWK4jSwqjUEgwWmwPtOjrLo_MnX89E
    print("Google AI Response:")
    print(response.text)

# ------------------------------------------------------
# Main
# ------------------------------------------------------

def main():
    print("\n=== Lotto → Google AI Studio Pipeline ===\n")

    # 1. Get analyzer output
    analysis_data = run_merge_and_analyze()
    if not analysis_data:
        return

    # 2. Load history
    history_data = load_history()

    # 3. Build payload
    outgoing_package = {
        "sent_at": datetime.now().isoformat(),
        "analysis": analysis_data,
        "history": history_data
    }

    # 4. Send to Google AI Studio
    send_to_google_studio(outgoing_package)

    print("\nPackage successfully sent.\n")


if __name__ == "__main__":
    main()
