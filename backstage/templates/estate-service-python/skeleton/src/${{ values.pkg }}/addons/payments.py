{%- if 'payments' in values.addons %}
"""Payments through Stripe. The key is the vault entry's `stripe-secret-key`, mounted as a file;
it is never in an environment variable or in this repository."""
import stripe

from .. import secrets


def client() -> stripe.StripeClient:
    key = secrets.read("stripe-secret-key")
    if not key:
        raise RuntimeError("stripe-secret-key not mounted")
    return stripe.StripeClient(key)
{%- else %}
"""Payments not ticked at creation. Re-run the template with Payments ticked to add it."""
{%- endif %}
