import type { Metadata, Viewport } from "next";

import { Providers } from "./providers";
import "./globals.css";

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
    <html lang="fa" dir="rtl" className="dark" suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
