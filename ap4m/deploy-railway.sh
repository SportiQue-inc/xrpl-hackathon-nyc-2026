#!/usr/bin/env bash
# Put the AP4M rail on Railway and switch the vault to it. Run from a clone that is linked to the Railway project:
#   ap4m/deploy-railway.sh [path to ap4m/.env with the keys]
# Key values are read from the .env file into Railway variables and never printed.
set -euo pipefail
cd "$(dirname "$0")/.."
ENV_FILE="${1:-$HOME/Developer/xrpl-ap4m/ap4m/.env}"
VAULT_SERVICE="${VAULT_SERVICE:-04899e89-a301-4446-b54b-b96e71dfbd32}"
RAIL=ap4m-rail
TOKEN_FILE="$HOME/.ap4m/rail.token"

v() { grep -E "^$1=" "$ENV_FILE" | tail -1 | cut -d= -f2- | sed -E "s/^['\"]//; s/['\"]$//"; }
for name in AGENT_PRIVATE_KEY MERCHANT_SUBMITTER_KEY MERCHANT_ID MERCHANT_PAYOUT; do
  [ -n "$(v "$name")" ] || { echo "$ENV_FILE has no $name" >&2; exit 1; }
done
mkdir -p "$HOME/.ap4m" && chmod 700 "$HOME/.ap4m"
[ -s "$TOKEN_FILE" ] || (umask 077 && openssl rand -hex 24 >"$TOKEN_FILE")
TOKEN="$(cat "$TOKEN_FILE")"

railway add --service "$RAIL" >/dev/null 2>&1 || true          # already there on a re-run
railway variables --service "$RAIL" --skip-deploys \
  --set "AGENT_PRIVATE_KEY=$(v AGENT_PRIVATE_KEY)" \
  --set "MERCHANT_SUBMITTER_KEY=$(v MERCHANT_SUBMITTER_KEY)" \
  --set "MERCHANT_ID=$(v MERCHANT_ID)" \
  --set "MERCHANT_PAYOUT=$(v MERCHANT_PAYOUT)" \
  --set "TEAM_NAME=SportiQue" --set "AP4M_API_URL=https://hackathon.ap4m.build" \
  --set "AP4M_CHANNEL_CAP=10" --set "AP4M_POOLS=vault:5,research:5" \
  --set "AP4M_RAIL_TOKEN=$TOKEN" >/dev/null
echo "variables set on $RAIL (values not shown)"
railway volume add --service "$RAIL" --mount-path /data >/dev/null 2>&1 || echo "volume: already attached or add it in the dashboard (mount /data)"
railway up ap4m --path-as-root --service "$RAIL" --detach
DOMAIN="${AP4M_RAIL_URL:-}"; [ -n "$DOMAIN" ] || DOMAIN="$(railway domain --service "$RAIL" 2>/dev/null | grep -Eo 'https://[A-Za-z0-9.-]+' | head -1)"
[ -n "$DOMAIN" ] || { echo "Create a public domain for $RAIL in the dashboard, then: AP4M_RAIL_URL=https://... $0" >&2; exit 1; }
echo "rail: $DOMAIN (health: $DOMAIN/health)"

railway variables --service "$VAULT_SERVICE" --skip-deploys \
  --set "VM_AP4M=1" --set "AP4M_RAIL_URL=$DOMAIN" --set "AP4M_RAIL_TOKEN=$TOKEN" >/dev/null
railway up --service "$VAULT_SERVICE" --detach
echo "vault redeploying with VM_AP4M=1. Wait for $DOMAIN/health to answer before the first deal."
