"""Check the published Netlify bundle, ngrok API and CORS from the public origin."""
import json
import re
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SITE = "https://stellar-basbousa-cee41b.netlify.app"


def get(url: str, headers: dict | None = None, method: str = "GET"):
    request = Request(url, headers=headers or {}, method=method)
    try:
        with urlopen(request, timeout=15) as response:
            return response.status, response.headers, response.read()
    except HTTPError as exc:
        return exc.code, exc.headers, exc.read()


status, _, body = get(SITE + "/")
assert status == 200
index = body.decode("utf-8")
assets = re.findall(r'(?:src|href)="([^"]+\.(?:js|css))"', index)
assert any(asset.startswith("main-") for asset in assets)
for asset in assets:
    status, _, data = get(SITE + "/" + asset)
    print("asset", asset, status, len(data))
    assert status == 200, f"Public asset failed: {asset}"
config_status, _, config_bytes = get(SITE + "/config.json")
assert config_status == 200
config = json.loads(config_bytes)
assert config["mode"] == "api"
base = config["apiUrl"].rstrip("/")
window = urlencode({"start": "2026-11-17T12:00:00+00:00", "end": "2026-11-17T23:00:00+00:00", "mode": "live"})
for path in ("/api/salud", "/api/eventos", "/api/estadisticas"):
    suffix = "" if path == "/api/salud" else "?" + window
    status, headers, data = get(base + path + suffix, {"Origin": SITE, "ngrok-skip-browser-warning": "1"})
    assert status == 200 and headers.get("access-control-allow-origin") == SITE, (path, status)
    print("api", path, status, len(data))
for path in ("/api/eventos", "/api/estadisticas"):
    status, headers, _ = get(base + path, {"Origin": SITE, "Access-Control-Request-Method": "GET",
                                          "Access-Control-Request-Headers": "ngrok-skip-browser-warning"}, "OPTIONS")
    assert status == 200 and headers.get("access-control-allow-origin") == SITE, (path, status)
    print("cors", path, status)
print("Public deployment HTTP checks passed")
