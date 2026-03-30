import os
import webbrowser
from urllib.parse import urlencode
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(".env")

CLIENT_ID = os.getenv("CLIENT_ID")
SCOPE = "https://www.googleapis.com/auth/gmail.send"
REDIRECT_URI = "http://localhost"  # For desktop apps

# -----------------------------
# Step 1: Generate authorization URL
# -----------------------------
params = {
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "scope": SCOPE,
    "response_type": "code",
    "access_type": "offline",  # ensures you get a refresh token
    "prompt": "consent"        # forces refresh token even if previously authorized
}

auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)

print("\n=== Gmail API Authorization ===")
print("1. Open this URL in your browser and sign in with your Gmail account:")
print(auth_url)

# Automatically open the URL in default browser
try:
    webbrowser.open(auth_url)
except:
    pass

print("\n2. After signing in and allowing access, you will be redirected to a URL like:")
print("   http://localhost/?code=YOUR_AUTH_CODE&scope=https://www.googleapis.com/auth/gmail.send")
print("\n3. Copy the value of 'code' from the URL and use it in your exchange.py script to get tokens.")