/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** e.g. https://your-api.example.com — optional; omit for same-origin or dev proxy */
  readonly VITE_API_BASE_URL?: string;
}
