"""
Module pour l'intégration avec Prometheus.

Ce module expose des métriques pour le monitoring de l'application
via l'endpoint /metrics.
"""

from flask import Blueprint, current_app, jsonify, request
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
import time

# Créer un blueprint pour les métriques
metrics_bp = Blueprint('prometheus_metrics', __name__)

# ============================================
# Métriques personnalisées
# ============================================

# Compteurs
REQUEST_COUNT = Counter(
    'leviia_requests_total',
    'Nombre total de requêtes HTTP',
    ['method', 'endpoint', 'http_status']
)

ERROR_COUNT = Counter(
    'leviia_errors_total',
    'Nombre total d\'erreurs',
    ['error_type']
)

# Gauges
ACTIVE_USERS = Gauge(
    'leviia_active_users',
    'Nombre d\'utilisateurs actifs'
)

ACTIVE_SESSIONS = Gauge(
    'leviia_active_sessions',
    'Nombre de sessions actives'
)

# Histogrammes
REQUEST_LATENCY = Histogram(
    'leviia_request_latency_seconds',
    'Latence des requêtes en secondes',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0]
)

DB_QUERY_TIME = Histogram(
    'leviia_db_query_time_seconds',
    'Temps d\'exécution des requêtes SQLAlchemy',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 1.0]
)

# Métriques système
CPU_USAGE = Gauge(
    'leviia_cpu_usage_percent',
    'Utilisation CPU en pourcentage'
)

MEMORY_USAGE = Gauge(
    'leviia_memory_usage_bytes',
    'Utilisation mémoire en octets'
)

DISK_USAGE = Gauge(
    'leviia_disk_usage_bytes',
    'Utilisation disque en octets'
)

# Métriques métier
SHIFTS_COUNT = Gauge(
    'leviia_shifts_total',
    'Nombre total de shifts'
)

ONCALLS_COUNT = Gauge(
    'leviia_oncalls_total',
    'Nombre total d\'astreintes'
)

LEAVES_COUNT = Gauge(
    'leviia_leaves_total',
    'Nombre total de congés'
)

USERS_COUNT = Gauge(
    'leviia_users_total',
    'Nombre total d\'utilisateurs'
)

GROUPS_COUNT = Gauge(
    'leviia_groups_total',
    'Nombre total de groupes'
)


# ============================================
# Middleware pour le tracking des requêtes
# ============================================

@metrics_bp.before_app_request
def before_request():
    """Début du tracking d'une requête."""
    if hasattr(current_app, '_prometheus_start_time'):
        return
    current_app._prometheus_start_time = time.time()


@metrics_bp.after_app_request
def after_request(response):
    """Fin du tracking d'une requête."""
    if not hasattr(current_app, '_prometheus_start_time'):
        return response
    
    latency = time.time() - current_app._prometheus_start_time
    method = request.method
    endpoint = request.path
    status_code = response.status_code
    
    # Incrémenter les compteurs
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, http_status=status_code).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)
    
    # Nettoyer
    del current_app._prometheus_start_time
    
    return response


@metrics_bp.app_errorhandler(Exception)
def handle_exception(error):
    """Tracking des erreurs."""
    ERROR_COUNT.labels(error_type=type(error).__name__).inc()
    return error


# ============================================
# Endpoint pour Prometheus
# ============================================

@metrics_bp.route('/metrics')
def metrics():
    """
    Endpoint pour Prometheus.
    
    Retourne les métriques au format Prometheus.
    """
    # Mettre à jour les métriques métier
    _update_business_metrics()
    
    # Mettre à jour les métriques système
    _update_system_metrics()
    
    # Générer les métriques
    metrics_data = generate_latest()
    
    return metrics_data, 200, {'Content-Type': CONTENT_TYPE_LATEST}


@metrics_bp.route('/health')
def health():
    """
    Endpoint de santé pour les probes Kubernetes.
    
    Retourne un statut 200 si l'application est en bonne santé.
    """
    return jsonify({
        'status': 'healthy',
        'version': current_app.config.get('VERSION', 'unknown'),
        'environment': current_app.config.get('FLASK_ENV', 'unknown')
    }), 200


@metrics_bp.route('/ready')
def ready():
    """
    Endpoint de prêt pour les probes Kubernetes.
    
    Retourne un statut 200 si l'application est prête à recevoir du trafic.
    """
    # Vérifier la connexion à la base de données
    try:
        from app import db
        db.session.execute('SELECT 1')
        db.session.commit()
        return jsonify({'status': 'ready'}), 200
    except Exception as e:
        return jsonify({'status': 'not ready', 'error': str(e)}), 503


# ============================================
# Fonctions utilitaires
# ============================================

def _update_business_metrics():
    """Mettre à jour les métriques métier."""
    try:
        from app.models import Shift, OnCall, Leave, User, Group
        from app import db
        
        SHIFTS_COUNT.set(Shift.query.count())
        ONCALLS_COUNT.set(OnCall.query.count())
        LEAVES_COUNT.set(Leave.query.count())
        USERS_COUNT.set(User.query.count())
        GROUPS_COUNT.set(Group.query.count())
        
    except Exception:
        pass


def _update_system_metrics():
    """Mettre à jour les métriques système."""
    try:
        import psutil
        
        # CPU
        CPU_USAGE.set(psutil.cpu_percent(interval=1))
        
        # Mémoire
        mem = psutil.virtual_memory()
        MEMORY_USAGE.set(mem.used)
        
        # Disque
        disk = psutil.disk_usage('/')
        DISK_USAGE.set(disk.used)
        
    except ImportError:
        # psutil n'est pas installé
        pass
    except Exception:
        pass


def init_prometheus(app):
    """
    Initialiser Prometheus avec l'application Flask.
    
    Args:
        app: L'application Flask
    """
    # Enregistrer le blueprint
    app.register_blueprint(metrics_bp)
    
    # Initialiser les métriques de base
    _update_business_metrics()
    _update_system_metrics()
    
    current_app.logger.info('Prometheus metrics initialized')
