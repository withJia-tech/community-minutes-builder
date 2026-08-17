/**
 * Fallback mirror of /data/fare-defaults.json and /data/parking-defaults.json.
 *
 * WHY THIS EXISTS
 * The canonical assumptions live in /data/*.json so a non-developer can revise
 * them without touching calculator logic. That buys auditability and costs a
 * network request that can fail: a mistyped path, a partial deploy, a 404 on
 * a renamed file, a flaky connection. A cost calculator that renders nothing
 * in those cases is worse than one carrying a stale-but-labelled default, so
 * the JSON is the source of truth and this is the parachute.
 *
 * WHAT THIS DOES *NOT* RESCUE — measured, not assumed
 * Opening index.html straight off disk. Chromium blocks ES module imports
 * over file:// as a CORS violation, so this module never loads and the
 * fallback never runs; the page is inert before any fetch is attempted.
 * Serve the folder over http for local development:
 *     python3 -m http.server 8099
 * That is a property of ES modules, not of this design — inlining every
 * script to dodge it would cost the unit tests, which is the worse trade.
 *
 * WHY THIS DOES NOT ROT
 * A mirror maintained by hand is a drift bug waiting to happen. It does not
 * drift here because test/data-drift.test.mjs asserts these objects are deeply
 * equal to the JSON files and fails the moment they diverge. Edit the JSON,
 * run the tests, and the test tells you to update this file.
 */

export const FARE_DEFAULTS = {
  assumptionsVersion: '2026.08',
  lastReviewed: '2026-08-17',
  caveat:
    'Every value below is an assumption, not a live figure. The calculator stamps this version onto shared results so a stale number is visible rather than silently wrong.',
  trip: {
    petrolPrice: 3.0,
    fuelEconomy: 12,
    erp: 0,
  },
  alternatives: {
    mrtFare: 1.8,
    walkTime: 10,
    hourlyRate: 25,
  },
  grabEstimate: {
    logicId: 'H2',
    base: 3.5,
    perKm: 0.55,
    caveat:
      'Ignores surge, time of day and platform fees. No public Grab API exists, so this stays an estimate and is always labelled as one.',
  },
  speeds: {
    driveKmh: 40,
    driveBufferMin: 4,
    mrtKmh: 25,
    grabKmh: 40,
    caveat:
      'H3 and H4. No traffic model, no transfer or platform-wait model. The MRT figure is the most under-modelled number in the build.',
    grabDerivation:
      'Grab uses the drive speed without the parking buffer, since nobody hunts for a space in a Grab.',
  },
  verdict: {
    logicId: 'D9',
    thresholdSgd: 5,
    caveat:
      'H7. A flat $5 band is arbitrary and does not scale with trip cost. A proportional band, max(5, 0.15 x driveTotal), is the noted fix path but is deliberately NOT implemented here, because D9 in the handoff specifies the flat threshold.',
  },
  limits: {
    maxDistanceKm: 300,
    maxParkHours: 72,
    caveat:
      'Guards against absurd input. Singapore is about 50 km end to end, so 300 km of one-way driving is already generous.',
  },
};

export const PARKING_DEFAULTS = {
  version: '1.0.0',
  lastReviewed: '2026-08-17',
  logicId: 'H1',
  status: 'heuristic',
  caveat:
    'Indicative flat hourly rates. Real Singapore carparks bill per 30 minutes with tiered escalation, and rates differ by day and time. These are approximations for comparison, not quotes.',
  upgradePath:
    'Phase 2 replaces this file with published HDB and URA carpark rates. Only the numbers change; the shape of this file does not.',
  destinations: [
    {
      id: 'hdb',
      label: 'HDB estate',
      hint: 'Void deck or multi-storey carpark',
      rate: 0.6,
      source: 'Typical HDB short-term rate',
    },
    {
      id: 'hospital',
      label: 'Hospital or clinic',
      hint: 'Public hospital visitor carpark',
      rate: 2.0,
      source: 'Typical restructured-hospital visitor rate',
    },
    {
      id: 'cbd',
      label: 'CBD or Orchard',
      hint: 'Town-centre commercial carpark',
      rate: 5.0,
      source: 'Typical central-area weekday rate',
    },
    {
      id: 'suburban-mall',
      label: 'Suburban mall',
      hint: 'Heartland shopping centre',
      rate: 3.0,
      source: 'Typical suburban mall rate',
    },
    {
      id: 'hotel-venue',
      label: 'Hotel or event venue',
      hint: 'Weddings, banquets, conferences',
      rate: 5.5,
      source: 'Typical hotel visitor rate',
    },
    {
      id: 'other',
      label: 'Somewhere else',
      hint: 'You already know the rate',
      rate: null,
      source: 'Your own figure',
    },
  ],
};

/**
 * Load assumptions, preferring the canonical JSON and falling back to the
 * mirror above. Never rejects — the calculator must always have numbers.
 * Returns { fares, parking, source } where source is 'data' or 'fallback'.
 */
export async function loadAssumptions(basePath = '../../data') {
  try {
    const [fares, parking] = await Promise.all([
      fetch(`${basePath}/fare-defaults.json`).then((r) => {
        if (!r.ok) throw new Error(`fare-defaults ${r.status}`);
        return r.json();
      }),
      fetch(`${basePath}/parking-defaults.json`).then((r) => {
        if (!r.ok) throw new Error(`parking-defaults ${r.status}`);
        return r.json();
      }),
    ]);
    return { fares, parking, source: 'data' };
  } catch (err) {
    console.warn(
      '[is-it-worth-it] Could not load /data/*.json, using built-in assumptions.',
      err,
    );
    return { fares: FARE_DEFAULTS, parking: PARKING_DEFAULTS, source: 'fallback' };
  }
}
