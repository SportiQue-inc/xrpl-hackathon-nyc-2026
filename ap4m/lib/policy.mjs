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
 * @returns {{ pay: boolean, reason: string, priceWei: bigint | null }}
 */
export function decide(offer, policy, consent, spentWei) {
  let priceWei;
  try { priceWei = toWei(offer?.price_rlusd); } catch { return refuse('offer has no valid price', null); }
  if (!offer.pay_to || !policy.payeeAllowlist.includes(String(offer.pay_to).toLowerCase())) {
    return refuse(`payee ${offer.pay_to ?? '(none)'} is not in the allowlist`, priceWei);
  }
  if (priceWei > policy.perCallCapWei) {
    return refuse(`price ${fromWei(priceWei)} RLUSD exceeds per-call cap ${fromWei(policy.perCallCapWei)} RLUSD`, priceWei);
  }
  if (spentWei + priceWei > policy.budgetWei) {
    return refuse(`price ${fromWei(priceWei)} RLUSD would bring the total to ${fromWei(spentWei + priceWei)} RLUSD, over the delegated budget ${fromWei(policy.budgetWei)} RLUSD`, priceWei);
  }
  const purpose = offer.purpose ?? {};
  if (purpose.study !== consent.study) return refuse(`study ${purpose.study} does not match consent ${consent.study}`, priceWei);
  if (purpose.duo !== consent.duo) return refuse(`purpose ${purpose.duo} does not match consented use ${consent.duo}`, priceWei);
  if (offer.pseudonym !== consent.pseudonym) return refuse(`pseudonym ${offer.pseudonym} is not covered by consent`, priceWei);
  if (!consent.weeks.includes(offer.week)) return refuse(`week ${offer.week} is outside consented weeks ${consent.weeks.join(',')}`, priceWei);
  const extra = (offer.items ?? []).filter((item) => !consent.items.includes(item));
  if (!offer.items?.length || extra.length) return refuse(`items ${extra.join(',') || '(none)'} are not consented`, priceWei);
  return {
    pay: true,
    reason: `price ${fromWei(priceWei)} <= cap ${fromWei(policy.perCallCapWei)}, total ${fromWei(spentWei + priceWei)} <= budget ${fromWei(policy.budgetWei)}, payee allowlisted, purpose ${purpose.duo} matches consent`,
    priceWei,
  };
}

function refuse(reason, priceWei) {
  return { pay: false, reason, priceWei };
}
