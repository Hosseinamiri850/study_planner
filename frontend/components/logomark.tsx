"use client";

/** Product logomark: an open book whose spine reads as a clock hand —
 * study (book) + tracked time (clock). Two colors: accent + currentColor.
 * Flips cleanly in RTL (symmetric shape, no directional strokes). */

export function Logomark({ size = 24 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden
      className="shrink-0"
    >
      {/* open book pages */}
      <path
        d="M12 6.5C10.2 4.9 7.4 4.5 4.5 4.5c-.55 0-1 .45-1 1v11c0 .55.45 1 1 1 2.9 0 5.7.4 7.5 2 1.8-1.6 4.6-2 7.5-2 .55 0 1-.45 1-1v-11c0-.55-.45-1-1-1-2.9 0-5.7.4-7.5 2Z"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinejoin="round"
      />
      <path d="M12 6.5v13" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
      {/* clock hand at the spine center */}
      <circle cx="12" cy="12" r="3.25" fill="var(--color-accent)" />
      <path
        d="M12 10.4V12l1.1 1.1"
        stroke="var(--color-accent-fg)"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
