/** The contact endpoint has two distinct release concerns:
 * 1. Broken/missing API contract is a customer-visible regression (P0 route).
 * 2. A valid API that says delivery is not activated is a known commercial blocker
 *    during pre-domain launch and must not fabricate a P0 visual design incident.
 */
export function classifyContactReadiness(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return 'invalid';
  if (value.acceptingEnquiries === true) return 'configured';
  if (value.acceptingEnquiries === false) return 'awaiting-inbox-activation';
  return 'invalid';
}
