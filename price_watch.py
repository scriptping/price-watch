#!/usr/bin/env python3
"""price-watch: Monitor any URL for changes. Alert via ntfy.sh."""

import requests
from bs4 import BeautifulSoup
import schedule
import time
import json
import os
import sys

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "targets": [
        {
            "name": "Example",
            "url": "https://example.com",
            "selector": "h1",
        }
    ],
    "interval_min": 5,
    "ntfy_topic": "scriptping",
    "ntfy_server": "https://ntfy.sh",
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    with open(CONFIG_FILE, "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    print(f"Created {CONFIG_FILE}. Edit it, then re-run.")
    sys.exit(0)


def get_content(url, selector):
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    el = soup.select_one(selector)
    return el.text.strip() if el else None


def send_alert(cfg, name, old, new):
    msg = f"{name}: {old} → {new}"
    try:
        requests.post(
            f"{cfg['ntfy_server']}/{cfg['ntfy_topic']}",
            data=msg.encode(),
            headers={"Title": "Price Watch", "Priority": "high"},
            timeout=10,
        )
        print(f"[ALERT] {msg}")
    except Exception as e:
        print(f"[ERROR] ntfy: {e}")


def check_all(cfg):
    for t in cfg["targets"]:
        try:
            val = get_content(t["url"], t["selector"])
            if val is None:
                print(f"[SKIP] {t['name']}: selector not found")
                continue
            prev = t.get("last_value")
            if prev is None:
                t["last_value"] = val
                print(f"[INIT] {t['name']}: {val}")
            elif val != prev:
                send_alert(cfg, t["name"], prev, val)
                t["last_value"] = val
            else:
                print(f"[OK]   {t['name']}: {val}")
        except Exception as e:
            print(f"[ERR]  {t['name']}: {e}")


def main():
    cfg = load_config()
    interval = cfg["interval_min"]
    print(f"price-watch: {len(cfg['targets'])} target(s), every {interval} min")
    print(f"Alerts → {cfg['ntfy_server']}/{cfg['ntfy_topic']}")
    print("Ctrl+C to stop\n")
    check_all(cfg)
    schedule.every(interval).minutes.do(lambda: check_all(cfg))
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
