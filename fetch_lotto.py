import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import time

BASE_URL = "https://www.lottery.net"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
}

# ------------------------------
# Config
# ------------------------------
start_year = 2013
end_year = 2025
state = "florida"

state_games = {
    "florida": "florida"
}

draw_types = ["midday", "evening"]
picks = [3, 4]


# ------- Date parser --------
def parse_base_date(month, day, year):
    dt = datetime.strptime(f"{month} {day} {year}", "%B %d %Y")
    base_date_str = dt.strftime("%Y-%m-%d")
    return base_date_str, dt


# ------- Core scraper --------
def scrape_draws(pick, draw_type):
    out = []
    state_url = state_games[state]

    for yr in range(start_year, end_year + 1):
        url = f"{BASE_URL}/{state_url}/pick-{pick}-{draw_type}/numbers/{yr}"
        print(f"Fetching: {url}")

        resp = requests.get(url, headers=HEADERS)
        if resp.status_code != 200:
            print(f"❌ Failed for {url}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.find_all("tr")

        for row in rows:
            tds = row.find_all("td")
            if len(tds) < 2:
                continue

            # Example date text: "Wed Apr 16, 2025"
            parts = tds[0].text.strip().split()
            if len(parts) < 4:
                continue

            month, day, year = parts[1], parts[2].rstrip(","), parts[3]
            base_date_str, dt = parse_base_date(month, day, year)

            raw = tds[1].get_text(separator=" ").strip()
            digits = [int(x) for x in raw.split() if x.isdigit()]
            if len(digits) < pick:
                continue

            numbers = digits[:pick]

            out.append({
                "dt": dt,
                "date_str": f"{base_date_str} ({draw_type})",
                "slot": draw_type,
                "numbers": numbers
            })

        time.sleep(1)  # respectful delay

    out.sort(key=lambda r: r["dt"])
    return out


# ------------------------------
# Run scraper
# ------------------------------
if __name__ == "__main__":
    final_data = {
        "house": "Florida",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "history": {}
    }

    for pick in picks:
        final_data["history"][f"pick{pick}"] = {}

        for draw in draw_types:
            print(f"\n=== Scraping Pick {pick} ({draw}) ===")
            results = scrape_draws(pick, draw)
            final_data["history"][f"pick{pick}"][draw] = results

    # Save JSON
    with open("lottery_net_history.json", "w") as f:
        json.dump(final_data, f, indent=2, default=str)

    print("\n✓ Completed! Saved → lottery_net_history.json")
