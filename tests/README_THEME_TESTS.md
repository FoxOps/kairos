# Tests pour le Thème Visuel - Leviia Schedule

Ce dossier contient tous les tests relatifs au thème visuel de Leviia Schedule.

## 📁 Structure des Tests

```
tests/
├── test_dark_theme.py          # Tests existants pour le thème sombre
├── test_theme_fixes.py         # NOUVEAU: Tests pour les corrections apportées
├── manual_test_theme.py       # NOUVEAU: Script de tests manuels
└── README_THEME_TESTS.md      # Ce fichier
```

## 🧪 Tests Automatiques

### 1. Tests Existants (`test_dark_theme.py`)

Ces tests vérifient que le thème sombre est correctement configuré :

- **TestDarkThemeCSS** : Vérifie la présence et le contenu du fichier CSS
- **TestDarkThemeTemplate** : Vérifie l'inclusion des fichiers dans les templates
- **TestDarkThemeAccessibility** : Vérifie l'accessibilité (skip-link, ARIA)
- **TestDarkThemeVariables** : Vérifie les variables CSS Bulma
- **TestDarkThemeWCAGCompliance** : Vérifie la conformité WCAG

**Exécution :**
```bash
pytest tests/test_dark_theme.py -v
```

### 2. Tests des Corrections (`test_theme_fixes.py`)

Ces tests vérifient que les corrections apportées fonctionnent correctement :

#### **TestNoDuplicateStyles**
- ✅ Vérifie que `skip-link` n'est défini qu'une seule fois
- ✅ Vérifie que les styles FullCalendar ne sont pas dupliqués

#### **TestCentralizedJavaScript**
- ✅ Vérifie que `script.js` existe et contient `ThemeManager`
- ✅ Vérifie qu'il n'y a plus de JavaScript inline dans `base.html`

#### **TestCSSVariables**
- ✅ Vérifie que les variables `--bulma-grey*` ont été ajoutées
- ✅ Vérifie que `base-styles.css` contient les classes utilitaires

#### **TestInlineStylesReplacement**
- ✅ Vérifie qu'il n'y a plus de styles inline dans `base.html`
- ✅ Vérifie que `dashboard.html` utilise les classes `type-tag`
- ✅ Vérifie que `index.html` utilise les classes `min-w-*`

#### **TestFileStructure**
- ✅ Vérifie que tous les fichiers requis existent
- ✅ Vérifie que les fichiers CSS/JS sont inclus dans les templates

**Exécution :**
```bash
pytest tests/test_theme_fixes.py -v
```

### 3. Exécution de Tous les Tests

Pour exécuter tous les tests du thème visuel :

```bash
pytest tests/test_dark_theme.py tests/test_theme_fixes.py -v
```

**Résultat attendu :** 34 tests passés ✅

## 🧪 Tests Manuels

### Script de Test (`manual_test_theme.py`)

Ce script permet de vérifier manuellement les corrections sans démarrer le serveur :

```bash
python tests/manual_test_theme.py
```

**Fonctionnalités testées :**
- ✅ Structure des fichiers (CSS, JS, templates)
- ✅ Contenu des fichiers CSS
- ✅ Contenu du fichier JavaScript
- ✅ Contenu des templates
- ✅ Détection des duplications

### Tests Dynamiques (Navigateur)

Pour tester les fonctionnalités dynamiques, démarrez le serveur et testez dans le navigateur :

```bash
# Démarrer le serveur
python run.py
```

Puis naviguez sur **http://localhost:5000** et vérifiez :

#### 1. **Thème Sombre**
- [ ] Cliquez sur le bouton **lune/soleil** dans la navbar
- [ ] Vérifiez que le thème change instantanément
- [ ] Rafraîchissez la page : le thème doit persister
- [ ] Ouvrez un nouvel onglet : le thème doit être le même
- [ ] Changez les préférences système (OS) : le thème doit s'adapter

#### 2. **FullCalendar**
- [ ] Vérifiez que le calendrier s'affiche correctement
- [ ] Les événements (shifts, astreintes, congés) doivent avoir les bonnes couleurs
- [ ] En mode sombre, les couleurs doivent être adaptées
- [ ] Le drag & drop fonctionne (si admin)

#### 3. **Accessibilité**
- [ ] Appuyez sur **Tab** jusqu'à ce que le skip-link soit focus
- [ ] Appuyez sur **Entrée** : vous devriez être redirigé vers le contenu principal
- [ ] Vérifiez que tous les boutons ont des attributs `aria-label`

#### 4. **Cohérence Visuelle**
- [ ] Naviguez entre les pages (accueil, shifts, astreintes, congés, dashboard)
- [ ] Vérifiez que le thème est cohérent sur toutes les pages
- [ ] Vérifiez que les boutons, tableaux et cartes ont le même style

## 📊 Couverture des Tests

