#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: ./set-env.sh OIDC_REDIRECT_URI"
    echo "Example: ./set-env.sh https://van-ai-guided-data-entry.apps.your-domain.com"
    exit 1
fi

OIDC_REDIRECT_URI=$1

if [ ! -f "server/.env" ]; then
    echo "Error: server/.env file not found!"
    exit 1
fi

echo "Setting environment variables for van-ai-guided-data-entry..."

# Read and set environment variables from server/.env
# Start at OIDC_ISSUER; ignore commented lines and inline comments after values
trim() {
  local s="$*"
  # trim leading
  s="${s#"${s%%[!$'\t\r\n ']*}"}"
  # trim trailing
  s="${s%"${s##*[!$'\t\r\n ']}"}"
  printf '%s' "$s"
}

processing=0
while IFS= read -r line || [[ -n "$line" ]]; do
  line="$(trim "$line")"

  # Skip empty or commented lines (handles leading spaces)
  [[ -z "$line" || "${line:0:1}" == "#" ]] && continue
  [[ "$line" != *"="* ]] && continue

  key="${line%%=*}"
  value="${line#*=}"

  key="$(trim "$key")"
  value="$(trim "$value")"

  # Strip inline comments from value (everything after '#')
  value="${value%%#*}"
  value="$(trim "$value")"

  # Start processing once we hit OIDC_ISSUER (include it)
  if [[ $processing -eq 0 && "$key" == "OIDC_ISSUER" ]]; then
    processing=1
  fi

  if [[ $processing -eq 1 && -n "$key" ]]; then
    echo "Setting $key..."
    cf set-env van-ai-guided-data-entry "$key" "$value"
  fi
done < server/.env

# Override OIDC_REDIRECT_URI with the provided argument
echo "Setting OIDC_REDIRECT_URI..."
cf set-env van-ai-guided-data-entry OIDC_REDIRECT_URI "$OIDC_REDIRECT_URI"

# Update client base URL in settings.ts based on OIDC_REDIRECT_URI and rebuild
echo "Updating client base URL from OIDC_REDIRECT_URI and rebuilding client..."

# Extract scheme://host[:port] only
BASE_URL=$(echo "$OIDC_REDIRECT_URI" | sed -E 's#^(https?://[^/]+).*#\1#')
echo "Computed BASE URL: $BASE_URL"

# Replace the PROD_API_BASE_URL line regardless of its current value
sed -i.bak -E "s|const PROD_API_BASE_URL\s*=\s*\".*\";|const PROD_API_BASE_URL = \"${BASE_URL}\";|g" client/src/data/settings.ts

if [ $? -ne 0 ]; then
  echo "Error: Failed to update client/src/data/settings.ts"
  exit 1
fi

(
  cd client && pnpm install && pnpm build
)

if [ $? -ne 0 ]; then
  echo "Error: Frontend build failed!"
  exit 1
fi

# Removed restage to match .bat behavior
echo "Environment variables set successfully and client rebuilt!"