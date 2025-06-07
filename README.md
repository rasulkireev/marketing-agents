
# Marketing Agents

## Deployment

1. Rename .env.example to .env and update all the relevant variables.
2. You should be able to run `docker compose up -d` on the server or your local machine.

## Local Development

### Getting Started

All the information on how to run, develop and update your new application can be found in the documentation.

1. Update the name of the `.env.example` to `.env` and update relevant variables.

To start you'll need to run these commands:
1. `poetry install`
2. `poetry export -f requirements.txt --output requirements.txt --without-hashes`
3. `poetry run python manage.py makemigrations`
4. `make serve` : Make sure you have a Docker Engine running. I recommend OrbStack.


### Next steps
- When everything is running, go to http://localhost:8009/ to check if the backend is running.
- You can sign up via regular signup. The first user will be made admin and superuser.
- Go to http://localhost:8009/admin/ and update Site info (http://localhost:8009/admin/sites/site/1/change/) to
  - localhost:8009 (if you are developing locally, and real domain when you are in prod)
  - Your project name


### Stripe
- For local. When you run make serve for the first time, a stripe-cli container will be created.
Looks at the logs for this container and at the top you will see a webhook secret generated.
Copy this and add it to your `.env` file.

The following notes are applicable only after you got the app running locally via `make serve`:
- Add Test and Prod Secret keys in the admin panel: http://localhost:8009/admin/djstripe/apikey/
(djstripe will figure out if they are live or test keys automatically)
- Create a webhook in Django admin panel: /admin/djstripe/webhookendpoint/
  - you can't use localhost as the domain for the webhook, so use something like `https://statushen.com/` or a real one if you have it. It doesn't matter for local.
  - When creating a webhook in the admin, specify the latest version from here https://stripe.com/docs/api/versioning
- Create your products in stripe (monthly, annual and one-time, for example), then sync them via `make stripe-sync` command.
- Current (`user-settings.html` and `pricing.html`) template assumes you have 3 products: monthly, annual and one-time.
  I haven't found a reliable way to programmatcialy set this template. When you have created your products in Stripe and synced them, update the template with the correct plan id.


### Deployment

1. Create 4 apps on CapRover.
  - `seo-blog-bot`
  - `seo-blog-bot-workers`
  - `seo-blog-bot-postgres`
  - `seo-blog-bot-redis`

2. Create a new CapRover app token for:
   - `seo-blog-bot`
   - `seo-blog-bot-workers`

3. Add Environment Variables to those same apps from `.env`.

4. Create a new GitHub Actions secret with the following:
   - `CAPROVER_SERVER`
   - `CAPROVER_APP_TOKEN`
   - `WORKERS_APP_TOKEN`
   - `REGISTRY_TOKEN`

5. Then just push main branch.

### Notes
- Don't forget to update the site domain and name on the Admin Panel.
