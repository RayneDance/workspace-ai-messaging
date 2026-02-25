#!/bin/bash
# Setup GCP project APIs and Service Account IAM roles for Google Chat Integration

set -e

# Change these variables before running
PROJECT_ID="your-project-id"
SA_EMAIL="your-service-account@$PROJECT_ID.iam.gserviceaccount.com"

echo "Enabling necessary Google Cloud APIs..."
gcloud services enable \
  iam.googleapis.com \
  pubsub.googleapis.com \
  eventarc.googleapis.com \
  run.googleapis.com \
  cloudfunctions.googleapis.com \
  --project="$PROJECT_ID"

echo "Assigning IAM roles to Service Account: $SA_EMAIL"

# 1. Service Account Token Creator (For DWD Impersonation)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/iam.serviceAccountTokenCreator"

# 2. Pub/Sub Publisher (To route events)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/pubsub.publisher"

# 3. Eventarc Event Receiver (To receive events from Workspace)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/eventarc.eventReceiver"

# 4. Cloud Run Invoker (To allow the trigger to hit your endpoint)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/run.invoker"

# 5. Logging Log Writer (For debugging)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/logging.logWriter"

echo "Setup complete!"
