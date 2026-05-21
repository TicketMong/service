#!/bin/sh
set -eu

PATIENT_SERVICE_URL="${E2E_PATIENT_SERVICE_URL:-http://patient-service:8081}"
APPOINTMENT_SERVICE_URL="${E2E_APPOINTMENT_SERVICE_URL:-http://appointment-service:8082}"
PRESCRIPTION_SERVICE_URL="${E2E_PRESCRIPTION_SERVICE_URL:-http://prescription-service:8083}"
NOTIFICATION_SERVICE_URL="${E2E_NOTIFICATION_SERVICE_URL:-http://notification-service:8084}"
TIMEOUT_SECONDS="${E2E_WAIT_TIMEOUT_SECONDS:-180}"
SLEEP_SECONDS="${E2E_WAIT_SLEEP_SECONDS:-5}"

start_time="$(date +%s)"

log() {
  printf '%s\n' "$*"
}

deadline_exceeded() {
  now="$(date +%s)"
  elapsed="$((now - start_time))"
  [ "$elapsed" -ge "$TIMEOUT_SECONDS" ]
}

check_health() {
  service_name="$1"
  service_url="$2"
  status_code="$(curl -sS -o /dev/null -w '%{http_code}' "$service_url/health" || true)"
  if [ "$status_code" != "200" ]; then
    log "$service_name is not ready yet. HTTP status: $status_code"
    return 1
  fi
  return 0
}

check_services() {
  check_health "patient-service" "$PATIENT_SERVICE_URL" &&
    check_health "appointment-service" "$APPOINTMENT_SERVICE_URL" &&
    check_health "prescription-service" "$PRESCRIPTION_SERVICE_URL" &&
    check_health "notification-service" "$NOTIFICATION_SERVICE_URL"
}

while true; do
  if check_services; then
    log "E2E services are ready."
    exit 0
  fi

  if deadline_exceeded; then
    log "Timed out waiting for E2E services."
    log "patient-service: $PATIENT_SERVICE_URL"
    log "appointment-service: $APPOINTMENT_SERVICE_URL"
    log "prescription-service: $PRESCRIPTION_SERVICE_URL"
    log "notification-service: $NOTIFICATION_SERVICE_URL"
    exit 1
  fi

  log "Waiting for E2E services..."
  sleep "$SLEEP_SECONDS"
done
