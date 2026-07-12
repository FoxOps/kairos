# 📋 Rapport - Tests E2E Playwright (navigateur réel)

**Branche** : `feature/e2e-playwright`
**PR** : à créer
**Date de début** : 2026-07-13
**Statut** : 🟡 En cours
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

*(mis à jour à chaque étape)*

---

*Dernière mise à jour : 2026-07-13*
