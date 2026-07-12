# 📋 Rapport - Refonte UI/UX : Design moderne et responsive

**Branche** : `feature/ui-ux-refonte`
**PR** : à créer
**Date de début** : 2026-07-12
**Statut** : 🟡 En cours
**Base** : `main` (post refonte Phases 1-6, commit `ae1c091`)

---

## 🎯 Portée (validée avec l'utilisateur)

- Garder Bulma 1.0.4 (déjà récent, pas de bug technique justifiant un
  changement de framework) mais aller au-delà des simples corrections :
  refonte visuelle profonde (palette, typographie, layout, cards,
  espacements) — pas juste des fixes ciblés.
- Corriger en priorité le vrai bug responsive trouvé à l'audit : menu de
  navigation mobile inutilisable (voir ci-dessous).
- Audit complet des breakpoints sur toutes les pages, pas seulement la
  navbar.

## 🔍 Audit initial

### Bug réel trouvé : navbar mobile inutilisable

`app/templates/base.html` a un `<nav class="navbar ...">` avec
`.navbar-menu` (7 liens + dropdown utilisateur) mais **aucun bouton
`.navbar-burger`** nulle part dans le template, ni logique JS pour
toggle `is-active`. Or Bulma masque `.navbar-menu` par défaut sous
1024px (`display: none`) tant que `.navbar-menu.is-active` n'est pas
appliqué. Résultat : sur mobile/tablette, le menu de navigation est
**invisible et totalement inaccessible** - aucun moyen d'atteindre
Shifts/Astreintes/Congés/Admin/Profil/Déconnexion. Confirmé par
recherche exhaustive (`grep -n "burger" base.html app/static/js/`) :
zéro résultat.

### État du design system

- `app/static/css/variables.css` ne fait que mapper les `--bulma-*`
  vers des noms d'app (`--color-primary`, etc.) sans aucune
  personnalisation - couleur primaire = turquoise par défaut de Bulma
  (`--bulma-primary-h: 171deg`), pas de palette de marque.
- Pas d'échelle d'espacement (spacing scale) ni de rayons de bordure
  cohérents définis en dehors des défauts Bulma bruts.
- Bulma 1.0.4 charge déjà `Inter` comme police par défaut
  (`--bulma-family-primary`), mais aucun fichier de police n'est
  vendorisé (`app/static/vendor/webfonts/` ne contient que Font
  Awesome) - `Inter` retombe donc silencieusement sur les polices
  système (SF Pro/Segoe UI/Roboto selon l'OS). Pas un bug (dégradation
  propre), mais noté : vendoriser Inter serait un vrai gain visuel,
  hors périmètre de cette passe (ajout d'assets, licence à vérifier) -
  **reporté**, voir section Reporté plus bas.
- CSS déjà bien organisée en couches (`base`, `components/`, `layout/`,
  `pages/`, `themes/dark.css`, `utilities.css`) - la structure est
  gardée telle quelle, seul le contenu est retouché.
- Bulma 1.x re-thème via 3 variables HSL (`--bulma-primary-h/-s/-l`),
  toutes les nuances dérivées (00 à 100, invert, etc.) sont calculées
  automatiquement par Bulma - c'est la bonne façon d'overrider,
  beaucoup plus robuste que de redéfinir chaque nuance à la main.

## 📐 Plan

1. Corriger le burger menu mobile (bug bloquant, priorité 1)
2. Nouvelle palette de marque (HSL override du primary Bulma - indigo
   moderne plutôt que le turquoise par défaut), échelle de rayons plus
   arrondie
3. Rafraîchir les composants : boutons, cards, formulaires, tables,
   modales (ombres, rayons, espacements cohérents avec la nouvelle
   palette)
4. Vérifier la cohérence du thème sombre avec la nouvelle palette
5. Audit responsive complet (tables sur mobile, dashboard, formulaires,
   calendrier) sur les pages principales (index, schedule, oncall,
   leave, admin)
6. Polish layout (header, footer, spacing global)

## ⚠️ Limite de vérification

Aucun outil de rendu/capture d'écran de navigateur disponible dans cet
environnement. Vérification faite par : serveur de développement réel +
`curl` (statut HTTP, présence des classes/attributs attendus dans le
HTML rendu), validité syntaxique CSS/JS, cohérence des variables. **Pas
de vérification visuelle pixel par pixel** - à faire manuellement dans
un navigateur avant merge.

---

## 📝 Journal

*(mis à jour à chaque étape)*

---

*Dernière mise à jour : 2026-07-12*
