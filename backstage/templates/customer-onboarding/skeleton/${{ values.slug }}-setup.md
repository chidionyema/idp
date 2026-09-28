# {{ values.organisation }} — {{ values.provider }} setup

**Status: requested, not yet live.** The binding is in a pull request. Events will not
arrive until that pull request is merged and the row is applied to the ingress
database. Nothing here has been tested against the live account yet, and this page will
not claim otherwise.

## What the customer does on their side

{% if values.provider == 'slack' %}
1. Install the app into the **{{ values.account }}** workspace.
2. Grant it the events scope, and nothing more than that.
3. Point the event subscription at the ingress URL the platform team gives you.
{% elif values.provider == 'teams' %}
1. In the Teams admin centre for **{{ values.account }}**, approve the app registration.
2. Add the app to the channel whose messages should reach us.
3. Point the outgoing webhook at the ingress URL the platform team gives you.
{% elif values.provider == 'discord' %}
1. Invite the bot to the **{{ values.account }}** server.
2. Give it read access to the channel whose messages should reach us.
3. Confirm the bot appears in the member list before testing.
{% elif values.provider == 'telegram' %}
1. Confirm **{{ values.account }}** is the bot's username exactly as BotFather shows it.
2. Send the bot one message, so Telegram starts delivering updates.
3. Keep the bot token where it is; the estate reads it from
   `{{ values.secretStore }}:{{ values.secretPath }}` and never holds a copy.
{% elif values.provider == 'webhook' %}
1. Confirm **{{ values.account }}** accepts POST with a JSON body.
2. Sign each request with the secret at `{{ values.secretStore }}:{{ values.secretPath }}`.
3. Send one request and check for a 202; anything else is refused, not queued.
{% endif %}

## If events do not arrive after the binding is applied

The lookup is on channel and external id together, so the usual cause is that
`{{ values.account }}` is not exactly the value {{ values.provider }} puts on the
event. The ingress refuses an unmatched message rather than guessing whose it is, so a
near-miss looks identical to nothing being sent.

The second thing to check is the credential at
`{{ values.secretStore }}:{{ values.secretPath }}`. If it was rotated, the fingerprint
on the row no longer matches and the binding has to be re-applied. Quote the tenant id
`{{ values.slug }}` when you raise it.
