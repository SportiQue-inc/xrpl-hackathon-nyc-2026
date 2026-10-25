# AP4M payment rail (rail-server.mjs) as its own service. Build from the repository root:
#   docker build -f ap4m/Dockerfile .
# Keys come from the service's variables (AGENT_PRIVATE_KEY, MERCHANT_SUBMITTER_KEY, ...); state lives on /data.
FROM node:22-slim
WORKDIR /app/ap4m
COPY ap4m/package.json ./
COPY ap4m/vendor ./vendor
RUN npm install --omit=dev --no-audit --no-fund
COPY ap4m/lib ./lib
COPY ap4m/rail-server.mjs ./
ENV AP4M_STATE_DIR=/data/ap4m NODE_OPTIONS=--network-family-autoselection-attempt-timeout=1000
CMD ["node", "rail-server.mjs"]
