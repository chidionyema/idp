import { permanentRedirect } from "next/navigation";

/**
 * Legacy routing playground belongs to the retired teal demo website, not the company's
 * public premium release. Its underlying reusable tooling remains in source
 * for a separately designed and verified launch; the old UI is never served.
 */
export default function RetiredPublicRoute() {
  permanentRedirect("/research");
}
