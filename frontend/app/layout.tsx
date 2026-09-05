import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";

import { Providers } from "./providers";
import "./globals.css";

const vazirmatn = localFont({
  src: "../public/fonts/Vazirmatn[wght].woff2",
  weight: "100 900",
  style: "normal",
  display: "swap",
  variable: "--font-vazirmatn",
});

const spaceGrotesk = localFont({
  src: "../public/fonts/SpaceGrotesk[wght].woff2",
  weight: "300 700",
  style: "normal",
  display: "swap",
  variable: "--font-space-grotesk",
  // Space Grotesk has no Arabic-script glyphs. Next's automatic metric
  // fallback ("spaceGrotesk Fallback") resolves to a system font WITH
  // Arabic coverage (e.g. Segoe UI on Windows), which intercepts Persian
  // digits/words before our Vazirmatn fallback can serve them. Disabling
  // the auto fallback lets the per-glyph fallback chain in globals.css
  // (--font-display) reach Vazirmatn directly.
  adjustFontFallback: false,
});

export const metadata: Metadata = {
  title: {
    default: "Study Planner",
    template: "%s | Study Planner",
  },
  description: "Plan courses, track study sessions, and see your progress.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fa" dir="rtl" className={`dark ${vazirmatn.variable} ${spaceGrotesk.variable}`} suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
