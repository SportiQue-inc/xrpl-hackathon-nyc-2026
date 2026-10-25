# AP4M payment rail (rail-server.mjs) as its own service. Build context is this folder:
#   railway up ap4m --path-as-root --service ap4m-rail     or     docker build ap4m
# Keys come from the service's variables (AGENT_PRIVATE_KEY, MERCHANT_SUBMITTER_KEY, ...); state lives on /data.
FROM node:22-slim
WORKDIR /app
COPY package.json ./
COPY vendor ./vendor
RUN npm install --omit=dev --no-audit --no-fund
COPY lib ./lib
COPY rail-server.mjs ./
ENV AP4M_STATE_DIR=/data/ap4m NODE_OPTIONS=--network-family-autoselection-attempt-timeout=1000
CMD ["node", "rail-server.mjs"]
