# Module de Configuration TOML - Leviia Schedule

## 📁 Structure du Module

```
app/config/
├── __init__.py                    # Module vide pour namespace
├── automation_rules.toml          # Fichier de configuration principal (TOML)
├── automation_rules.py            # Classe AutomationConfig - Gestion de la configuration
├── migration.py                    # Migration et validation des données
└── README.md                       # Ce fichier
```

## 🎯 Rôle de chaque composant

### 1. `automation_rules.toml`
**Rôle** : Fichier de configuration principal au format TOML  
**Contenu** : Toutes les règles métiers pour l'automatisation des astreintes et shifts  
**Modifiable** : Oui, via l'interface admin ou directement via un éditeur  

**Sections** :
- `[oncall]` - Configuration des astreintes
- `[shifts]` - Configuration des shifts
- `[groups]` - Configuration des groupes
- `[generation]` - Paramètres de génération

### 2. `automation_rules.py` - Classe `AutomationConfig`
**Rôle** : Charger, gérer et synchroniser la configuration TOML  
**Fonctionnalités** :
- Chargement de la configuration depuis le fichier TOML
- Fusion avec les valeurs par défaut
- Cache avec vérification de date de modification
- Verrouillage thread-safe pour la concurrence
- Synchronisation bidirectionnelle avec la base de données
- Méthodes utilitaires pour accéder aux paramètres

**Utilisation** :
```python
from app.config.automation_rules import AutomationConfig

# Charger la configuration
config = AutomationConfig.load()

# Accéder à une section
oncall_config = AutomationConfig.get_oncall_rules()
shift_config = AutomationConfig.get_shift_rules()

# Synchroniser avec la base de données
AutomationConfig.sync_groups_to_toml()
AutomationConfig.sync_shift_types_to_toml()

# Sauvegarder la configuration
AutomationConfig.save(new_config)
```

### 3. `migration.py` - Classes `DatabaseConfigMigrator` et `ConfigValidator`
**Rôle** : Migration des données existantes et validation de la configuration  

#### `DatabaseConfigMigrator`
- Extraction de la configuration depuis la base de données
- Migration vers le format TOML
- Synchronisation bidirectionnelle

#### `ConfigValidator`
- Validation de chaque section de configuration
- Validation complète avant sauvegarde
- Messages d'erreur clairs et localisés

**Utilisation** :
```python
from app.config.migration import DatabaseConfigMigrator, ConfigValidator

# Migrer la base vers TOML
result = DatabaseConfigMigrator.sync_toml_from_database()

# Valider une configuration
is_valid, errors = ConfigValidator.validate_all(config)
```

## 🔄 Flux de Données

```
┌─────────────────────────────────────────────────────────────┐
│                    INTERFACE ADMIN / API                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  AutomationConfig (automation_rules.py)        │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  - load() : Charge depuis TOML (avec cache et verrou)     │  │
│  │  - save() : Sauvegarde dans TOML                         │  │
│  │  - reload() : Recharge depuis le fichier                   │  │
│  │  - get_*_rules() : Accès aux sections                     │  │
│  │  - sync_*_to_toml() : DB → TOML                           │  │
│  │  - sync_*_from_toml() : TOML → DB                         │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│  automation_rules    │ │    migration.py      │ │   Base de données    │
│      .toml           │ │                     │ │                     │
│  (Fichier TOML)      │ │ - DatabaseConfigMigrator │ │ - User, Group      │
│                     │ │ - ConfigValidator    │ │ - ShiftType        │
│                     │ │                     │ │ - Shift, OnCall    │
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
```

## 📊 Architecture des Règles Métiers

### Hiérarchie des classes d'automatisation

