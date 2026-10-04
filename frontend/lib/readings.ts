// Helpers for presenting observations: the backend's `value` already contains the unit ("138 mg/dL"),
// so rendering value + unit side by side printed it twice.

import type { ObservationRead } from "@/lib/api";

/** Big number and small unit for a reading, without repeating the unit. */
export function splitReading(obs: ObservationRead): { main: string; unit: string } {
  const unit = obs.unit ?? "";
  const value = obs.value ?? obs.status ?? "\u2014"; // conditions/medications show their status
  const main = unit && value.endsWith(unit) ? value.slice(0, -unit.length).trim() : value;
  return { main: main || value, unit };
}

/** The most recent reading per metric name, newest first -- a "latest readings" view, not the full history. */
export function latestPerMetric(observations: ObservationRead[]): ObservationRead[] {
  const byName = new Map<string, ObservationRead>();
  for (const obs of observations) {
    const current = byName.get(obs.name);
    if (!current || (obs.observed_date ?? "") >= (current.observed_date ?? "")) byName.set(obs.name, obs);
  }
  return [...byName.values()].sort(
    (a, b) => (b.observed_date ?? "").localeCompare(a.observed_date ?? "") || a.name.localeCompare(b.name)
  );
}
