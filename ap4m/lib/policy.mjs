// Deterministic payment policy. The agent pays only when every rule passes; no human prompt.
import { fromWei, toWei } from './units.mjs';

export function buildPolicy({ perCallCapRlusd, budgetRlusd, payeeAllowlist }) {
  return Object.freeze({
    perCallCapWei: toWei(perCallCapRlusd),
    budgetWei: toWei(budgetRlusd),
    payeeAllowlist: Object.freeze(payeeAllowlist.map((address) => address.toLowerCase())),
  });
}

// The participant's consent for this task: which study, which data use, which items and weeks.
export function buildConsent({ pseudonym, study, duo, items, weeks }) {
  return Object.freeze({ pseudonym, study, duo, items: Object.freeze([...items]), weeks: Object.freeze([...weeks]) });
}

/**
 * @param offer     402 offer from the export endpoint
 * @param policy    from buildPolicy
 * @param consent   from buildConsent
 * @param spentWei  RLUSD already paid in this task, in wei
 * @returns {{ pay: boolean, reason: string, reasons: string[], priceWei: bigint | null }}
 *   Every rule is checked and every rule that fails is listed in `reasons` (joined in `reason`), so a refusal
 *   shows each limit on its own: a request can be outside the consent and over the cap at the same time.
 *   An offer without a valid price skips only the two checks that need one (cap, budget); `priceWei` is then null.
 */
export function decide(offer, policy, consent, spentWei) {
  offer = offer ?? {};
  const reasons = [];
  let priceWei = null;
  try { priceWei = toWei(offer.price_rlusd); } catch { reasons.push('offer has no valid price'); }
  if (!offer.pay_to || !policy.payeeAllowlist.includes(String(offer.pay_to).toLowerCase())) {
    reasons.push(`payee ${offer.pay_to ?? '(none)'} is not in the allowlist`);
  }
  if (priceWei !== null && priceWei > policy.perCallCapWei) {
    reasons.push(`price ${fromWei(priceWei)} RLUSD exceeds per-call cap ${fromWei(policy.perCallCapWei)} RLUSD`);
  }
  if (priceWei !== null && spentWei + priceWei > policy.budgetWei) {
    reasons.push(`price ${fromWei(priceWei)} RLUSD would bring the total to ${fromWei(spentWei + priceWei)} RLUSD, over the delegated budget ${fromWei(policy.budgetWei)} RLUSD`);
  }
  const purpose = offer.purpose ?? {};
  if (purpose.study !== consent.study) reasons.push(`study ${purpose.study} does not match consent ${consent.study}`);
  if (purpose.duo !== consent.duo) reasons.push(`purpose ${purpose.duo} does not match consented use ${consent.duo}`);
  if (offer.pseudonym !== consent.pseudonym) reasons.push(`pseudonym ${offer.pseudonym} is not covered by consent`);
  if (!consent.weeks.includes(offer.week)) reasons.push(`week ${offer.week} is outside consented weeks ${consent.weeks.join(',')}`);
  const extra = (offer.items ?? []).filter((item) => !consent.items.includes(item));
  if (!offer.items?.length || extra.length) reasons.push(`items ${extra.join(',') || '(none)'} are not consented`);
  if (reasons.length) return refuse(reasons, priceWei);
  return {
    pay: true,
    reason: `price ${fromWei(priceWei)} <= cap ${fromWei(policy.perCallCapWei)}, total ${fromWei(spentWei + priceWei)} <= budget ${fromWei(policy.budgetWei)}, payee allowlisted, purpose ${purpose.duo} matches consent`,
    reasons: [],
    priceWei,
  };
}

function refuse(reasons, priceWei) {
  return { pay: false, reason: reasons.join('; '), reasons, priceWei };
}
