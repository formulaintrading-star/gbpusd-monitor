import os, json, requests, pathlib
from datetime import datetime, timedelta

API_KEY = os.environ["TWELVE_DATA_KEY"]
NTFY_TOPIC = os.environ["NTFY_TOPIC"]
THRESHOLD = float(os.environ.get("THRESHOLD_PIPS", "19.5"))
PIP = 0.0001
STATE_FILE = pathlib.Path("state.json")


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"alerted": []}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state))


def main():
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": "GBP/USD",
        "interval": "15min",
        "outputsize": 5,
        "timezone": "UTC",
        "apikey": API_KEY,
    }
    r = requests.get(url, params=params, timeout=20)
    data = r.json()
    if "values" not in data:
        print("API error:", data)
        return

    state = load_state()
    alerted = set(state.get("alerted", []))

    for bar in data["values"]:
        high = float(bar["high"])
        low = float(bar["low"])
        range_pips = (high - low) / PIP
        t = bar["datetime"]
        if range_pips >= THRESHOLD and t not in alerted:
            utc_dt = datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
            local_dt = utc_dt + timedelta(hours=3)
            local_str = local_dt.strftime("%Y-%m-%d %H:%M")
            msg = f"15m range: {range_pips:.1f} pips (threshold {THRESHOLD}) — bar closed {local_str}"
            requests.post(
                f"https://ntfy.sh/{NTFY_TOPIC}",
                data=msg.encode("utf-8"),
                headers={"Title": "Range notification", "Priority": "high", "Tags": "warning"},
                timeout=10,
            )
            alerted.add(t)
            print("Alert sent:", msg)

    state["alerted"] = list(alerted)[-50:]
    save_state(state)


if __name__ == "__main__":
    main()
