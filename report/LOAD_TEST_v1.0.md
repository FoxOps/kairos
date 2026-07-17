# Test de charge v1.0

## Méthodologie

**Outil recommandé pour un usage réel** : `scripts/load_test.sh`, un
wrapper autour de `wrk` (préféré) ou `hey` — deux binaires externes, zéro
dépendance Python supplémentaire (cohérent avec la philosophie de ce
projet : peu de dépendances, voir CLAUDE.md et le choix déjà fait pour
`hey`/`wrk` plutôt que Locust). Aucun des deux n'était installable dans
l'environnement bac-à-sable de cette session (pas de `sudo` interactif
disponible pour `pacman -S wrk`) — les résultats ci-dessous ont donc été
obtenus avec un script Python autonome utilisant uniquement la bibliothèque
standard (`concurrent.futures` + `urllib`, pas de dépendance ajoutée au
projet), pour produire des chiffres réels plutôt que de laisser cette
section vide. **`scripts/load_test.sh` reste le script livré et
recommandé** pour toute mesure future — plus rapide et plus complet que le
script ad hoc utilisé ici (support HTTP/2, latences plus précises,
histogrammes).

### Configuration testée

- Serveur : `gunicorn --workers 1 --threads 4 --timeout 120` — exactement
  la commande de `docker/entrypoint.sh` en mode production (voir
  CLAUDE.md "Database backups" pour le contexte de ce choix : un seul
  worker + 4 threads, pas de multi-process).
- Base de données : SQLite, ~31 utilisateurs, ~390 shifts (60 jours dans
  le passé, 120 dans le futur), 12 astreintes — volumétrie modeste mais
  réaliste pour une équipe utilisant cette app (voir CLAUDE.md : outil de
  planning d'équipe, pas un SaaS multi-tenant à grande échelle).
- Machine : poste de développement partagé avec le reste de cette session
  (résultats à titre indicatif, pas un banc de test dédié isolé — voir
  "Limites" ci-dessous).

### Un vrai bug trouvé en préparant ce test

En essayant simplement de me connecter par script pour tester les pages
authentifiées, la connexion échouait silencieusement (`/dashboard`
redirigeait toujours vers `/login`, comme si aucune session n'était
jamais conservée) — alors même que `TALISMAN_FORCE_HTTPS=false` et
`SESSION_COOKIE_SECURE` à sa valeur par défaut (`false`), la configuration
documentée par défaut pour un déploiement sans proxy TLS. Investigation :
Flask-Talisman a son **propre** défaut indépendant pour
`session_cookie_secure` (`True`), non lié à `force_https`, et son hook
`before_request` réécrit `app.config["SESSION_COOKIE_SECURE"] = True` à
**chaque requête** dès que `app.debug` est `False` — écrasant
silencieusement le réglage `SESSION_COOKIE_SECURE` de l'app.
Conséquence : dans exactement la configuration par défaut documentée
(`TALISMAN_FORCE_HTTPS=false`, pas de proxy TLS), le cookie de session
était marqué `Secure`, donc jamais renvoyé par le navigateur en HTTP
simple - **connexion cassée en pratique** pour tout déploiement suivant
la configuration par défaut sans HTTPS (`python run.py` →
`http://localhost:5000`, ou Docker sans proxy TLS déjà configuré).

Ce bug était resté invisible jusqu'ici pour une raison précise, elle-même
un second bug : `run.py` forçait `debug=True` sur le serveur de
développement Flask **quel que soit** `FLASK_DEBUG`/`Config.DEBUG` — et
comme le hook de Talisman ne réécrit le cookie que `if not app.debug`,
ce premier bug masquait accidentellement le second en local. En
corrigeant uniquement le premier (`debug=True` en dur, un vrai risque de
sécurité : le débogueur interactif Werkzeug toujours actif, RCE
potentiel sur toute exception non gérée) sans corriger le second, la
correction aurait **cassé la connexion locale** pour quiconque n'a pas
explicitement `FLASK_DEBUG=true`. Les deux ont été corrigés ensemble
(`run.py` : `debug=app.config.get("DEBUG", False)` ;
`app/__init__.py` : `Talisman(..., session_cookie_secure=app.config.get("SESSION_COOKIE_SECURE", False))`),
avec un test manuel de bout en bout (connexion réelle, cookie inspecté,
`/dashboard` accessible après connexion) confirmant la correction avant
de lancer le test de charge lui-même.

## Résultats

10 secondes par endpoint sauf mention contraire, requêtes séquentielles
par thread (pas de pause entre requêtes - charge continue).

| Endpoint | Concurrence | Req. totales | Erreurs | req/s | p50 | p95 | p99 | max |
|---|---|---|---|---|---|---|---|---|
| `/health` | 10 | 2324 | 0 | 232.4 | 14.6 ms | 44.0 ms | 71.7 ms | 166.2 ms |
| `/login` (GET) | 10 | 1338 | 0 | 133.8 | 54.5 ms | 97.9 ms | 140.9 ms | 199.2 ms |
| `/dashboard` (auth) | 10 | 1059 | 0 | 105.9 | 75.5 ms | 113.6 ms | 154.7 ms | 207.3 ms |
| `/schedule` (auth) | 10 | 1108 | 0 | 110.8 | 73.7 ms | 115.2 ms | 163.9 ms | 219.8 ms |
| `/schedule` (auth) | 50 | 1176 | 0 | 117.6 | 408.5 ms | 491.0 ms | 683.3 ms | 760.6 ms |

**Zéro erreur sur l'ensemble des tests** (aucune requête en timeout,
aucune 5xx).

