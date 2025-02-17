#!/bin/sh

# Default to server command if no arguments provided
if [ $# -eq 0 ]; then
    echo "No arguments provided. Defaulting to running the server."
    server=true
else
    server=false
fi

# All commands before the conditional ones
export PROJECT_NAME=seo_blog_bot

# Base OpenTelemetry configuration
export OTEL_EXPORTER_OTLP_ENDPOINT=https://signoz-otel-collector-proxy.cr.lvtd.dev
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf

# Logging specific configuration
export OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED=true
export OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=${OTEL_EXPORTER_OTLP_ENDPOINT}/v1/logs
export OTEL_EXPORTER_OTLP_LOGS_PROTOCOL=http/protobuf

# Additional OpenTelemetry configuration
export OTEL_PROPAGATORS=tracecontext,baggage
export OTEL_PYTHON_LOG_CORRELATION=true
export OTEL_TRACES_SAMPLER=parentbased_always_on


export DJANGO_SETTINGS_MODULE="seo_blog_bot.settings"

while getopts ":sw" option; do
    case "${option}" in
        s)  # Run server
            server=true
            ;;
        w)  # Run worker
            server=false
            ;;
        *)  # Invalid option
            echo "Invalid option: -$OPTARG" >&2
            ;;
    esac
done
shift $((OPTIND - 1))

# If no valid option provided, default to server
if [ "$server" = true ]; then
    python manage.py collectstatic --noinput
    python manage.py migrate
    export OTEL_SERVICE_NAME=${PROJECT_NAME}_${ENVIRONMENT:-dev}
    export OTEL_RESOURCE_ATTRIBUTES=service.name=${PROJECT_NAME}_${ENVIRONMENT:-dev}
    opentelemetry-instrument \
      --traces_exporter console,otlp \
      --metrics_exporter console,otlp \
      --logs_exporter console,otlp \
      --service_name ${PROJECT_NAME}_${ENVIRONMENT:-dev} \
      gunicorn ${PROJECT_NAME}.wsgi:application --bind 0.0.0.0:80 --workers 3 --threads 2 --reload
else
    export OTEL_SERVICE_NAME="${PROJECT_NAME}_${ENVIRONMENT:-dev}_workers"
    export OTEL_RESOURCE_ATTRIBUTES=service.name=${PROJECT_NAME}_${ENVIRONMENT:-dev}_workers
    opentelemetry-instrument \
      --traces_exporter console,otlp \
      --metrics_exporter console,otlp \
      --logs_exporter console,otlp \
      --service_name ${PROJECT_NAME}_${ENVIRONMENT:-dev}_workers \
      python manage.py qcluster
fi
