#!/usr/bin/env bash
# Start the synthetic export merchant, run the participant agent once, stop the merchant, print the summary.
#   ./run-live.sh            live run on XRPL EVM Testnet (needs ap4m/.env and npm install)
#   DRY_RUN=1 ./run-live.sh  no network: fake signer, fake redeem, same decision logs
set -euo pipefail
cd "$(dirname "$0")"

# Never echo values; only report which names are present.
has() {
  [ -n "${!1:-}" ] && return 0
  [ -f .env ] && grep -Eq "^[[:space:]]*$1[[:space:]]*=[[:space:]]*[^[:space:]]" .env
}

if [ "${DRY_RUN:-}" != "1" ]; then
  missing=()
  for name in AGENT_PRIVATE_KEY TEAM_NAME MERCHANT_ID MERCHANT_SUBMITTER_KEY; do
    has "$name" || missing+=("$name")
  done
  has MERCHANT_PAYOUT || has MERCHANT_PAYOUT_ADDRESS || missing+=("MERCHANT_PAYOUT (or MERCHANT_PAYOUT_ADDRESS)")
  if [ ${#missing[@]} -gt 0 ]; then
    echo "ap4m/.env is missing: ${missing[*]}" >&2
    echo "Copy .env.example to .env and fill it from the participant portal (My setup tab)." >&2
    exit 1
  fi
  if [ ! -d node_modules/@ap4m/sdk ] || [ ! -d node_modules/ethers ]; then
    echo "Run 'npm install' in ap4m/ first (installs ethers 6.17.0 and the vendored AP4M SDK)." >&2
    exit 1
  fi
fi

port="${MERCHANT_PORT:-}"
if [ -z "$port" ] && [ -f .env ]; then
  port="$( { grep -E '^[[:space:]]*MERCHANT_PORT[[:space:]]*=' .env || true; } | tail -1 | sed -E 's/^[^=]*=[[:space:]]*//; s/[[:space:]]*$//')"
fi
port="${port:-4400}"

mkdir -p out
log="out/merchant-$(date -u +%Y%m%dT%H%M%SZ).log"
node merchant.mjs >"$log" 2>&1 &
merchant_pid=$!
trap 'kill "$merchant_pid" 2>/dev/null || true; wait "$merchant_pid" 2>/dev/null || true' EXIT

for _ in $(seq 1 60); do
  if grep -q '^\[merchant\] .*serving' "$log" 2>/dev/null; then break; fi
  if ! kill -0 "$merchant_pid" 2>/dev/null; then cat "$log" >&2; echo "merchant exited" >&2; exit 1; fi
  sleep 0.5
done
grep -q '^\[merchant\] .*serving' "$log" || { cat "$log" >&2; echo "merchant did not start" >&2; exit 1; }
cat "$log"

MERCHANT_URL="http://127.0.0.1:${port}" node agent.mjs | tee out/agent-last.log
status=${PIPESTATUS[0]}

echo
echo "== summary =="
grep -E '^\[(decision|pay|package|settle|summary)\]' out/agent-last.log || true
exit "$status"
