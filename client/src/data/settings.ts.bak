// NOTE:
// - During local development (`pnpm dev`), we always target the backend at http://127.0.0.1:8000
// - During production builds (`pnpm build`), we use the value of PROD_API_BASE_URL.
//   The set-env scripts will automatically update PROD_API_BASE_URL to the base of OIDC_REDIRECT_URI
//   (scheme + host [+ port], no path), and then rebuild the frontend.

// This placeholder gets overwritten by set-env.{bat,sh} during CI/CD or first deployment.
// Do not change the variable name; the scripts search/replace this exact line.
// prettier-ignore
const PROD_API_BASE_URL = "https://van-ai-guided-data-entry.apps.int.ap1-paas.cloud.corpintra.net";

export const apiURL = import.meta.env.DEV
  ? "http://127.0.0.1:8000/api"
  : PROD_API_BASE_URL + "/api";

export const redirectURL = import.meta.env.DEV
  ? "https://127.0.0.1:5000"
  : PROD_API_BASE_URL;