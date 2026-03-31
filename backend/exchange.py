import os
import requests
from dotenv import load_dotenv, set_key

# Load your existing .env
load_dotenv(".env")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRETE")
REDIRECT_URI = "http://localhost"  # Must match what you used to generate the code
AUTH_CODE = "<Completed>"  # Last edited 30-03-2026

# Exchange authorization code for tokens
token_url = "https://oauth2.googleapis.com/token"
data = {
    "code": AUTH_CODE,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "redirect_uri": REDIRECT_URI,
    "grant_type": "authorization_code"
}

response = requests.post(token_url, data=data)
tokens = response.json()

if "error" in tokens:
    print("Error fetching tokens:", tokens)
else:
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    expires_in = tokens.get("expires_in")

    print("Access Token:", access_token)
    print("Refresh Token:", refresh_token)
    print("Expires in (seconds):", expires_in)

    # Optional: save to .env for your FastAPI project
    set_key(".env", "ACCESS_TOKEN", access_token)
    set_key(".env", "REFRESH_TOKEN", refresh_token)
    print("Tokens saved to .env")