import os
import json
import functions_framework
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.auth.transport import requests
from google.cloud import secretmanager

@functions_framework.http
def renew_subscription(request):
    """
    Cloud Function to create or renew a Google Workspace Chat subscription.
    Triggered by Eventarc Pub/Sub topic on a schedule (e.g., every 2 hours).
    """
    # Recommended: Use environment variables for project-specific config
    PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "your-project-id")
    TOPIC_ID = os.environ.get("PUBSUB_TOPIC_ID", "your-topic-id")
    MONITORED_SPACES = [] # Add space IDs here (e.g., 'spaces/XXXXXXXX')

    secret_name = "projects/YOUR_PROJECT_NUMBER/secrets/YOUR_SECRET_NAME/versions/latest"
    
    scopes = [
        "https://www.googleapis.com/auth/chat.spaces",
        "https://www.googleapis.com/auth/chat.messages",
        "https://www.googleapis.com/auth/chat.memberships",
    ]

    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(name=secret_name)
    key_data = json.loads(response.payload.data.decode("utf-8"))
    
    creds = service_account.Credentials.from_service_account_info(
        key_data,
        scopes=scopes,
        subject="user@yourdomain.com",
    )
    
    auth_request = requests.Request()
    creds.refresh(auth_request)

    service = build("workspaceevents", "v1", credentials=creds, cache_discovery=False)

    for space in MONITORED_SPACES:
        space = space.strip()
        body = {
            "targetResource": f"//chat.googleapis.com/{space}",
            "eventTypes": ["google.workspace.chat.message.v1.created"],
            "notificationEndpoint": {"pubsubTopic": f"projects/{PROJECT_ID}/topics/{TOPIC_ID}"},
            "payloadOptions": {"includeResource": True}
        }
        
        try:
            service.subscriptions().create(body=body).execute()
        except Exception as e:
            # Handle existing subscription renewal (409 Conflict)
            if hasattr(e, "resp") and int(e.resp.status) == 409:
                sub_name = None
                error_details = json.loads(e.content).get("error", {}).get("details", [])
                
                for detail in error_details:
                    if detail.get("reason") == "SUBSCRIPTION_ALREADY_EXISTS":
                        sub_name = detail["metadata"]["current_subscription"]
                        break
                
                if sub_name:
                    service.subscriptions().patch(
                        name=sub_name, 
                        updateMask="ttl", 
                        body={"ttl": "0s"}
                    ).execute()

    return "Done", 200
