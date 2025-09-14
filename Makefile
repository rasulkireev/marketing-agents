serve:
	docker compose -f docker-compose-local.yml up -d --build
	docker compose logs -f backend

manage:
	docker compose run --rm backend python ./manage.py $(filter-out $@,$(MAKECMDGOALS))

makemigrations:
	docker compose run --rm backend python ./manage.py makemigrations

shell:
	docker compose run --rm backend python ./manage.py shell_plus --ipython

test:
	docker compose run --rm backend pytest

bash:
	docker compose run --rm backend bash

test-webhook:
	docker compose run --rm stripe trigger customer.subscription.created

stripe-sync:
	docker compose run --rm backend python ./manage.py djstripe_sync_models Product Price

restart-worker:
	docker compose up -d workers --force-recreate

prod-shell:
	./deployment/prod-shell.sh
