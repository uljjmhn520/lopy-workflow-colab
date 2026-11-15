import json
import os
import sys
from pathlib import Path

# Add uv cache paths to sys.path
archive = "/home/debian/.cache/uv/archive-v0"
for d in os.listdir(archive):
    p = os.path.join(archive, d)
    if os.path.isdir(p):
        sys.path.append(p)

from google_auth_oauthlib.flow import InstalledAppFlow
from colab_cli.auth import PUBLIC_SCOPES, REMOTE_REDIRECT_URI

CONFIG_PATH = Path("/home/debian/.config/colab-cli")
CONFIG_PATH.mkdir(parents=True, exist_ok=True)
TOKEN_PATH = CONFIG_PATH / "token.json"

# Inlined oauth config from colab_cli
oauth_config_file = Path("/home/debian/.cache/uv/archive-v0/pRapMiwTleK7KZWC/colab_cli/oauth_config.json")
with open(oauth_config_file, "r") as f:
    client_config = json.load(f)

flow = InstalledAppFlow.from_client_config(client_config, PUBLIC_SCOPES)
flow.redirect_uri = REMOTE_REDIRECT_URI
auth_url, _ = flow.authorization_url(prompt="consent", token_usage="remote")

print("\n>>> AUTH_URL_START")
print(auth_url)
print(">>> AUTH_URL_END\n", flush=True)

code = input("Enter the authorization code: ").strip()

flow.fetch_token(code=code)
creds = flow.credentials

with open(TOKEN_PATH, "w") as f:
    f.write(creds.to_json())

print("LOGIN_SUCCESS: Token saved to", TOKEN_PATH, flush=True)
