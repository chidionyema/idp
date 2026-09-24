# {{ values.organisation }} — {{ values.provider }} Integration

## Status: Connected ✓

A test event arrived (ID: {{ values.eventReceived }}).

## What happens next

Events from {{ values.account }} now flow to your organisation.

## Provider-specific steps

{% if values.provider == 'slack' %}
### Slack
1. Go to your Slack workspace settings
2. Verify the app is installed under "Installed Apps"
3. Events will appear in the #general channel by default
{% elif values.provider == 'teams' %}
### Microsoft Teams
1. Open the Teams admin center
2. Verify the app registration is active
3. Events appear in the configured channel
{% elif values.provider == 'discord' %}
### Discord
1. Open your Discord server settings
2. Verify the bot is in the server
3. Events appear in the configured text channel
{% elif values.provider == 'telegram' %}
### Telegram
1. Open your bot in BotFather
2. Verify the bot token is active
3. Start a chat with the bot to receive events
{% elif values.provider == 'webhook' %}
### Webhook
1. Verify your endpoint accepts POST requests
2. Check the webhook URL is correct
3. Test with a manual POST request
{% endif %}

## Troubleshooting

If events stop arriving:
1. Check the secret at {{ values.secretLocation }} is still valid
2. Verify the account still has the integration installed
3. Contact your platform team with the organisation name: {{ values.organisation }}