```
┌─────────────────────────────────────────────────────────────┐
│                    app/utils/automation.py                      │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  BusinessRules                                          │  │
│  │    - Règles métiers par défaut (hardcodées)               │  │
│  │    - Peut être remplacé par la configuration TOML         │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  OnCallAutomation                                       │  │
│  │    - Génération des astreintes avec rotation             │  │
│  │    - Vérification des contraintes légales                 │  │
│  │    - Recherche des utilisateurs disponibles              │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  ShiftAutomation                                        │  │
│  │    - Génération des shifts selon les règles               │  │
│  │    - Vérification des disponibilités                    │  │
│  │    - Recherche de remplaçants                           │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              app/utils/advanced_shift_automation.py             │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  AdvancedShiftAutomation                                 │  │
│  │    - Implémente les 4 règles métiers configurables :      │  │
│  │      1. oncall_has_evening_shift                         │  │
│  │      2. rotation_after_oncall                            │  │
│  │      3. default_shift                                    │  │
│  │      4. two_users_special_case                           │  │
│  │    - Utilise la configuration depuis automation_rules.py  │  │
│  │    - Génération jour par jour avec application des règles  │  │
│  │    - Rééquilibrage automatique après modification de congé│  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Règles Métiers Configurables

Les 4 règles principales sont définies dans `automation_rules.toml` :

1. **`oncall_has_evening_shift`** (Priorité 1)
   - La personne en astreinte a le shift 13h-21h (si dans groupe schedule)

2. **`rotation_after_oncall`** (Priorité 2)
   - Après une astreinte, l'utilisateur a le shift 07h-15h la semaine suivante

3. **`default_shift`** (Priorité 3)
   - Shift par défaut 09h-17h pour tous les autres cas

4. **`two_users_special_case`** (Priorité 4)
   - Avec 2 utilisateurs disponibles, la personne NON d'astreinte a le shift 07h-15h

## 🔧 Configuration par Défaut

Voir le fichier `automation_rules.toml` pour la configuration complète.

## 📝 Bonnes Pratiques

1. **Toujours valider avant de sauvegarder** :
   ```python
   is_valid, errors = ConfigValidator.validate_all(config)
   if not is_valid:
       # Gérer les erreurs
       return errors
   AutomationConfig.save(config)
   ```

2. **Utiliser le cache intelligemment** :
   ```python
   # Le cache est automatiquement invalidé quand le fichier change
   config = AutomationConfig.load()
   
   # Forcer le rechargement si nécessaire
   config = AutomationConfig.load(force_reload=True)
   ```

3. **Gérer les erreurs de synchronisation** :
   ```python
   if not AutomationConfig.sync_groups_to_toml():
       # La synchronisation a échoué, voir les logs
       logger.error("Synchronisation échouée")
   ```

4. **Utiliser les décorateurs de permissions** :
   ```python
   from app.utils.decorators import config_editor_required
   
   @app.route('/admin/automation/config')
   @admin_required
   @config_editor_required
   def automation_config():
       # Seuls les admins peuvent accéder à cette route
       ...
   ```

## 🚨 Résolution des Problèmes

### Problème : Le fichier TOML est corrompu
**Solution** : 
1. Vérifier les logs pour voir l'erreur de parsing
2. Corriger le fichier TOML ou le supprimer (il sera recréé avec les valeurs par défaut)
3. Redémarrer l'application

### Problème : La configuration n'est pas mise à jour
**Solution** :
1. Vérifier que le fichier a bien été modifié
2. Vérifier les permissions sur le fichier
3. Forcer le rechargement : `AutomationConfig.reload()`

### Problème : Erreurs de synchronisation
**Solution** :
1. Vérifier les logs pour voir l'erreur exacte
2. Vérifier que la base de données est accessible
3. Vérifier que les entités référencées existent (groupes, utilisateurs)

## 📚 Documentation Complémentaire

- [Rapport d'Analyse Completa](../RAPPORT_ANALYSE_CONFIGURATION_TOML.md)
- [Tests Unitaires](../../tests/test_config_improvements.py)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [TOML Documentation](https://toml.io/)
