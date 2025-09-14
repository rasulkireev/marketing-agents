- [Deployment](#deployment)
  - [Render](#render)
  - [Docker Compose](#docker-compose)
  - [Pure Python / Django deployment](#pure-python--django-deployment)
  - [Custom Deployment on Caprover](#custom-deployment-on-caprover)
- [Local Development](#local-development)
  - [Getting Started](#getting-started)
  - [Next steps](#next-steps)
  - [Stripe](#stripe)
  - [Notes](#notes)
- [Star History](#star-history)


## Deployment

### Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/rasulkireev/marketing-agents)

The only required env vars are:
- GEMINI_API_KEY
- PERPLEXITY_API_KEY
- JINA_READER_API_KEY
- KEYWORDS_EVERYWHERE_API_KEY

The rest are optional.

**Note:** This should work out of the box with Render's free tier if you provide the AI API keys. Here's what you need to know about the limitations:

- **Worker Service Limitation**: The worker service is not a dedicated worker type (those are only available on paid plans). For the free tier, I had to use a web service through a small hack, but it works fine for most use cases.

- **Memory Constraints**: The free web service has a 512 MB RAM limit, which can cause issues with **automated background tasks only**. When you add a project, it runs a suite of background tasks to analyze your website, generate articles, keywords, and other content. These automated processes can hit memory limits and potentially cause failures.

- **Manual Tasks Work Fine**: However, if you perform tasks manually (like generating a single article), these typically use the web service instead of the worker and should work reliably since it's one request at a time.

- **Upgrade Recommendation**: If you do upgrade to a paid plan, use the actual worker service instead of the web service workaround for better automated task reliability.

**Reality Check**: The website functionality should be usable on the free tier - you'll only pay for API costs. Manual operations work fine, but automated background tasks (especially when adding multiple projects) may occasionally fail due to memory constraints. It's not super comfortable for heavy automated use, but perfectly functional for manual content generation.

If you know of any other services like Render that allow deployment via a button and provide free Redis, Postgres, and web services, please let me know in the [Issues](https://github.com/rasulkireev/marketing-agents/issues) section. I can try to create deployments for those. Bear in mind that free services are usually not large enough to run this application reliably.


### Docker Compose

This should also be pretty streamlined. On your server you can create a folder in which you will have 2 files:

1. `.env`
Copy the contents of `.env.example` into `.env` and update all the necessary values.

2. docker-compose.yml
Cope the contents of `docker-compose-prod.yml` into `docker-compose.yml` and run the suggested command from the top of the `docker-compose-prod.yml` file.

How you are going to expose the backend container is up to you. I usually do it via Nginx Reverse Proxy with `http://marketing-agents-backend-1:80` UPSTREAM_HTTP_ADDRESS.


### Pure Python / Django deployment

Not recommended due to not being too safe for production and not being tested by me.

If you are not into Docker or Render and just wanto to run this via regular commands you will need to have 5 processes running:
- `python manage.py collectstatic --noinput && python manage.py migrate && gunicorn ${PROJECT_NAME}.wsgi:application --bind 0.0.0.0:80 --workers 3 --threads 2`
- `python manage.py qcluster`
- `npm install && npm run start`
- `postgres`
- `redis`

You'd still need to make sure .env has correct values.

### Custom Deployment on Caprover

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

6. Github Workflow in this repo should take care of the rest.

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


### Notes
- Don't forget to update the site domain and name on the Admin Panel.


## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=rasulkireev/marketing-agents&type=Date)](https://www.star-history.com/#rasulkireev/marketing-agents&Date)
