// Synthetic catalog for the SLEEP-01 demo. Every value here is generated; no real person is behind P-017.
import { createHash } from 'node:crypto';

export const STUDY = Object.freeze({
  id: 'SLEEP-01',
  title: 'Synthetic sleep and recovery study',
  // GA4GH Data Use Ontology: HMB = health/medical/biomedical research.
  duo: 'HMB',
  items: Object.freeze(['resting_heart_rate_bpm', 'fatigue_score']),
});

// Price per export call, in RLUSD. Week 6 is the scripted over-cap listing the agent must refuse.
export const LISTINGS = Object.freeze([
  { pseudonym: 'P-017', week: 3, priceRlusd: '0.05' },
  { pseudonym: 'P-017', week: 4, priceRlusd: '0.05' },
  { pseudonym: 'P-017', week: 5, priceRlusd: '0.05' },
  { pseudonym: 'P-017', week: 6, priceRlusd: '0.50' },
]);

export function packageId(pseudonym, week) {
  return `${STUDY.id}-${pseudonym}-w${week}`.toLowerCase();
}

export function findListing(pseudonym, week) {
  return LISTINGS.find((entry) => entry.pseudonym === pseudonym && entry.week === Number(week));
}

// Deterministic pseudo-random numbers so the same week always yields the same package and hash.
function seeded(seed) {
  let counter = 0;
  return () => {
    const digest = createHash('sha256').update(`${seed}:${counter++}`).digest();
    return digest.readUInt32BE(0) / 0xffffffff;
  };
}

// A study-only package: pseudonym, study-relative days (real dates shifted away), and only the requested items.
export function syntheticPackage(pseudonym, week) {
  const random = seeded(`${STUDY.id}:${pseudonym}:${week}`);
  const days = [];
  for (let day = 1; day <= 7; day++) {
    days.push({
      study_day: (week - 1) * 7 + day,
      resting_heart_rate_bpm: Math.round(56 + random() * 14),
      fatigue_score: Math.round(random() * 10),
    });
  }
  return {
    schema: 'agentrail.synthetic-export.v1',
    synthetic: true,
    study: STUDY.id,
    pseudonym,
    week,
    date_handling: 'shifted to study-relative days; no calendar dates',
    items: [...STUDY.items],
    days,
  };
}
