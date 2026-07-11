# Analyse du Frontend - Leviia Schedule

## Sommaire
- [Problèmes de duplication](#problèmes-de-duplication)
- [Incohérences](#incohérences)
- [Améliorations possibles](#améliorations-possibles)
- [Corrections apportées](#corrections-apportées)

---

## Problèmes de duplication

### 1. CSS - Classes utilitaires dupliquées

**Fichiers concernés :**
- `app/static/css/base-styles.css` (lignes 400-450)
- `app/static/css/dark-theme.css` (lignes 40-60)

**Problème :**
Les classes utilitaires suivantes sont définies dans les deux fichiers :
- `.gap-0` à `.gap-5`
- `.min-w-80`, `.min-w-140`, `.min-w-150`, `.min-w-180`, `.min-w-200`
- `.w-80`, `.w-100`
- `.mb-0` à `.mb-5`
- `.d-none`, `.d-block`, `.d-flex`, `.d-inline`, `.d-inline-block`
- `.visible`, `.invisible`

**Solution :**
Conserver ces classes uniquement dans `base-styles.css` et les supprimer de `dark-theme.css`.

### 2. CSS - Styles de focus dupliqués

**Fichiers concernés :**
- `app/static/css/base-styles.css` (lignes 30-80)
- `app/static/css/dark-theme.css` (lignes 200-230)

**Problème :**
Les styles pour `:focus-visible` sont définis dans les deux fichiers avec des sélecteurs similaires.

**Solution :**
Centraliser tous les styles de focus dans `base-styles.css` et ne garder dans `dark-theme.css` que les surcharges spécifiques au thème sombre.

### 3. CSS - Styles de notification dupliqués

**Fichiers concernés :**
- `app/static/css/base-styles.css` (lignes 200-220, 500-520)
- `app/static/css/dark-theme.css` (lignes 100-130)

**Problème :**
Les styles pour `.notification` apparaissent deux fois dans `base-styles.css` et sont aussi dans `dark-theme.css`.

**Solution :**
Supprimer les doublons dans `base-styles.css` et garder une seule définition cohérente.

### 4. HTML - Légendes des actions dupliquées

**Fichiers concernés :**
- `app/templates/schedule.html` (lignes 135-148)
- `app/templates/oncall.html` (lignes 95-107)
- `app/templates/leave.html` (lignes 70-77)

**Problème :**
Chaque template a une section "Légende des actions" très similaire avec des boutons d'exemple.

**Solution :**
Créer un template partiel `_action_legend.html` réutilisable.

### 5. HTML - Boutons d'export ICS dupliqués

**Fichiers concernés :**
- `app/templates/index.html` (lignes 25-35)
- `app/templates/schedule.html` (lignes 20-26)
- `app/templates/oncall.html` (lignes 19-25)
- `app/templates/leave.html` (lignes 19-25)
- `app/templates/admin/dashboard.html` (lignes 92-100)

**Problème :**
Les boutons d'export ICS sont dupliqués dans plusieurs templates avec des variations mineures.

**Solution :**
Créer un template partiel `_ics_export_buttons.html` réutilisable.

### 6. HTML - Structure des tableaux similaire

**Fichiers concernés :**
- `app/templates/schedule.html`
- `app/templates/oncall.html`
- `app/templates/leave.html`

**Problème :**
La structure des tableaux (conteneur, caption, thead, tbody) est très similaire.

**Solution :**
Créer des classes CSS communes et éventuellement un macro Jinja2 pour les tableaux.

### 7. JavaScript - Code dupliqué dans les confirmations

**Fichier concerné :**
- `app/templates/schedule.html` (lignes 90-130)
- `app/templates/oncall.html` (lignes 70-85)
- `app/templates/leave.html` (ligne 57)

**Problème :**
Les appels à `confirm()` ou `Leviia.confirmActionAccessible()` sont dupliqués avec des messages similaires.

**Solution :**
Utiliser systématiquement `Leviia.confirmActionAccessible()` et standardiser les messages.

---

## Incohérences

### 1. Utilisation de `aria-label`

**Problème :**
- Certains boutons ont `aria-label`
- D'autres ont `title`
- Certains n'ont ni l'un ni l'autre

**Exemples :**
- `schedule.html` ligne 15 : `aria-label="Ajouter un nouveau shift"`
- `schedule.html` ligne 21 : `aria-label="Exporter tous les shifts au format iCalendar"`
- `leave.html` ligne 20 : `title="Exporter tous les congés"` (pas de aria-label)

**Solution :**
Standardiser sur `aria-label` pour tous les éléments interactifs et ajouter `title` comme fallback.

### 2. Classes Bulma incohérentes

**Problème :**
- Certains templates utilisent `is-flex` + `is-flex-wrap-wrap`
- D'autres utilisent `is-flex is-flex-wrap-nowrap`
- Certains n'utilisent pas les classes Bulma du tout

**Solution :**
Standardiser sur l'utilisation des classes Bulma natives.

### 3. Structure HTML incohérente

**Problème :**
- Certains templates ont `<main role="main">`
- D'autres non
- Certains ont des sections avec `aria-labelledby`
- D'autres non

**Solution :**
Standardiser la structure HTML avec des rôles ARIA cohérents.

### 4. Utilisation de `role="group"`

**Problème :**
- `schedule.html` utilise `role="group"` pour les boutons
- `oncall.html` ne l'utilise pas
- `leave.html` ne l'utilise pas

**Solution :**
Ajouter `role="group"` à tous les groupes de boutons.

### 5. Messages de confirmation incohérents

**Problème :**
- Certains utilisent `confirm()` natif
- D'autres utilisent `Leviia.confirmActionAccessible()`
- Les messages varient (majuscules, ponctuation)

**Exemples :**
- `oncall.html` ligne 29 : `confirm('Êtes-vous SÛR de vouloir supprimer TOUTES les astreintes ?')`
- `schedule.html` ligne 32 : `Leviia.confirmActionAccessible('Êtes-vous SÛR de vouloir supprimer TOUS les shifts ?')`

**Solution :**
Utiliser systématiquement `Leviia.confirmActionAccessible()` avec des messages standardisés.

---

## Améliorations possibles

### 1. CSS

1. **Centraliser les variables CSS**
   - Créer un fichier `_variables.css` avec toutes les variables
   - Importer ce fichier dans tous les autres fichiers CSS

2. **Organiser le CSS par composants**
   - Créer des fichiers séparés pour :
     - `buttons.css`
     - `tables.css`
     - `forms.css`
     - `cards.css`
     - `modals.css`

3. **Utiliser des mixins Sass**
   - Convertir le CSS en SCSS pour utiliser des mixins
   - Réduire la duplication de code

### 2. HTML/Templates

1. **Créer des templates partiels**
   - `_action_legend.html`
   - `_ics_export_buttons.html`
   - `_table_container.html`
   - `_pagination.html` (déjà existe)

2. **Utiliser des macros Jinja2**
   - Pour les formulaires répétitifs
   - Pour les tableaux
   - Pour les cartes de statistiques

3. **Améliorer l'accessibilité**
   - Ajouter `aria-label` à tous les éléments interactifs
   - Ajouter `aria-describedby` où nécessaire
   - Vérifier l'ordre de tabulation

### 3. JavaScript

1. **Centraliser la logique de confirmation**
   - Utiliser systématiquement `Leviia.confirmActionAccessible()`
   - Standardiser les messages

2. **Améliorer la gestion des erreurs**
   - Utiliser `Leviia.announceToScreenReader()` pour toutes les erreurs
   - Standardiser les messages d'erreur

3. **Optimiser les écouteurs d'événements**
   - Utiliser la délégation d'événements où possible
   - Éviter les duplications de code

---

## Corrections apportées

### 1. CSS

- [ ] Suppression des classes utilitaires dupliquées dans `dark-theme.css`
- [ ] Suppression des styles de notification dupliqués dans `base-styles.css`
- [ ] Centralisation des styles de focus dans `base-styles.css`
- [ ] Organisation du CSS par sections claires

### 2. HTML/Templates

- [ ] Création de `_action_legend.html`
- [ ] Création de `_ics_export_buttons.html`
- [ ] Standardisation de l'utilisation de `aria-label`
- [ ] Standardisation de l'utilisation de `role="group"`
- [ ] Standardisation de la structure HTML

### 3. JavaScript

- [ ] Remplacement de tous les `confirm()` par `Leviia.confirmActionAccessible()`
- [ ] Standardisation des messages de confirmation
- [ ] Optimisation des écouteurs d'événements

---

## Statistiques

- **Fichiers HTML analysés :** 46
- **Lignes de code HTML :** ~4676
- **Fichiers CSS analysés :** 3
- **Lignes de code CSS :** ~24843
- **Fichiers JS analysés :** 1
- **Lignes de code JS :** 673

---

## Outils utilisés

- `grep` pour rechercher les duplications
- `wc` pour compter les lignes
- Analyse manuelle des fichiers
