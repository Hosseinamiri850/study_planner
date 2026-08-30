/** Client-side validation mirroring the backend's rules
 * (app/utils/validation.py). The backend remains authoritative; these
 * give fast feedback without a round-trip. */

export const USERNAME_PATTERN = /^[A-Za-z0-9_]{3,80}$/;

export function validUsername(value: string): boolean {
  return USERNAME_PATTERN.test(value);
}

export function validPassword(value: string): boolean {
  return value.length >= 8;
}

export function validPriority(value: string): value is "low" | "medium" | "high" {
  return value === "low" || value === "medium" || value === "high";
}

/** Backend accepts 0..24 (app/utils/validation.py:positive_hours). */
export function validEstimatedHours(value: number): boolean {
  return Number.isFinite(value) && value >= 0 && value <= 24;
}
