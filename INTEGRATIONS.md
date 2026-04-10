# Integration env variables and how to apply them

This repository standardises external-integration configuration (SMTP, OAuth, API keys, webhooks, S3) as environment variables.

Quick steps

1. Copy `ci/integrations.env.example` to `ci/.env` (or to a local `.env`) and fill values.
2. Keep `ci/.env` and any local `.env` files out of version control (the repo `.gitignore` already ignores them).
3. For CI, populate the same keys via your CI secret store or generate ephemeral values at runtime.

Applying values to Odoo

You can either configure the provider settings via the Odoo Settings UI or set system parameters programmatically. Example (run inside an `odoo shell` session):

```python
from os import environ
env['ir.config_parameter'].set_param('my_module.smtp_host', environ.get('SMTP_HOST') or '')
env['ir.config_parameter'].set_param('my_module.sendgrid_api_key', environ.get('SENDGRID_API_KEY') or '')
```

Replace `my_module.*` with the parameter keys your instance expects. Keep secrets in environment variables or secret stores and avoid committing them to Git.
