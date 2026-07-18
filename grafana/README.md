# Grafana Dashboard - Kairos

`kairos-dashboard.json` scrapes the metrics exposed by
`app/utils/prometheus_metrics.py` on `/metrics` (an endpoint gated by
`PROMETHEUS_ENABLED`, see `app/__init__.py`).

## Import

1. Grafana > Dashboards > New > Import
2. Paste the content of `kairos-dashboard.json` (or upload the file)
3. Choose the Prometheus datasource that scrapes `/metrics`

## Prometheus-side requirements

A scrape job pointing at the app, for example:

```yaml
scrape_configs:
  - job_name: kairos
    metrics_path: /metrics
    static_configs:
      - targets: ["kairos:5000"]
```

## Contents

- HTTP requests/s and errors/s (`kairos_requests_total`, `kairos_errors_total`)
- p95 latency per endpoint (`kairos_request_latency_seconds`)
- p95 SQL query time (`kairos_db_query_time_seconds`)
- Active users/sessions (`kairos_active_users`, `kairos_active_sessions`)
- Business volume: shifts, on-call, leave, users, groups
- CPU / memory / disk (`kairos_cpu_usage_percent`, `kairos_memory_usage_bytes`, `kairos_disk_usage_bytes`)

Dashboard not tested against a real Grafana instance (none available in
this environment) - metric names and JSON syntax verified against
`app/utils/prometheus_metrics.py` and the Grafana schema (`schemaVersion: 39`).
