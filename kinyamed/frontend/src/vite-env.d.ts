/// <reference types="vite/client" />

/** Typed environment. Declared rather than reaching for `any`, so a typo in an
 *  env var name is a compile error instead of an undefined at runtime. */
interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
}
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
