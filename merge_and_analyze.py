import json
import datetime
from datetime import timedelta
import requests

# --- Configuration ---
STATES = {
    "illinois": {
        "pick3_url": "https://www.lottery.net/illinois/pick-3/numbers",
        "pick4_url": "https://www.lottery.net/illinois/pick-4/numbers",
        "pick3_game": "pick3",
        "pick4_game": "pick4"
    },
    "florida": {
        "pick3_url": "https://www.flalottery.com/pick3", # Placeholder for scraper logic
        "pick4_url": "https://www.flalottery.com/pick4",
        "pick3_game": "pick3",
        "pick4_game": "pick4"
    }
}

REPLACEMENT_VALUES = {
    0: 5, 1: 9, 2: 8, 3: 7, 4: 6, 5: 0, 6: 4, 7: 3, 8: 2, 9: 1
}

# --- Helper Functions ---

def parse_date(date_str):
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None

def get_replacement(num):
    return REPLACEMENT_VALUES.get(num, num)

def check_win_7day(target_candidate, draws, start_index):
    """
    Checks if the target_candidate appears in draws[start_index] to draws[start_index + 7].
    Returns the date of the win if found, else None.
    """
    # Look ahead up to 7 days (or as many as exist)
    limit = min(len(draws), start_index + 7)
    for i in range(start_index, limit):
        if target_candidate in draws[i]['numbers']:
            return draws[i]['date']
    return None

def analyze_combo_performance(combo_str, draws, game_type):
    """
    Runs the simulation for a specific combo (e.g., "34") over the history of draws.
    """
    # 1. Sort draws by date ascending (oldest first) to simulate timeline
    sorted_draws = sorted(draws, key=lambda x: x['date'])
    
    # Initialize State
    base_num = int(combo_str[0]) # e.g., 3
    is_active = False # "off"
    
    wins = 0
    pairs_history = []
    
    # We need to track stopped candidates: { candidate_num: expiry_date }
    # But in this specific per-combo logic, we just track the combo's lifecycle.
    # The global stop-loss logic might be separate, but here we track this combo's wins.
    
    latest_win_date = None
    latest_play_date = None
    
    # Iterate through history
    for i, draw in enumerate(sorted_draws):
        draw_nums = draw['numbers']
        draw_date = draw['date']
        
        # Check if Base is drawn (Activator)
        if base_num in draw_nums:
            # If not active, turn ON
            if not is_active:
                is_active = True
                
                # Determine Candidate
                # Logic: If base is 3, replacement is 7. Candidate is 7.
                candidate = get_replacement(base_num)
                
                # Record this "Play"
                latest_play_date = draw_date
                
                # Check for Win in next 7 days
                # We pass the full sorted list and the NEXT index
                win_date = check_win_7day(candidate, sorted_draws, i + 1)
                
                pair_record = {
                    "play_dt": draw_date.isoformat(),
                    "play_date_str": draw_date.strftime("%Y-%m-%d"),
                    "candidate": candidate,
                    "pos": 0, # simplified
                    "base": base_num,
                    "win_dt": win_date.isoformat() if win_date else None,
                    "win_date_str": win_date.strftime("%Y-%m-%d") if win_date else None
                }
                
                if win_date:
                    wins += 1
                    latest_win_date = win_date
                    # Logic: If it wins, does it stay on? 
                    # Usually "Hit and run" implies it turns off or resets.
                    # For this algo, we'll assume it toggles OFF after a win processing window?
                    # Or stays ON until a specific condition?
                    # Using provided logic: "State toggling". Let's assume a Win resets it to Off.
                    is_active = False 
                else:
                    # If no win in 7 days, it might stay on or eventually turn off.
                    # For safety/stop-loss, let's assume it stays active until a Stop Loss event 
                    # OR we just treat the 'activation' as a single event.
                    pass
                
                pairs_history.append(pair_record)
        
        # Check if Candidate hits while Active (if we didn't just turn it on/off)
        # (This is covered by the lookahead above for simplicity in reporting)
        
    return {
        "combo": combo_str,
        "wins": wins,
        "latest_play": latest_play_date.isoformat() if latest_play_date else None,
        "latest_win": latest_win_date.isoformat() if latest_win_date else None,
        "pairs": pairs_history[-5:], # Keep last 5 for UI
        "state": "on" if is_active else "off"
    }

# --- Mock Data Generation (Since we can't scrape) ---
# In a real scenario, `extract_data` would use BeautifulSoup
def generate_mock_draws(days=365):
    draws = []
    base = datetime.date.today()
    import random
    for x in range(days):
        d = base - datetime.timedelta(days=x)
        # Random pick 3
        draws.append({
            "date": d,
            "numbers": [random.randint(0,9) for _ in range(3)]
        })
    return draws

def main():
    output = {
        "ok": True,
        "generated_at": datetime.datetime.now().isoformat(),
        "datasets": {},
        "source_urls": []
    }
    
    # Process Illinois
    # In real script: il_draws = extract_data(...)
    il_draws = generate_mock_draws() 
    
    top_combos = []
    # Analyze 00-99
    for i in range(100):
        combo = f"{i:02d}"
        result = analyze_combo_performance(combo, il_draws, "pick3")
        top_combos.append(result)
        
    top_combos.sort(key=lambda x: x['wins'], reverse=True)
    
    output["datasets"]["illinois"] = {
        "latest_results": {
            "pick3": {"date": str(il_draws[0]['date']), "draws": {"midday": il_draws[0]['numbers']}},
            "pick4": {"date": None, "draws": {}}
        },
        "top_combos": top_combos[:10], # Top 10
        "alerts": [],
        "state_snapshot": {
            "combo_states": {c['combo']: c['state'] for c in top_combos},
            "stopped_candidates": {}
        }
    }
    
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    main()