import os
import json
import time
import random
import signal
import sys
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

# --- Configuration ---
BASE_URL = "https://www.lottery.net/illinois"
RAW_DATA_FILE = "illinois_history_raw.json"
FRONTEND_DATA_FILE = "lotto_data.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.google.com/"
}

# --- Global Flag for Graceful Exit ---
KEEP_RUNNING = True

def signal_handler(sig, frame):
    """Handles Ctrl+C to stop the loop gracefully."""
    global KEEP_RUNNING
    print("\n[!] Ctrl+C detected. Stopping after current fetch and saving data...")
    KEEP_RUNNING = False

# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)

# --- Part 1: Fetching Logic ---

def fetch_il_draw(date_str, pick=3, draw_type="midday"):
    """Fetches numbers for a specific date/game."""
    url = f"{BASE_URL}/pick-{pick}-{draw_type}/numbers/{date_str}"
    
    try:
        # Random sleep to act like a human
        time.sleep(random.uniform(0.5, 1.5))
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[ERROR] Failed fetching {url}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # TARGET SPECIFIC HTML STRUCTURE
    # Look for <ul class="illinois results pick-3-midday">
    target_class_part = f"pick-{pick}-{draw_type}"
    
    # We use a lambda to find a ul that contains "illinois", "results", and the specific game type
    ul = soup.find("ul", class_=lambda x: x and "illinois" in x and "results" in x and target_class_part in x)

    if not ul:
        # print(f"[WARN] No results found on page {url}")
        return None

    numbers = []
    # Only find <li class="ball"> to avoid "fireball" or other elements
    for li in ul.find_all("li", class_="ball"):
        text = li.get_text(strip=True)
        if text.isdigit():
            numbers.append(int(text))

    # Validate count
    if len(numbers) < pick:
        return None

    # Return only the required amount of numbers (just in case)
    result = numbers[:pick]
    print(f"   -> Found: {result}")
    return result

def load_raw_data():
    """Safely loads the raw history file."""
    if os.path.exists(RAW_DATA_FILE):
        try:
            with open(RAW_DATA_FILE, "r") as f:
                data = json.load(f)
            if isinstance(data, list):
                print("[FIX] Found list in JSON, resetting to dict.")
                return {}
            return data
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}

def save_raw_data(data):
    with open(RAW_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def fetch_il_history(start_year=2024, end_year=2025):
    """Iterates through dates and fills gaps."""
    global KEEP_RUNNING
    data = load_raw_data()

    # Initialize keys if missing
    if "pick3" not in data: data["pick3"] = {}
    if "pick4" not in data: data["pick4"] = {}

    today = datetime.now()

    for year in range(start_year, end_year + 1):
        if not KEEP_RUNNING: break
        
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31)
        current_date = start_date

        while current_date <= end_date and current_date <= today:
            if not KEEP_RUNNING: break

            date_str = current_date.strftime("%m-%d-%Y")

            # --- Pick 3 ---
            if date_str not in data["pick3"]:
                data["pick3"][date_str] = {}

            # Midday
            if "midday" not in data["pick3"][date_str]:
                print(f"Fetching Pick 3 Midday: {date_str}...", end="")
                nums = fetch_il_draw(date_str, 3, "midday")
                if nums: data["pick3"][date_str]["midday"] = nums
                else: print(" No data.")

            # Evening
            if "evening" not in data["pick3"][date_str]:
                print(f"Fetching Pick 3 Evening: {date_str}...", end="")
                nums = fetch_il_draw(date_str, 3, "evening")
                if nums: data["pick3"][date_str]["evening"] = nums
                else: print(" No data.")

            # --- Pick 4 ---
            if date_str not in data["pick4"]:
                data["pick4"][date_str] = {}

            # Midday
            if "midday" not in data["pick4"][date_str]:
                print(f"Fetching Pick 4 Midday: {date_str}...", end="")
                nums = fetch_il_draw(date_str, 4, "midday")
                if nums: data["pick4"][date_str]["midday"] = nums
                else: print(" No data.")

            # Evening
            if "evening" not in data["pick4"][date_str]:
                print(f"Fetching Pick 4 Evening: {date_str}...", end="")
                nums = fetch_il_draw(date_str, 4, "evening")
                if nums: data["pick4"][date_str]["evening"] = nums
                else: print(" No data.")

            # Save periodically
            if current_date.day % 5 == 0:
                save_raw_data(data)

            current_date += timedelta(days=1)

    # Final save before exiting
    save_raw_data(data)
    return data

