# How-to

## Add a secret
Put the key in the vault entry `${{ values.name }}-env`; it lands as a file under `/var/run/secrets/${{ values.name }}` within the hour.
