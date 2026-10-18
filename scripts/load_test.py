import argparse
import json
import math
import secrets
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener


def run(base: str, requests: int, workers: int) -> dict:
    opener = build_opener(HTTPCookieProcessor(CookieJar()))

    def call(path, data=None, token="", client=opener):
        body = None if data is None else json.dumps(data).encode()
        req = Request(base + path, data=body, headers={
            "Content-Type": "application/json", "X-CSRFToken": token,
        })
        with client.open(req, timeout=20) as response:
            return json.load(response)

    token = call("/api/session/")["csrfToken"]
    username = "load_" + secrets.token_hex(5)
    password = secrets.token_urlsafe(24)
    token = call("/api/register/", {
        "username": username, "password1": password, "password2": password,
    }, token)["csrfToken"]
    category = call("/api/categories/",
                    {"name": "Load", "limit": "10000"}, token)
    for i in range(20):
        call("/api/transactions/", {
            "category": category["id"], "amount": "12.34", "type": "expense",
            "date": "2026-10-18", "description": f"Load {i}",
        }, token)
    cookie_header = "; ".join(
        f"{c.name}={c.value}" for handler in opener.handlers
        if isinstance(handler, HTTPCookieProcessor) for c in handler.cookiejar
    )

    def request_one(i):
        start = time.perf_counter()
        path = ("/api/summary/?month=2026-10" if i % 2 == 0
                else "/api/transactions/?month=2026-10")
        client = build_opener()
        req = Request(base + path, headers={"Cookie": cookie_header})
        try:
            with client.open(req, timeout=20) as response:
                data = json.load(response)
                valid = (data.get("expense") == "246.80" if i % 2 == 0
                         else data.get("count") == 20)
                success = response.status == 200 and valid
        except (HTTPError, OSError, ValueError):
            success = False
        return (time.perf_counter() - start) * 1000, success

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(request_one, range(requests)))
    elapsed = time.perf_counter() - start
    timings = sorted(r[0] for r in results)
    return {
        "requests": requests, "workers": workers,
        "errors": sum(not r[1] for r in results),
        "seconds": round(elapsed, 3), "rps": round(requests / elapsed, 2),
        "median_ms": round(statistics.median(timings), 2),
        "p95_ms": round(timings[math.ceil(len(timings) * .95) - 1], 2),
        "account": username,
        "scenario": "20 writes; concurrent summary/history reads",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.requests < 1 or not 1 <= args.workers <= 32:
        parser.error("requests must be positive; workers must be 1..32")
    result = run(args.url.rstrip("/"), args.requests, args.workers)
    report = json.dumps(result, indent=2, ensure_ascii=False)
    print(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report + "\n", encoding="utf-8")
    raise SystemExit(1 if result["errors"] else 0)
