# Rapport d'Analyse : Système de Configuration TOML pour l'Automatisation des Astreintes et Shifts

**Branche analysée :** `config/automation-toml`  
**Date :** 21 juin 2026  
**Auteur :** Vibe Code Agent

---

## 📋 Sommaire

1. [Introduction et Contexte](#1-introduction-et-contexte)
2. [Architecture du Système de Configuration](#2-architecture-du-système-de-configuration)
3. [Analyse des Composants](#3-analyse-des-composants)
4. [Points Forts du Système Actuel](#4-points-forts-du-système-actuel)
5. [Axes d'Amélioration](#5-axes-damélioration)
6. [Recommandations Prioritaires](#6-recommandations-prioritaires)
7. [Conclusion](#7-conclusion)

---

## 1. Introduction et Contexte

Le système Leviia Schedule a récemment migré vers une architecture de configuration centralisée basée sur **TOML** pour gérer les règles d'automatisation des astreintes (on-call) et des shifts. Cette migration vise à :

- **Externaliser** la configuration des règles métiers hors du code source
- **Centraliser** la gestion des paramètres dans un fichier unique (`automation_rules.toml`)
- **Faciliter** la modification des règles via l'interface d'administration
- **Synchroniser** automatiquement la base de données avec la configuration

La branche `config/automation-toml` contient l'implémentation complète de ce système.

---

## 2. Architecture du Système de Configuration

### 2.1 Structure des Fichiers

```
app/config/
├── __init__.py                    # Module vide pour namespace
├── automation_rules.toml          # Fichier de configuration principal
├── automation_rules.py            # Module de gestion de la configuration
└── migration.py                    # Module de migration et validation

app/utils/
├── automation.py                  # Automatisation de base (astreintes et shifts)
└── advanced_shift_automation.py   # Règles métiers avancées

app/routes/
└── admin.py                       # Routes d'administration avec intégration TOML
```

### 2.2 Flux de Données

```mermaid
flowchart TD
    A[automation_rules.toml] -->|load()| B[AutomationConfig]
    B -->|get_*_rules()| C[Modules d'automatisation]
    C -->|Génération| D[Base de données]
    D -->|sync_*_to_toml()| A
    E[Interface Admin] -->|Modifications| A
    E -->|Actions| C
```

### 2.3 Sections de Configuration

Le fichier `automation_rules.toml` contient 4 sections principales :

1. **`[oncall]`** : Configuration des astreintes
   - `rotation_order` : Ordre de rotation des utilisateurs
   - `min_days_between_oncalls` : Contrainte légale (14 jours par défaut)
   - `start_day`, `start_hour` : Début de l'astreinte (vendredi 21h)
   - `end_day`, `end_hour` : Fin de l'astreinte (vendredi suivant 07h)

2. **`[shifts]`** : Configuration des shifts
   - `shift_types` : Liste des types de shifts disponibles
   - `rules` : Règles d'assignation avec priorité
   - `work_days` : Jours de travail (0-4 = lundi-vendredi)
   - `daily_requirements` : Besoins quotidiens par type de shift

3. **`[groups]`** : Configuration des groupes
   - `schedule_groups` : Groupes éligibles pour les shifts
   - `oncall_groups` : Groupes éligibles pour les astreintes

4. **`[generation]`** : Paramètres de génération
   - `default_period_days` : Période par défaut (180 jours)
   - `advance_generation_enabled` : Génération automatique à l'avance
   - `rebalance_on_leave_change` : Rééquilibrage automatique

---

## 3. Analyse des Composants

### 3.1 `automation_rules.py` - Module de Configuration

**Fonctionnalités clés :**
- ✅ Chargement de la configuration depuis le fichier TOML
- ✅ Fusion avec les valeurs par défaut (`DEFAULT_CONFIG`)
- ✅ Méthodes d'accès par section (`get_oncall_rules()`, `get_shift_rules()`, etc.)
- ✅ Méthodes utilitaires pour les calculs (durée, dates de début/fin)
- ✅ Synchronisation bidirectionnelle avec la base de données
- ✅ Rechargement dynamique (`reload()`)

**Mécanisme de fusion :**
```python
# _merge_with_defaults() fusionne la config chargée avec DEFAULT_CONFIG
merged = DEFAULT_CONFIG.copy()
for section in DEFAULT_CONFIG.keys():
    if section in config:
        if isinstance(DEFAULT_CONFIG[section], dict):
            merged[section].update(config[section])
        else:
            merged[section] = config[section]
```

**Synchronisation avec la base :**
- `sync_groups_to_toml()` : Met à jour le TOML depuis les groupes DB
- `sync_shift_types_to_toml()` : Met à jour le TOML depuis les types de shifts DB
- `sync_shift_types_from_toml()` : Met à jour la DB depuis le TOML

### 3.2 `migration.py` - Migration et Validation

**DatabaseConfigMigrator :**
- Extraction de la configuration depuis la base de données
- Migration vers le format TOML
- Synchronisation bidirectionnelle

**ConfigValidator :**
- Validation de chaque section (`validate_oncall_config`, `validate_shift_config`, etc.)
- Validation complète (`validate_all`)
- Retourne un tuple `(bool, List[str])` avec le statut et les erreurs

**Points forts :**
- Validation complète avant sauvegarde
- Messages d'erreur clairs et localisés
- Prise en compte des contraintes métiers (heures valides, jours valides, etc.)

### 3.3 `automation.py` - Automatisation de Base

**OnCallAutomation :**
- Génération des astreintes avec rotation
- Vérification des contraintes légales (`check_oncall_constraint`)
- Recherche des utilisateurs disponibles (`find_next_available_user`)
- Prise en compte de l'ordre de rotation personnalisé

**ShiftAutomation :**
- Génération des shifts selon les règles métiers
- Vérification des disponibilités (`can_assign_shift`)
- Recherche de remplaçants (`find_replacement_user`)
- Gestion des conflits (congés, astreintes existantes)

**Fonctions utilitaires :**
- `generate_full_schedule()` : Génération complète (astreintes + shifts)
- `get_automation_status()` : État actuel de l'automatisation

### 3.4 `advanced_shift_automation.py` - Règles Métiers Avancées

**Règles implémentées :**
1. **Règle 1** (`oncall_has_evening_shift`) : La personne en astreinte a le shift 13h-21h (si dans groupe schedule)
2. **Règle 2** (`rotation_after_oncall`) : Après une astreinte, l'utilisateur a le shift 07h-15h la semaine suivante
3. **Règle 3** (`default_shift`) : Shift par défaut 09h-17h
4. **Règle 4** (`two_users_special_case`) : Avec 2 utilisateurs, la personne NON d'astreinte a le shift 07h-15h

**Fonctionnalités avancées :**
- `rebalance_after_leave()` : Rééquilibrage automatique après modification de congé
- `generate_daily_shifts()` : Génération jour par jour avec application des règles
- `determine_shift_for_user()` : Détermination du créneau selon les règles activées

### 3.5 Intégration dans l'Interface d'Administration

**Routes principales :**
- `/admin/automation` : Tableau de bord
- `/admin/automation/config` : Configuration des règles (GET/POST)
- `/admin/automation/full` : Génération complète avec ordre de rotation
- `/admin/automation/shifts` : Génération des shifts
- `/admin/automation/refresh-shifts` : Rafraîchissement des shifts
- `/admin/automation/status` : État de l'automatisation

**Fonctionnalités :**
- Modification de l'ordre de rotation via drag-and-drop
- Sauvegarde automatique dans le TOML
- Dry run pour prévisualisation
- Synchronisation automatique lors des modifications de groupes/types de shifts

---

## 4. Points Forts du Système Actuel

### ✅ **Architecture Modulaire**
- Séparation claire des responsabilités (configuration, automatisation, validation)
- Modules bien organisés et documentés
- Réutilisabilité du code

### ✅ **Configuration Centralisée**
- Toutes les règles dans un seul fichier TOML
- Facile à modifier et à versionner
- Valeurs par défaut intégrées

### ✅ **Synchronisation Bidirectionnelle**
- Base de données → TOML (groupes, types de shifts)
- TOML → Base de données (types de shifts)
- Mécanisme de migration pour les données existantes

### ✅ **Validation Robuste**
- Validation avant sauvegarde
- Messages d'erreur clairs
- Prise en compte des contraintes métiers

### ✅ **Flexibilité des Règles**
- Règles activables/désactivables
- Priorité configurable
- Possibilité d'ajouter de nouvelles règles

### ✅ **Interface d'Administration Complète**
- Configuration via formulaire web
- Prévisualisation (dry run)
- Génération manuelle et automatique

### ✅ **Gestion des Conflits**
- Vérification des congés
- Vérification des astreintes existantes
- Recherche de remplaçants

### ✅ **Historique et Audit**
- Les modifications sont traçables via git (fichier TOML versionné)
- Messages de log clairs dans les routes admin

---

## 5. Axes d'Amélioration

### 🔴 **Problèmes Critiques**

#### 5.1.1 Gestion des Erreurs Silencieuses

**Problème :** Plusieurs méthodes utilisent `try/except` avec `pass` ou ne remontent pas les erreurs.

**Exemples :**
```python
# Dans automation_rules.py
try:
    AutomationConfig.sync_groups_to_toml()
except Exception as e:
    pass  # ❌ Erreur silencieuse

# Dans migration.py
try:
    # ...
except Exception as e:
    db.session.rollback()
    pass  # ❌ Erreur silencieuse
```

**Impact :**
- Difficile de déboguer
- L'utilisateur n'est pas informé des échecs de synchronisation
- Risque de désynchronisation silencieuse entre DB et TOML

**Solution :**
- Logger les erreurs avec `app.logger.error()` ou `app.logger.warning()`
- Remonter les exceptions critiques
- Utiliser un système de notifications pour les erreurs non bloquantes

---

#### 5.1.2 Problème de Concurrence

**Problème :** Aucune gestion de la concurrence pour l'accès au fichier TOML.

**Exemples :**
- Plusieurs requêtes peuvent modifier le fichier simultanément
- Risque de corruption du fichier TOML
- Problème de race condition entre lecture/écriture

**Impact :**
- Données corrompues
- Incohérence entre la configuration en mémoire et le fichier
- Comportement imprévisible

**Solution :**
- Utiliser un verrou (`threading.Lock` ou `filelock`)
- Implémenter un mécanisme de verrouillage optimiste
- Utiliser une base de données pour la configuration (option alternative)

---

#### 5.1.3 Problème de Cache

**Problème :** La configuration est chargée une fois et mise en cache dans `_config`.

**Exemples :**
```python
class AutomationConfig:
    _config = None  # ❌ Cache statique
    
    @classmethod
    def load(cls) -> Dict[str, Any]:
        if cls._config is None:
            # Charger depuis le fichier
            cls._config = toml.load(f)
        return cls._config
```

**Impact :**
- Les modifications du fichier TOML ne sont pas prises en compte sans redémarrage
- `reload()` doit être appelé manuellement après chaque modification
- Risque de désynchronisation si le fichier est modifié directement

**Solution :**
- Implémenter un cache avec durée de vie (TTL)
- Vérifier la date de modification du fichier avant de retourner le cache
- Utiliser un observateur de fichiers (`watchdog`)

---

### 🟡 **Problèmes Majeurs**

#### 5.2.1 Validation Incomplète

**Problème :** La validation ne couvre pas tous les cas.

**Exemples :**
- Pas de validation que les groupes référencés existent en base
- Pas de validation que les utilisateurs dans `rotation_order` existent
- Pas de validation des chevauchements de shifts types
- Pas de validation que `end_day` >= `start_day` pour les astreintes

**Impact :**
- Configuration invalide peut être sauvegardée
- Erreurs à l'exécution
- Comportement inattendu

**Solution :**
- Ajouter des validations supplémentaires dans `ConfigValidator`
- Valider l'existence des entités référencées
- Valider la cohérence des règles (ex : pas de conflit entre règles)

---

#### 5.2.2 Synchronisation Partielle

**Problème :** La synchronisation ne couvre pas tous les éléments.

**Exemples :**
- Les utilisateurs ne sont pas synchronisés avec le TOML
- L'ordre de rotation n'est pas synchronisé avec la base
- Les astreintes existantes ne sont pas prises en compte dans la configuration

**Impact :**
- Désynchronisation entre DB et TOML
- Configuration incomplète
- Difficile de migrer vers un nouveau système

**Solution :**
- Implémenter une synchronisation complète
- Ajouter des méthodes pour synchroniser les utilisateurs
- Documenter clairement ce qui est synchronisé et ce qui ne l'est pas

---

#### 5.2.3 Problème de Performance

**Problème :** Certaines opérations sont coûteuses et peuvent impacter les performances.

**Exemples :**
- `sync_shift_types_from_toml()` : Supprime et recrée tous les types de shifts
- `rebalance_after_leave()` : Régénère tous les shifts pour une période
- `generate_full_schedule()` : Génération complète peut être lente

**Impact :**
- Latence pour l'utilisateur
- Charge sur la base de données
- Risque de timeout

**Solution :**
- Implémenter des opérations incrémentales
- Utiliser des transactions pour les opérations groupées
- Ajouter des index sur les colonnes fréquemment interrogées
- Implémenter un système de cache pour les résultats de génération

---

#### 5.2.4 Problème de Sécurité

**Problème :** Certaines validations sont manquantes ou insuffisantes.

**Exemples :**
- Pas de validation des permissions pour les modifications de configuration
- Pas de protection contre les injections TOML
- Pas de validation de la taille des listes (ex : `rotation_order` trop long)

**Impact :**
- Risque de modification non autorisée
- Risque d'injection de code
- Déni de service possible

**Solution :**
- Ajouter des vérifications de permissions
- Valider la taille des entrées
- Utiliser une bibliothèque de parsing TOML sécurisée
- Sanitizer les entrées utilisateur

---

#### 5.2.5 Problème de Documentation

**Problème :** La documentation est incomplète ou obsolète.

**Exemples :**
- Pas de documentation sur le format TOML attendu
- Pas de documentation sur les valeurs par défaut
- Pas de documentation sur les règles métiers
- Commentaires en anglais dans certains fichiers, en français dans d'autres

**Impact :**
- Difficile pour les nouveaux développeurs
- Risque de mauvaise configuration
- Maintenance plus complexe

**Solution :**
- Documenter le format TOML dans un README dédié
- Ajouter des docstrings complètes
- Standardiser la langue des commentaires
- Ajouter des exemples de configuration

---

### 🟢 **Problèmes Mineurs**

#### 5.3.1 Incohérence des Noms

**Problème :** Certains noms sont incohérents ou peu clairs.

**Exemples :**
- `automation_rules.toml` vs `automation_rules.py` (nom similaire mais rôle différent)
- `BusinessRules` dans `automation.py` vs règles dans TOML
- `AdvancedShiftAutomation` vs `ShiftAutomation` (différence pas claire)

**Impact :**
- Confusion pour les développeurs
- Difficile de comprendre l'architecture

**Solution :**
- Renommer les fichiers/modules pour plus de clarté
- Utiliser des noms plus descriptifs
- Documenter clairement le rôle de chaque composant

---

#### 5.3.2 Duplication de Code

**Problème :** Certaines fonctionnalités sont dupliquées.

**Exemples :**
- `get_eligible_users()` existe dans `OnCallAutomation` et `ShiftAutomation`
- `get_oncall_user_for_date()` existe dans `AdvancedShiftAutomation` et pourrait être dans `OnCallAutomation`
- Logique de vérification des congés dupliquée

**Impact :**
- Maintenance plus complexe
- Risque d'incohérence
- Code moins DRY

**Solution :**
- Extraire le code commun dans des classes de base
- Utiliser l'héritage ou la composition
- Centraliser la logique commune

---

#### 5.3.3 Tests Insuffisants

**Problème :** La couverture de tests est incomplète.

**Exemples :**
- Pas de tests pour `automation_rules.py`
- Pas de tests pour `migration.py`
- Tests limités pour `AdvancedShiftAutomation`
- Pas de tests d'intégration

**Impact :**
- Risque de régression
- Difficile de valider les modifications
- Qualité du code moins garantie

**Solution :**
- Ajouter des tests unitaires pour tous les modules
- Ajouter des tests d'intégration
- Implémenter des tests de validation de configuration
- Utiliser pytest pour une meilleure couverture

---

#### 5.3.4 Configuration par Défaut Incomplète

**Problème :** Certaines valeurs par défaut sont manquantes ou incohérentes.

**Exemples :**
- `DEFAULT_CONFIG` dans `automation_rules.py` ne couvre pas tous les cas
- Certaines clés peuvent être manquantes dans le TOML
- Pas de validation que toutes les clés nécessaires sont présentes

**Impact :**
- Comportement inattendu si une clé est manquante
- Difficile de savoir quelles clés sont obligatoires

**Solution :**
- Compléter `DEFAULT_CONFIG` avec toutes les valeurs possibles
- Documenter les clés obligatoires vs optionnelles
- Ajouter une validation que toutes les clés nécessaires sont présentes

---

#### 5.3.5 Gestion des Versions

**Problème :** Aucune gestion des versions de configuration.

**Exemples :**
- Impossible de revenir à une version précédente
- Impossible de comparer les modifications
- Impossible de savoir quand une configuration a été modifiée

**Impact :**
- Difficile de déboguer les problèmes de configuration
- Risque de perte de configuration
- Pas d'historique des modifications

**Solution :**
- Versionner le fichier TOML avec git
- Ajouter un champ `version` ou `last_modified` dans la configuration
- Implémenter un système de backup automatique
- Ajouter un historique des modifications dans la base de données

---

#### 5.3.6 Internationalisation

**Problème :** Le système mélange français et anglais.

**Exemples :**
- Noms des règles en anglais (`oncall_has_evening_shift`)
- Descriptions en français
- Messages de log en français
- Interface admin en français

**Impact :**
- Incohérence pour les utilisateurs
- Difficile à maintenir

**Solution :**
- Standardiser sur une seule langue (préférentiellement français)
- Utiliser un système d'internationalisation (i18n)
- Externaliser les messages dans des fichiers de traduction

---

## 6. Recommandations Prioritaires

### 🎯 **Priorité 1 : Corrections Critiques**

| ID | Action | Complexité | Impact | Responsable |
|----|--------|------------|--------|-------------|
| R1.1 | Ajouter du logging pour toutes les erreurs silencieuses | Faible | Élevé | Développeur |
| R1.2 | Implémenter un mécanisme de verrouillage pour le fichier TOML | Moyenne | Élevé | Développeur |
| R1.3 | Implémenter un cache avec TTL ou vérification de date de modification | Moyenne | Élevé | Développeur |

### 🎯 **Priorité 2 : Améliorations Majeures**

| ID | Action | Complexité | Impact | Responsable |
|----|--------|------------|--------|-------------|
| R2.1 | Compléter la validation (groupes existants, utilisateurs existants) | Moyenne | Élevé | Développeur |
| R2.2 | Implémenter une synchronisation complète bidirectionnelle | Élevée | Élevé | Développeur |
| R2.3 | Optimiser les opérations de génération et synchronisation | Moyenne | Moyen | Développeur |
| R2.4 | Ajouter des vérifications de permissions | Faible | Moyen | Développeur |

### 🎯 **Priorité 3 : Améliorations Mineures**

| ID | Action | Complexité | Impact | Responsable |
|----|--------|------------|--------|-------------|
| R3.1 | Standardiser les noms des modules et classes | Faible | Faible | Développeur |
| R3.2 | Éliminer la duplication de code | Moyenne | Moyen | Développeur |
| R3.3 | Ajouter des tests unitaires et d'intégration | Moyenne | Moyen | Développeur |
| R3.4 | Compléter la configuration par défaut | Faible | Faible | Développeur |
| R3.5 | Implémenter un système de versionnage de configuration | Moyenne | Faible | Développeur |
| R3.6 | Standardiser la langue (français) | Faible | Faible | Développeur |

---

## 7. Conclusion

Le système de configuration TOML pour l'automatisation des astreintes et shifts dans Leviia Schedule représente une **amélioration significative** par rapport à une configuration hardcodée. L'architecture est **modulaire, flexible et bien conçue**, avec une bonne séparation des responsabilités.

Cependant, plusieurs **problèmes critiques** doivent être adressés en priorité :
1. **Gestion des erreurs silencieuses** - Risque de désynchronisation et difficulté de débogage
2. **Concurence** - Risque de corruption des données
3. **Cache statique** - Configuration non mise à jour automatiquement

Une fois ces problèmes résolus, des **améliorations majeures** peuvent être apportées pour renforcer la robustesse, la performance et la maintenabilité du système.

**Recommandation globale :**
- **Phase 1 (Urgent)** : Corriger les problèmes critiques (R1.1, R1.2, R1.3)
- **Phase 2 (Important)** : Implémenter les améliorations majeures (R2.1, R2.2, R2.3)
- **Phase 3 (Amélioration continue)** : Traiter les problèmes mineurs (R3.x)

Le système a un **potentiel élevé** et avec les améliorations proposées, il pourrait devenir un modèle de configuration externalisée pour les applications Flask.

---

## Annexes

### A.1 Exemple de Configuration TOML Complète

```toml
[oncall]
rotation_order = [1, 2, 3, 4]  # IDs des utilisateurs dans l'ordre de rotation
min_days_between_oncalls = 14  # Contrainte légale : minimum 2 semaines entre deux astreintes
start_day = 4  # 4 = vendredi (0=lundi, 6=dimanche)
start_hour = 21  # Heure de début de l'astreinte
end_day = 4  # Jour de fin
end_hour = 7  # Heure de fin

[shifts]
shift_types = [
    { name = "morning", start = 7, end = 15, label = "07h-15h" },
    { name = "day", start = 9, end = 17, label = "09h-17h" },
    { name = "evening", start = 13, end = 21, label = "13h-21h" }
]

rules = [
    { rule = "oncall_has_evening_shift", enabled = true, priority = 1, 
      description = "Personne en astreinte = shift 13h-21h (si dans groupe schedule)" },
    { rule = "rotation_after_oncall", enabled = true, priority = 2, 
      description = "Rotation : après astreinte = shift 07h-15h la semaine suivante" },
    { rule = "default_shift", enabled = true, priority = 3, 
      description = "Shift par défaut : 09h-17h" },
    { rule = "two_users_special_case", enabled = true, priority = 4, 
      description = "2 utilisateurs : non-astreinte = 07h-15h, astreinte = 13h-21h" }
]

work_days = [0, 1, 2, 3, 4]  # Lundi au vendredi

daily_requirements = {
    monday = { morning = 1, day = 1, evening = 1 },
    tuesday = { morning = 1, day = 1, evening = 1 },
    wednesday = { morning = 1, day = 1, evening = 1 },
    thursday = { morning = 1, day = 1, evening = 1 },
    friday = { morning = 1, day = 1, evening = 1 }
}

[groups]
schedule_groups = ["Technique", "Support"]  # Groupes éligibles pour les shifts
oncall_groups = ["Astreinte", "Technique"]  # Groupes éligibles pour les astreintes

[generation]
default_period_days = 180  # Période par défaut : 6 mois
advance_generation_enabled = true  # Génération automatique à l'avance
rebalance_on_leave_change = true  # Rééquilibrer automatiquement
```

### A.2 Diagramme d'Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        INTERFACE ADMIN                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Formulaires │  │   API REST   │  │      Tableau de bord      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     app/routes/admin.py                            │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  - automation_dashboard()                                     │  │
│  │  - automation_config()  (GET/POST)                            │  │
│  │  - automation_full()    (Génération complète)                 │  │
│  │  - automation_shifts() (Génération shifts)                    │  │
│  │  - refresh_shifts()     (Rafraîchissement)                    │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ automation.py    │ │ advanced_...py   │ │ automation_...py │
│                 │ │                 │ │                 │
│ - OnCallAutomation │ │ - AdvancedShift │ │ - AutomationConfig│
│ - ShiftAutomation  │ │   Automation    │ │ - ConfigValidator │
│ - BusinessRules    │ │                 │ │ - DatabaseConfig │
│ - generate_full...│ │ - rebalance...  │ │   Migrator       │
└─────────────────┘ └─────────────────┘ └─────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Base de données │ │ automation_rules │ │      Logs       │
│                 │ │    .toml         │ │                 │
│ - User          │ │ - [oncall]       │ │ - app.logger    │
│ - Group         │ │ - [shifts]       │ │ - Flask logs    │
│ - Shift         │ │ - [groups]       │ │                 │
│ - OnCall        │ │ - [generation]   │ │                 │
│ - Leave         │ │                 │ │                 │
│ - ShiftType     │ │                 │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### A.3 Liste des Fichiers Modifiés dans la Branche

```
app/config/__init__.py                    # NOUVEAU
app/config/automation_rules.py           # NOUVEAU (286 lignes)
app/config/automation_rules.toml         # NOUVEAU (62 lignes)
app/config/migration.py                  # NOUVEAU (323 lignes)
app/routes/admin.py                      # MODIFIÉ (+91 lignes)
app/utils/advanced_shift_automation.py   # EXISTANT
app/utils/automation.py                  # EXISTANT
requirements.txt                         # MODIFIÉ (ajout toml==0.10.2)
```

---

*Fin du rapport*
