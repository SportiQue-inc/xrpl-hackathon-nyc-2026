// WebAuthn in the browser for the participant's approvals. The engine (or UniQdata, through the
// engine) sends options with base64url fields; the authenticator (Touch ID, a phone, a security
// key) answers; we send back base64url fields named as UniQdata names them.

const toBuf = (s) => {
  const b = atob(s.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((s.length + 3) % 4));
  return Uint8Array.from(b, (c) => c.charCodeAt(0)).buffer;
};
const toB64u = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const creds = (list) => (list || []).map((c) => ({ ...c, id: toBuf(c.id) }));

export const passkeySupported = () => !!(window.PublicKeyCredential && navigator.credentials);

export async function createPasskey(publicKey) {
  const c = await navigator.credentials.create({ publicKey: {
    ...publicKey, challenge: toBuf(publicKey.challenge), user: { ...publicKey.user, id: toBuf(publicKey.user.id) },
    excludeCredentials: creds(publicKey.excludeCredentials) } });
  return { credentialId: toB64u(c.rawId), rawId: toB64u(c.rawId), attestationObject: toB64u(c.response.attestationObject),
           clientDataJson: toB64u(c.response.clientDataJSON),
           transports: c.response.getTransports ? c.response.getTransports() : [] };
}

export async function signWithPasskey(publicKey) {
  const a = await navigator.credentials.get({ publicKey: {
    ...publicKey, challenge: toBuf(publicKey.challenge), allowCredentials: creds(publicKey.allowCredentials) } });
  const out = { credentialId: toB64u(a.rawId), rawId: toB64u(a.rawId), authenticatorData: toB64u(a.response.authenticatorData),
                clientDataJson: toB64u(a.response.clientDataJSON), signature: toB64u(a.response.signature) };
  if (a.response.userHandle) out.userHandle = toB64u(a.response.userHandle);
  if (publicKey.challengeId) out.challengeId = publicKey.challengeId;
  return out;
}
