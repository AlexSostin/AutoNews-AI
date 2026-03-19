import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import sonarjs from "eslint-plugin-sonarjs";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // SonarJS: detect duplicate logic, cognitive complexity, code smells
  sonarjs.configs.recommended,
  {
    rules: {
      // ── Duplication detection ──────────────────────────────────────
      "sonarjs/no-identical-functions": "warn",    // two functions with same body
      "sonarjs/no-duplicated-branches": "warn",    // if/else branches that do the same thing
      // ── Complexity ────────────────────────────────────────────────
      "sonarjs/cognitive-complexity": ["warn", 20], // flag overly complex functions
      // ── Code smells ───────────────────────────────────────────────
      "sonarjs/no-collapsible-if": "warn",         // nested ifs that could be merged
      "sonarjs/no-redundant-boolean": "warn",      // `if (x === true)`
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    "node_modules/**",
  ]),
]);

export default eslintConfig;
