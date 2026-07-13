# 📋 Rapport - Tests E2E Playwright (navigateur réel)

**Branche** : `feature/e2e-playwright`
**PR** : [#104](https://github.com/FoxOps/leviia-schedule/pull/104) (draft)
**Date de début** : 2026-07-13
**Statut** : 🟢 Implémentation terminée, vérifiée en réel
**Base** : `main` (post refonte UI/UX, PR #103, commit `b881b3d`)

---

## 🎯 Décision : compléter, pas remplacer

`tests/e2e/test_user_flows.py` existant utilise le client de test Flask
(pas de vrai navigateur) - son propre docstring dit explicitement :
« Pas de navigateur headless réel (pas de Selenium/Playwright
disponible dans cet environnement de dev - pas de chromedriver/
geckodriver, pas de sudo) ». **Cette affirmation est fausse** :
`playwright install chromium` (sans `--with-deps`, qui lui nécessite
sudo) télécharge et installe un Chromium autonome sans droits root,
vérifié en pratique dans la session précédente (refonte UI/UX - a
permis de trouver 3 bugs CSP réels invisibles autrement).

**Décision : garder les tests E2E Flask existants ET ajouter une
nouvelle couche Playwright**, pas de remplacement :

- Les tests E2E Flask (client de test, pas de navigateur) restent
  utiles : rapides (pas de démarrage de navigateur), zéro dépendance
  lourde, bons pour vérifier permissions/redirections/données
  (ex: `TestUserRequestsLeave.test_user_cannot_request_leave_for_someone_else`).
- Les tests Playwright couvrent une catégorie de bug **structurellement
  invisible** au client de test Flask, car il n'exécute jamais de JS ni
  n'applique de CSS/CSP : c'est exactement la catégorie des 3 bugs
  trouvés manuellement lors de la refonte UI/UX (script inline bloqué
  par CSP sur 2 pages, police d'icônes FullCalendar bloquée par
  `font-src` manquant). Le but principal de cette PR est de transformer
  cette vérification manuelle ponctuelle en garde-fou de régression
  permanent.

## 🔍 Design

- **Dépendance optionnelle**, pas dans `requirements.txt` principal :
  `requirements-e2e.txt` (playwright seul). L'app tourne très bien sans.
- Tests marqués et **skip proprement** si playwright/chromium absent
  (`pytest.importorskip`) - `make test`/CI existant ne casse jamais,
  aucune obligation d'installer un navigateur pour contribuer au projet.
- Serveur Flask réel lancé dans un thread (pas le client de test) avec
  Talisman **réellement actif** (CSP appliquée pour de vrai, pas
  TestingConfig qui la désactive) - sinon les bugs CSP resteraient
  invisibles même avec un vrai navigateur.
- Priorité aux tests à forte valeur / faible flakiness : zéro erreur
  console sur les pages clés (généralise l'audit manuel), navbar burger
  mobile (JS pur, intestable côté serveur), thème sombre (localStorage,
  intestable côté serveur), copie presse-papiers ICS (vérifie le fix de
  la refonte UI/UX). Pas de tests drag & drop FullCalendar (fragile,
  faible valeur ajoutée vs effort).

## ⚠️ Limite

Ces tests nécessitent `pip install -r requirements-e2e.txt &&
playwright install chromium` en local pour s'exécuter - sinon ils sont
skippés (visible dans le résumé pytest comme `skipped`, pas caché).

---

## 📝 Journal

### Implémentation (commits `d01e9e4`, `6991b7d`, `0650b21`)

- `requirements-e2e.txt` : `playwright==1.61.0` + `pytest-playwright==0.8.0`
  (auto-enregistre les fixtures `page`/`browser`/`context`).
- `tests/e2e/conftest.py` : fixture `live_server_url` (module-scope) -
  lance un vrai `app.run()` dans un thread démon sur un port libre,
  Talisman réellement actif (CSP appliquée), CSRF désactivé (hors
  scope ici, déjà couvert par `test_security.py`), admin seedé avec
  des identifiants connus (`e2e-admin@leviia.local` /
  `e2e-password-123` - pas un mot de passe aléatoire comme
  `run.py`/`DEFAULT_ADMIN_PASSWORD`, qui avait piégé la vérification
  manuelle précédente : mot de passe généré à la volée, jamais loggé,
  connexion impossible sans le fixer explicitement).
- `tests/e2e/test_browser_flows.py` : login réel, burger mobile,
  thème sombre, **zéro erreur console sur 8 pages** (le garde-fou
  principal), bouton copier ICS.
- `.gitlab-ci/.gitlab-ci.yml` : job `run_e2e_browser` (image officielle
  `mcr.microsoft.com/playwright/python`, `allow_failure: true` le
  temps de prouver sa stabilité en CI réelle, n'affecte pas
  `run_tests`).
- `CLAUDE.md` mis à jour (commandes + section Testing conventions) -
  correction au passage : le docstring de `test_user_flows.py`
  affirmait à tort que Playwright n'était pas installable sans sudo
  dans cet environnement (faux, `playwright install chromium` sans
  `--with-deps` n'en a pas besoin).

### Vérifications réelles faites (pas seulement écrit et supposé correct)

1. **14/14 tests passent** en conditions réelles (Chromium installé
   dans `.venv`, serveur réel, CSP active).
2. **Le garde-fou détecte vraiment les régressions** : `font-src`
   temporairement retiré de `CSP_POLICY`, `test_page_has_no_console_errors[chromium-/]`
   échoue avec le message d'erreur console exact (violation CSP),
   remis en place, re-vérifié vert. Sans cette étape, rien ne
   garantissait que le test faisait autre chose que passer
   inconditionnellement.
3. **Skip propre confirmé** : suite installée dans un venv jetable
   sans `requirements-e2e.txt` - les 6 tests E2E Flask existants
   passent normalement, `test_browser_flows.py` devient exactement
   1 entrée `skipped` (pas 14 échecs, pas d'erreur de collecte).
4. Suite complète du projet (795 tests avec les 14 nouveaux) passe
   sans régression.
5. `--junitxml` généré avec succès en local (le flag utilisé dans le
   nouveau job CI fonctionne réellement, pas juste copié d'un autre
   job par analogie).

---

*Dernière mise à jour : 2026-07-13 — implémentation et vérifications
terminées. PR #104 en draft, prête pour revue.*
