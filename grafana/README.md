# Dashboard Grafana - Leviia Schedule

`leviia-schedule-dashboard.json` scrape les métriques exposées par
`app/utils/prometheus_metrics.py` sur `/metrics` (endpoint gated par
`PROMETHEUS_ENABLED`, voir `app/__init__.py`).

## Import

1. Grafana > Dashboards > New > Import
2. Coller le contenu de `leviia-schedule-dashboard.json` (ou uploader le fichier)
3. Choisir la datasource Prometheus qui scrape `/metrics`

## Prérequis côté Prometheus

Un job de scrape pointant vers l'app, par exemple :

```yaml
scrape_configs:
  - job_name: leviia-schedule
    metrics_path: /metrics
    static_configs:
      - targets: ["leviia-schedule:5000"]
```

## Contenu

- Requêtes HTTP/s et erreurs/s (`leviia_requests_total`, `leviia_errors_total`)
- Latence p95 par endpoint (`leviia_request_latency_seconds`)
- Temps requêtes SQL p95 (`leviia_db_query_time_seconds`)
- Utilisateurs/sessions actifs (`leviia_active_users`, `leviia_active_sessions`)
- Volumétrie métier : shifts, astreintes, congés, utilisateurs, groupes
- CPU / mémoire / disque (`leviia_cpu_usage_percent`, `leviia_memory_usage_bytes`, `leviia_disk_usage_bytes`)

Dashboard non testé contre une instance Grafana réelle (aucune disponible
dans cet environnement) - noms de métriques et syntaxe JSON vérifiés contre
`app/utils/prometheus_metrics.py` et le schéma Grafana (`schemaVersion: 39`).