## Analyse

- `/health` (pas d'accès DB, juste un JSON statique) sert de référence :
  ~230 req/s, latence dominée par l'overhead HTTP/WSGI lui-même sur cette
  machine, pas par l'app.
- `/login` (GET, rendu de template + génération d'un token CSRF par
  requête) ajoute environ 40 ms de latence médiane par rapport à
  `/health` - cohérent avec le coût du rendu Jinja + la génération
  cryptographique du token CSRF par Flask-WTF, pas un signal d'alerte.
- `/dashboard` et `/schedule` (authentifiées, avec accès DB réel -
  agrégats, `joinedload` sur les shifts/astreintes de la période
  affichée) ajoutent encore ~20 ms par rapport à `/login` - cohérent
  avec une poignée de requêtes SQL par page sur SQLite, pas une
  dégradation inattendue.
- **Le point notable** : passer de 10 à 50 connexions concurrentes sur
  `/schedule` fait grimper la latence médiane de 74 ms à 409 ms (×5.5)
  pour un débit quasi identique (110.8 → 117.6 req/s, +6%) - signe clair
  de saturation, pas d'un problème applicatif : avec `--workers 1
  --threads 4`, seules 4 requêtes s'exécutent réellement en parallèle à
  tout instant, les 46 autres connexions simultanées attendent en file.
  C'est le comportement **attendu** de la configuration gunicorn
  documentée pour ce projet (un seul worker, léger, pensé pour une
  équipe utilisant l'app en interne - voir CLAUDE.md) et non un défaut
  de l'application elle-même : les mêmes 50 connexions contre plusieurs
  workers gunicorn (`--workers 4` par exemple) répartiraient la charge
  au lieu de la mettre en file.

## Limites de cette mesure

- Machine de développement partagée, pas un banc de test isolé - les
  chiffres absolus (ms, req/s) ne sont pas comparables à un futur
  environnement de production ; les **proportions** (facteur ×5.5 entre
  10 et 50 connexions, écart `/health` vs pages authentifiées) restent
  informatives.
- SQLite, pas PostgreSQL/MySQL - la base de données de production
  recommandée (voir CLAUDE.md "Configuration: two parallel systems") a un
  modèle de concurrence différent (verrouillage au niveau ligne, pas
  fichier) qui se comporterait probablement mieux sous forte concurrence
  en écriture. Ce test ne couvre que des routes en lecture.
- Pas de scénario d'écriture concurrente testé (création/modification de
  shifts) - out of scope pour cette passe, candidat pour un futur test
  de charge plus poussé si le besoin s'en fait sentir après un premier
  déploiement réel.
- Un seul worker gunicorn testé (`--workers 1`, la config documentée par
  défaut) - le palier de concurrence observé (facteur ×5.5 à 50
  connexions) est directement un artefact de ce choix, pas une limite de
  l'application ; passer à plusieurs workers reste la réponse standard
  si un déploiement réel constate une charge concurrente plus élevée que
  celle testée ici.

## Verdict

Aucune régression, aucune erreur, latences cohérentes avec le travail
réellement effectué par chaque endpoint. Le seul signal notable
(saturation à 50 connexions concurrentes avec un seul worker) est un
comportement attendu de la configuration par défaut, pas un problème de
code — documenté ici pour que l'équipe sache quel levier actionner
(`--workers`) si un déploiement réel dépasse la charge testée. Rien dans
ce test ne bloque la stabilisation v1.0.
