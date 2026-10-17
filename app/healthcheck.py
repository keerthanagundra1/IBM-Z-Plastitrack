"""Container health check: works whether the app serves HTTPS or HTTP."""
import ssl
import sys
import urllib.request

ctx = ssl._create_unverified_context()      # self-signed local cert; we only check liveness
for url in ("https://127.0.0.1:8501/health", "http://127.0.0.1:8501/health"):
    try:
        urllib.request.urlopen(url, context=ctx if url.startswith("https") else None, timeout=4)
        sys.exit(0)
    except Exception:
        continue
sys.exit(1)
