#!/usr/bin/env bash
# ==============================================================================
# One-Click Setup Script for Google Cloud Platform (GCP)
# Configures Cloud Run, Artifact Registry, and Service Account for GitHub Actions
# ==============================================================================
set -e

# Configuration
REGION="us-central1"
REPO_NAME="nawras-repo"
SA_NAME="github-actions-sa"
KEY_FILE="gcp-sa-key.json"

echo "🔍 Detecting active Google Cloud Project..."
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" = "(unset)" ]; then
    echo "❌ No active GCP project found. Please set your project ID:"
    echo "   gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "✅ Active Project: ${PROJECT_ID}"
echo "📍 Target Region:  ${REGION}"

# 1. Enable Required GCP APIs
echo "⚙️ Enabling necessary Google Cloud APIs (Cloud Run, Artifact Registry, IAM)..."
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    iam.googleapis.com \
    --project="${PROJECT_ID}"

# 2. Create Artifact Registry Docker Repository
echo "📦 Setting up Artifact Registry repository: ${REPO_NAME}..."
if ! gcloud artifacts repositories describe "${REPO_NAME}" --location="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud artifacts repositories create "${REPO_NAME}" \
        --repository-format=docker \
        --location="${REGION}" \
        --description="Docker repository for Nawras Market Agent" \
        --project="${PROJECT_ID}"
    echo "✅ Artifact Registry repository created."
else
    echo "ℹ️ Artifact Registry repository already exists."
fi

# 3. Create Service Account for GitHub Actions
echo "👤 Setting up Service Account: ${SA_NAME}..."
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe "${SA_EMAIL}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud iam service-accounts create "${SA_NAME}" \
        --display-name="GitHub Actions Deployer" \
        --project="${PROJECT_ID}"
    echo "✅ Service account created: ${SA_EMAIL}"
else
    echo "ℹ️ Service account already exists: ${SA_EMAIL}"
fi

# 4. Grant Required IAM Roles
echo "🔑 Granting IAM permissions to service account..."
ROLES=(
    "roles/run.admin"
    "roles/artifactregistry.writer"
    "roles/iam.serviceAccountUser"
)

for role in "${ROLES[@]}"; do
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="${role}" \
        --quiet >/dev/null
    echo "   + Granted: ${role}"
done

# 5. Generate Service Account Key for GitHub Actions
echo "🔐 Generating Service Account Key: ${KEY_FILE}..."
gcloud iam service-accounts keys create "${KEY_FILE}" \
    --iam-account="${SA_EMAIL}" \
    --project="${PROJECT_ID}"

echo ""
echo "=============================================================================="
echo "🎉 GCP SETUP COMPLETE! NEXT STEPS FOR GITHUB REPOSITORY SECRETS:"
echo "=============================================================================="
echo "1. Go to your GitHub repository: Settings -> Secrets and variables -> Actions"
echo "2. Add the following repository secrets:"
echo ""
echo "   Secret Name: GCP_PROJECT_ID"
echo "   Secret Value: ${PROJECT_ID}"
echo ""
echo "   Secret Name: GOOGLE_API_KEY"
echo "   Secret Value: <your_gemini_api_key>"
echo ""
echo "   Secret Name: GCP_SA_KEY"
echo "   Secret Value: (Copy the ENTIRE contents of the file: ${KEY_FILE})"
echo ""
echo "⚠️ Keep ${KEY_FILE} safe and DO NOT commit it to Git (it is in .gitignore)."
echo "=============================================================================="
