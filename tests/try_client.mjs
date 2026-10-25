import assert from "node:assert/strict";
import { engine } from "../apps/shared/api.js";

const requests = [];
globalThis.fetch = async (url, options) => {
  requests.push({ url, ...options });
  return { ok: true, status: 200, json: async () => ({ signature: "demo" }) };
};

await engine("", { token: async () => "token", sandboxCode: "judges-2026" }).signApproval("owner", 7);
assert.equal(requests[0].url, "/api/dev/devices/approver%3Aowner%40org_sleeplab/sign-approval/7");
assert.equal(requests[0].headers["X-Sandbox-Code"], "judges-2026");
assert.equal(requests[1].headers.Authorization, "Bearer token");

requests.length = 0;
await engine("", { token: async () => "token" }).signApproval("owner", 7);
assert.equal(requests[0].headers["X-Sandbox-Code"], undefined);
console.log("PASS: remote demo co-sign carries the code; default clients keep their auth behavior.");
