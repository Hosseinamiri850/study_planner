import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

/* RTL safety: physical horizontal Tailwind properties break the fa/en
 * mirroring contract (docs/redesign/04 §8). Promoted to error at Phase 6 —
 * the codebase is clean; keep it that way. */
const noPhysicalProperties = {
  files: ["app/**/*.{ts,tsx}", "components/**/*.{ts,tsx}", "lib/**/*.{ts,tsx}"],
  rules: {
    "no-restricted-syntax": [
      "error",
      {
        selector: "Literal[value=/\\b(p[lr]-|m[lr]-|left-|right-|text-left|text-right|border-[lr]-|rounded-[ltrb]+-[ltrb])/]",
        message:
          "Use logical Tailwind properties (ps-/pe-/ms-/me-/start-/end-/text-start/text-end) instead of physical pl/pr/ml/mr/left/right — RTL mirroring depends on it.",
      },
    ],
  },
};

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    ignores: [
      "node_modules/**",
      ".next/**",
      "out/**",
      "build/**",
      "next-env.d.ts",
    ],
  },
  noPhysicalProperties,
];

export default eslintConfig;
