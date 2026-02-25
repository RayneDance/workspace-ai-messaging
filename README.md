# Reliable AI Integration into Google Workspace Chat

If you’ve spent any time trying to get an LLM to reliably read messages in Google Workspace Chat, you know the struggle. Between hallucinated API features and documentation that seems to lead in circles, the "simple" task of message delivery is anything but.

I’ve spent the time in the trenches fighting with Gemini and Workspace permissions so you don't have to. Here is the architecture for a reliable, general-purpose AI integration that actually hears what’s happening in the room.

## The Architecture

To get this running, you need a specific stack of Google Cloud and Workspace components. Think of this as your "shopping list" for the build:

- **Cloud Run**: Your LLM interface hosting a `/googlechat` endpoint to receive events.
- **Service Account**: To handle backend authentication.
- **Licensed User**: A full Workspace user account for Domain-Wide Delegation (DWD) impersonation.
- **Cloud Scheduler**: A cron job to keep the lights on.
- **Pub/Sub & Eventarc**: The plumbing that routes events to your application.
- **Cloud Function**: Called by Eventarc to actually manage subscriptions.

### The "Big Catch" with Google Chat

Here is the hurdle that trips most developers up: By default, Google Chat apps are "deaf." They only receive events if they are directly messaged or explicitly @tagged.

If you want to build a personified AI that acts as a general-purpose participant, a standard Chat App won’t cut it. To make the AI "hear" every message:

1. Your application must subscribe to Workspace events.
2. Crucially, the application must **impersonate a licensed user via DWD** during that subscription process.

Once the application is acting on behalf of a user, the floodgates open, and Chat events begin to flow down through Pub/Sub and Eventarc.

### The Refresh Loop

Workspace subscriptions aren't "set it and forget it." At the time of writing, the default timeout is **4 hours**.

If you don’t refresh, your AI goes deaf again. You’ll need to set up your Cloud Scheduler (cron) to trigger a refresh logic within that window. I recommend setting your own timeout slightly shorter than the 4-hour mark (e.g., 2 hours) to ensure zero downtime in message delivery.

---

## The Setup

### 1. Project Setup
I strongly recommend isolating this integration within its own dedicated Google Cloud project.

1. Create a new Google Cloud project.
2. Navigate to the **IAM & Admin console** and create a **Service Account**. This account will act as the identity for your integration, and you will eventually use it for Domain-Wide Delegation.
3. Create an API key for your Service Account and download the file.
4. Add the file content to a **Secret Manager** secret. Keep the secret name handy for later.
5. Record the unique ID (Client ID) of the Service Account from its details page for the DWD step later.

### 2. Enabling APIs & Permissions
With your project and Service Account ready, you’ll need to enable the necessary Google Cloud services and assign roles.

> **Example Script**: Review and run [`scripts/setup_gcp.sh`](scripts/setup_gcp.sh) to automate API enabling and policy binding. Be sure to update the environment variables `PROJECT_ID` and `SA_EMAIL` inside the script before running!

### 3. Domain-Wide Delegation (DWD)
Next, we need to allow our user account to be accessed via API calls.

1. Go to your [Google Admin Console](https://admin.google.com/) and click **Security** -> **Access & Data Controls** -> **API Controls**.
2. At the bottom of the right column, click **Manage Domain Wide Delegation**.
3. Click **Add New**.
4. The **Client ID** will be the unique ID of your service account.
5. For **OAuth scopes**, add the following minimum recommended scopes (comma separated):
   ```text
   https://www.googleapis.com/auth/chat.spaces,
   https://www.googleapis.com/auth/chat.messages,
   https://www.googleapis.com/auth/chat.memberships,
   https://www.googleapis.com/auth/workspace.events.subscription.readonly
   ```
   *Note: If you want to access other services like Calendar events, add those scopes here too. The full URL is required. Give it 15+ minutes to propagate.*

### 4. The Pub/Sub Communications Channel
We need a way for Chat events/messages to reach our bot.

1. Go to **Pub/Sub** and setup a primary topic, for example `chat-events`.
2. Setup a **Push** subscription to this topic to eventually route messages to your Cloud Run bot endpoint.
3. Setup another topic to trigger the renewal timer, named something like `subscription-message`.

### 5. The Timer (Cloud Scheduler)
We need something to kick off a subscription refresh every so often (e.g., every 2 hours).

1. Create a **Cloud Scheduler job**.
2. Give it a memorable name, set the timezone, and use the cron string `* */2 * * *` (every 2 hours).
3. Under "Configure the execution" select **Pub/Sub**.
4. Select the topic you created for renewals (`subscription-message`).
5. For the message body, add something small like `/`.
6. Click **Create** to establish your baseline refresh rate.

### 6. The Cloud Function Subscription Manager
Now we need to create a Cloud Function that will handle the logic of actually subscribing and renewing subscriptions.

1. Go to **Cloud Run/Cloud Functions** and start writing a new Python (or your preferred language) function.
2. Disable public networking for the function.
3. Your trigger will be the Eventarc Pub/Sub topic created for renewals (`subscription-message`).

> **Example Script**: See the complete implementation at [`scripts/renew_subscription.py`](scripts/renew_subscription.py) to map to your Cloud Function. Update values like `MONITORED_SPACES` and `secret_name` accordingly.
>
> **Critical implementation detail:** AI will often attempt to perform API calls with just loaded credentials. A `creds.refresh(auth_request)` call must be executed to obtain the proper token required by the OAuth2 flow before making the Workspace Events request. Check the script to see how this operates!

### 7. Reading/Writing from Google Workspace Chat (Cloud Run App)
Now we need to set up our app to serve as the endpoint for receiving Chat Events and replying.

1. Set up a **Cloud Run Service**. You'll need an application like Flask with a route mapping to `/googlechat`.
2. Set your Pub/Sub `chat-events` Push-subscription to hit this Cloud Run endpoint. **Secure your endpoint properly!**

> **Example Script**: See [`scripts/example_app.py`](scripts/example_app.py) for a boilerplate application template. This script demonstrates how to set up the DWD authentication headers and implements an endpoint to receive messages, along with helper logic for sending basic fallback replies to threads.