| Catégorie | Tests Automatiques | Tests Manuels |
|-----------|-------------------|---------------|
| **CSS** | ✅ 12 tests | ✅ 10 vérifications |
| **JavaScript** | ✅ 4 tests | ✅ 6 vérifications |
| **Templates** | ✅ 8 tests | ✅ 8 vérifications |
| **Duplications** | ✅ 4 tests | ✅ 4 vérifications |
| **Accessibilité** | ✅ 6 tests | ✅ 3 vérifications |
| **Total** | **34 tests** | **31 vérifications** |

## 🎯 Checklist de Validation

### Avant de Merger

- [x] Tous les tests automatiques passent (`pytest tests/test_dark_theme.py tests/test_theme_fixes.py -v`)
- [x] Le script de test manuel passe (`python tests/manual_test_theme.py`)
- [ ] Tests manuels dans le navigateur (voir section ci-dessus)
- [ ] Revue de code par un autre développeur

### Après le Merge

- [ ] Vérifier que les tests passent en CI
- [ ] Surveiller les erreurs en production
- [ ] Recueillir les feedbacks des utilisateurs

## 📝 Historique des Corrections

### PR #84 : Fix: Corrige les bugs et duplications du thème visuel

**Problèmes corrigés :**

1. **Styles CSS dupliqués**
   - `skip-link` était défini dans `base.html` (inline) et `dark-theme.css`
   - Styles FullCalendar étaient définis dans `index.html` (inline) et `dark-theme.css`
   - **Solution** : Centralisation dans des fichiers CSS dédiés

2. **JavaScript dupliqué**
   - Fonctions de gestion du thème (`applyTheme`, `getSystemTheme`, etc.) étaient inline dans `base.html`
   - **Solution** : Centralisation dans `script.js` avec la classe `ThemeManager`

3. **Variables CSS manquantes**
   - `var(--bulma-grey)` était utilisé mais non défini
   - **Solution** : Ajout des variables `--bulma-grey`, `--bulma-grey-light`, `--bulma-grey-dark`

4. **Styles inline**
   - Plusieurs éléments avaient des styles inline (`style="min-width: 180px"`, etc.)
   - **Solution** : Remplacement par des classes CSS (`.min-w-180`, `.d-none`, etc.)

**Fichiers modifiés :**
- `app/static/css/base-styles.css` (NOUVEAU)
- `app/static/css/fullcalendar-styles.css` (NOUVEAU)
- `app/static/css/dark-theme.css` (MODIFIÉ)
- `app/static/js/script.js` (MODIFIÉ)
- `app/templates/base.html` (MODIFIÉ)
- `app/templates/dashboard.html` (MODIFIÉ)
- `app/templates/index.html` (MODIFIÉ)

**Tests ajoutés :**
- `tests/test_theme_fixes.py` (NOUVEAU - 12 tests)
- `tests/manual_test_theme.py` (NOUVEAU - script de test manuel)

## 🔧 Dépannage

### Problème : Les tests échouent

1. **Vérifiez les dépendances :**
   ```bash
   pip install -r requirements.txt
   pip install pytest
   ```

2. **Vérifiez la configuration :**
   ```bash
   python -c "from app import app; print(app.config)"
   ```

3. **Exécutez les tests individuellement :**
   ```bash
   pytest tests/test_dark_theme.py::TestDarkThemeCSS -v
   pytest tests/test_theme_fixes.py::TestNoDuplicateStyles -v
   ```

### Problème : Le thème sombre ne fonctionne pas

1. **Vérifiez que les fichiers CSS sont chargés :**
   - Ouvrez les outils de développement (F12)
   - Vérifiez que `dark-theme.css`, `base-styles.css` et `fullcalendar-styles.css` sont chargés

2. **Vérifiez que le JavaScript est chargé :**
   - Vérifiez que `script.js` est chargé
   - Vérifiez qu'il n'y a pas d'erreurs dans la console

3. **Vérifiez le localStorage :**
   - Ouvrez la console et exécutez :
     ```javascript
     localStorage.getItem('theme')
     ```
   - Si la valeur est `null`, le thème système est utilisé
   - Si la valeur est `'dark'` ou `'light'`, c'est le thème sélectionné

### Problème : FullCalendar ne s'affiche pas correctement

1. **Vérifiez que le CSS est chargé :**
   - Ouvrez les outils de développement
   - Vérifiez que `fullcalendar-styles.css` est chargé

2. **Vérifiez que les classes sont appliquées :**
   - Inspectez un événement du calendrier
   - Vérifiez qu'il a les classes `.fc-event-shift`, `.fc-event-oncall` ou `.fc-event-leave`

3. **Vérifiez le thème sombre :**
   - Activez le thème sombre
   - Vérifiez que les sélecteurs `[data-theme="dark"]` sont appliqués

## 📚 Documentation Complémentaire

- [Analyse complète des bugs et duplications](https://github.com/FoxOps/leviia-schedule/issues/XX)
- [Documentation Bulma CSS](https://bulma.io/documentation/)
- [Documentation FullCalendar](https://fullcalendar.io/docs)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

---

**Dernière mise à jour :** 2026-06-26  
**Auteur :** Vibe Code (Mistral AI)  
**PR associée :** [#84](https://github.com/FoxOps/leviia-schedule/pull/84)
