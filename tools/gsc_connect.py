#!/usr/bin/env python3
"""One-time setup that connects nularo.com to Google Search Console.

Run locally (never in CI), with the Desktop OAuth client JSON downloaded
from Google Cloud Console:

  python3 tools/gsc_connect.py login ~/Downloads/client_secret_*.json
      Opens the browser for consent, stores credentials in
      ~/.config/nularo-gsc/creds.json (outside the repo, mode 600).
  python3 tools/gsc_connect.py token
      Asks Google for the HTML verification file and writes it to the
      repo root. Commit and push it, wait for Pages to deploy, then:
  python3 tools/gsc_connect.py verify
      Verifies ownership, adds the property to Search Console and
      submits the sitemap.
  python3 tools/gsc_connect.py secrets
      Copies the credentials into the repo's GitHub Actions secrets
      (via gh, values sent on stdin, never printed).

Stdlib only. Everything here is free.
"""

import http.server
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://nularo.com/"
REPO = "creature-hq/nularo-site"
CREDS = Path.home() / ".config" / "nularo-gsc" / "creds.json"
SCOPES = [
    "https://www.googleapis.com/auth/webmasters",
    "https://www.googleapis.com/auth/siteverification",
]


def call(method, url, access, body=None):
    req = urllib.request.Request(
        url,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {access}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {url} failed: {e.code} {e.read().decode()[:500]}")


def load():
    if not CREDS.exists():
        sys.exit("run `login` first")
    return json.loads(CREDS.read_text())


def access_token(c):
    data = urllib.parse.urlencode(
        {
            "client_id": c["client_id"],
            "client_secret": c["client_secret"],
            "refresh_token": c["refresh_token"],
            "grant_type": "refresh_token",
        }
    ).encode()
    with urllib.request.urlopen("https://oauth2.googleapis.com/token", data) as r:
        return json.load(r)["access_token"]


def login(client_file):
    client = json.loads(Path(client_file).expanduser().read_text())
    client = client.get("installed") or client.get("web")
    got = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Connected. You can close this tab.</h2>")

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    redirect = f"http://127.0.0.1:{srv.server_port}"
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(
        {
            "client_id": client["client_id"],
            "redirect_uri": redirect,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",
            "prompt": "consent",
        }
    )
    print("Opening Google sign-in in your browser...")
    subprocess.run(["open", url])
    while "code" not in got and "error" not in got:
        srv.handle_request()
    if "error" in got:
        sys.exit(f"Google returned: {got['error']}")
    data = urllib.parse.urlencode(
        {
            "code": got["code"],
            "client_id": client["client_id"],
            "client_secret": client["client_secret"],
            "redirect_uri": redirect,
            "grant_type": "authorization_code",
        }
    ).encode()
    with urllib.request.urlopen("https://oauth2.googleapis.com/token", data) as r:
        tok = json.load(r)
    if "refresh_token" not in tok:
        sys.exit("no refresh token came back; rerun login")
    CREDS.parent.mkdir(parents=True, exist_ok=True)
    CREDS.write_text(
        json.dumps(
            {
                "client_id": client["client_id"],
                "client_secret": client["client_secret"],
                "refresh_token": tok["refresh_token"],
            }
        )
    )
    CREDS.chmod(0o600)
    print(f"saved credentials to {CREDS}")


def token():
    access = access_token(load())
    r = call(
        "POST",
        "https://www.googleapis.com/siteVerification/v1/token",
        access,
        {"site": {"type": "SITE", "identifier": SITE}, "verificationMethod": "FILE"},
    )
    name = r["token"]
    (ROOT / name).write_text(f"google-site-verification: {name}")
    print(f"wrote {name}; commit, push, wait for Pages, then run `verify`")


def verify():
    access = access_token(load())
    call(
        "POST",
        "https://www.googleapis.com/siteVerification/v1/webResource?verificationMethod=FILE",
        access,
        {"site": {"type": "SITE", "identifier": SITE}},
    )
    print("ownership verified")
    enc = urllib.parse.quote(SITE, safe="")
    call("PUT", f"https://www.googleapis.com/webmasters/v3/sites/{enc}", access)
    print("property added to Search Console")
    sm = urllib.parse.quote(SITE + "sitemap.xml", safe="")
    call("PUT", f"https://www.googleapis.com/webmasters/v3/sites/{enc}/sitemaps/{sm}", access)
    print("sitemap submitted")


def secrets():
    c = load()
    for name, value in (
        ("GSC_CLIENT_ID", c["client_id"]),
        ("GSC_CLIENT_SECRET", c["client_secret"]),
        ("GSC_REFRESH_TOKEN", c["refresh_token"]),
        ("GSC_SITE", SITE),
    ):
        subprocess.run(["gh", "secret", "set", name, "--repo", REPO], input=value.encode(), check=True)
    print("GitHub Actions secrets set")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "login" and len(sys.argv) == 3:
        login(sys.argv[2])
    elif cmd in ("token", "verify", "secrets"):
        globals()[cmd]()
    else:
        sys.exit(__doc__)
