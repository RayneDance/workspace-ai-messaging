import os
import requests
from flask import Flask, request
from google.oauth2 import service_account
from google.auth.transport.requests import Request

app = Flask(__name__)

# Configuration from Environment
KEY_PATH = os.environ.get("SERVICE_ACCOUNT_KEY_PATH", "path/to/your/service-account.json")
USER_EMAIL = os.environ.get("IMPERSONATED_USER_EMAIL", "user@yourdomain.com")
SCOPES = ["https://www.googleapis.com/auth/chat.messages.create"]

def get_auth_headers():
    """Generates DWD auth headers."""
    creds = service_account.Credentials.from_service_account_file(
        KEY_PATH, 
        scopes=SCOPES, 
        subject=USER_EMAIL
    )
    creds.refresh(Request())
    return {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json"
    }

def send_message(space_id, text, thread_id=None):
    """Sends a basic message to a Google Chat space."""
    url = f"https://chat.googleapis.com/v1/{space_id}/messages"
    
    payload = {"text": text}
    if thread_id:
        payload["thread"] = {"name": thread_id}
        
    response = requests.post(
        url, 
        headers=get_auth_headers(), 
        json=payload, 
        params={"messageReplyOption": "REPLY_MESSAGE_FALLBACK_TO_NEW_THREAD"} if thread_id else {},
        timeout=30
    )
    response.raise_for_status()
    return response.json()

"""
****** DO NOT USE THIS AS IS. YOU MUST ADD AUTHENTICATION ******
"""
@app.route("/googlechat", methods=["POST"])
def googlechat():
    """
    ****** DO NOT USE THIS AS IS. YOU MUST ADD AUTHENTICATION ******

    Endpoint mapping to receive Chat events and messages.
    """
    # NOTE: Read the message here and forward to your agent.
    # Below is a simple example:
    data = request.get_json()
    if not data:
        return "No Content", 400

    space_id = data.get("space", {}).get("name")
    message_text = data.get("message", {}).get("text")
    
    print(f"Received message in {space_id}: {message_text}")
    
    # You will need to secure this endpoint with authentication creds.
    
    # Example logic: Echo the message back
    # if space_id and message_text:
    #     send_message(space_id, f"I received: {message_text}")
    
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