# --- Part 2: Analysis & Frontend Generation ---

def calculate_stats(raw_data):
    """Converts raw date-keyed data into the format App.tsx expects."""
    
    # Sort dates desc
    sorted_dates_p3 = sorted(raw_data.get("pick3", {}).keys(), key=lambda x: datetime.strptime(x, "%m-%d-%Y"), reverse=True)
    latest_p3_date = sorted_dates_p3[0] if sorted_dates_p3 else None
    latest_p3_draw = raw_data["pick3"].get(latest_p3_date, {}) if latest_p3_date else {}

    sorted_dates_p4 = sorted(raw_data.get("pick4", {}).keys(), key=lambda x: datetime.strptime(x, "%m-%d-%Y"), reverse=True)
    latest_p4_date = sorted_dates_p4[0] if sorted_dates_p4 else None
    latest_p4_draw = raw_data["pick4"].get(latest_p4_date, {}) if latest_p4_date else {}

    # Logic for "Top Combos" (Mock logic based on frequency of first 2 digits)
    combos_counts = {}
    
    # Analyze last 60 draws for hot combos
    for d_str in sorted_dates_p3[:60]:
        draw = raw_data["pick3"][d_str]
        for t in ["midday", "evening"]:
            if t in draw:
                nums = draw[t]
                if len(nums) >= 2:
                    # Simple strategy: pair the first two numbers
                    key = f"{nums[0]}{nums[1]}"
                    combos_counts[key] = combos_counts.get(key, 0) + 1

    top_combos = []
    for k, v in sorted(combos_counts.items(), key=lambda item: item[1], reverse=True)[:5]:
        top_combos.append({
            "combo": k,
            "wins": v,
            "latest_play": datetime.now().isoformat(),
            "pairs": [],
            "state": "on" if v > 2 else "off"
        })

    # Construct Final JSON
    frontend_data = {
        "ok": True,
        "generated_at": datetime.now().isoformat(),
        "house": "Illinois", 
        "latest_results": {
            "pick3": {
                "date": latest_p3_date,
                "draws": latest_p3_draw
            },
            "pick4": {
                "date": latest_p4_date,
                "draws": latest_p4_draw
            }
        },
        "source_urls": [
            {"name": "Illinois Lottery Official", "url": "https://www.lottery.net/illinois"}
        ],
        "top_combos": top_combos,
        "alerts": [
            # Mock alerts to populate UI if real logic isn't ready
            {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "combo": "00",
                "candidate": 7,
                "action": "play",
                "source": "Pick3",
                "result": "Pending"
            }
        ],
        "state_snapshot": {
            "combo_states": {k: "on" for k in combos_counts.keys()},
            "stopped_candidates": {}
        }
    }
    return frontend_data

if __name__ == "__main__":
    print("--- Catalyst Engine: Illinois Module ---")
    print("Press Ctrl+C at any time to stop safely.")

    # 1. Fetch History
    print("Step 1: Updating History...")
    # Adjust years as needed
    raw_data = fetch_il_history(start_year=2024, end_year=2025)

    # 2. Generate Frontend Data
    print("\nStep 2: Analyzing & Formatting...")
    final_json = calculate_stats(raw_data)

    # 3. Save for App
    with open(FRONTEND_DATA_FILE, "w") as f:
        json.dump(final_json, f, indent=2)

    print(f"SUCCESS: Data saved to {FRONTEND_DATA_FILE}")