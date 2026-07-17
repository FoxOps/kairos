# 🚀 Guide de Démarrage Rapide - Leviia Schedule

> **Version** : 1.0.0 | **Dernière mise à jour** : Juin 2026

---

## 🎯 En 5 Minutes

### 1️⃣ Installation (méthode recommandée : Docker Compose)

Pas besoin de cloner le dépôt - deux fichiers suffisent :

```bash
mkdir leviia-schedule && cd leviia-schedule
curl -o docker-compose.yml https://raw.githubusercontent.com/FoxOps/leviia-schedule/main/docker/docker-compose.example.yml
curl -o .env https://raw.githubusercontent.com/FoxOps/leviia-schedule/main/docker/.env.example

nano .env  # LEVIIA_IMAGE=harbor.leviia.com/<HARBOR_PROJECT>/leviia-schedule:latest, SECRET_KEY, DEFAULT_ADMIN_PASSWORD

docker compose up -d
```

**Accès** : http://localhost:5000

> ⚠️ **L'étape `nano .env`** (au moins `SECRET_KEY`/`DEFAULT_ADMIN_PASSWORD`)
> est indispensable : sans `DEFAULT_ADMIN_PASSWORD`, l'application génère
> un mot de passe admin aléatoire au premier démarrage (jamais affiché
> nulle part) au lieu du `admin123` par défaut ci-dessous.

> **📖 Détail complet** (registry, volumes, variables) :
> [`deployment/docker.md`](../deployment/docker.md)

### Alternative : installation locale (développement / cas particuliers)

Réservé au développement sur le code ou aux cas où Docker n'est pas
disponible - l'image Docker ci-dessus reste la méthode principale.

```bash
git clone https://github.com/FoxOps/leviia-schedule.git
cd leviia-schedule
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Copier la configuration par défaut
cp .env.example .env

# Démarrer
python run.py
```

**Accès** : http://localhost:5000

> ⚠️ **L'étape `cp .env.example .env` est indispensable** : sans elle,
> `DEFAULT_ADMIN_PASSWORD` n'est pas défini et l'application génère un
> mot de passe admin aléatoire au premier démarrage (jamais affiché nulle
> part) au lieu du `admin123` par défaut ci-dessous.

---

### 2️⃣ Première Connexion

- **Email** : `admin@leviia.local`
- **Mot de passe** : `admin123`

> ⚠️ **Changez immédiatement le mot de passe !**

---

### 2️⃣ Authentification SSO/OIDC (Optionnelle)

Si vous utilisez **Keycloak**, **Okta**, **Auth0** ou un autre fournisseur OIDC :

1. Configurez votre fournisseur OIDC avec l'URL de callback : `http://localhost:5000/oidc/callback`
2. Ajoutez les variables d'environnement dans votre fichier `.env` :
   ```bash
   OIDC_ENABLED=true
   OIDC_ISSUER=https://votre-fournisseur.com/realms/votre-realm
   OIDC_CLIENT_ID=votre-client-id
   OIDC_CLIENT_SECRET=votre-client-secret
   OIDC_REDIRECT_URI=http://localhost:5000/oidc/callback
   ```
3. Redémarrez l'application : `python run.py`
4. Connectez-vous via le bouton **Se connecter avec SSO**

> ⚠️ **Info** : Consultez le [Guide Administrateur](ADMIN_GUIDE.md) pour une configuration complète SSO/OIDC.

---

### 3️⃣ Configuration de Base

#### Créer un groupe
1. **Admin** > **Groupes** > **Ajouter**
2. Nom : `Équipe Technique`
3. ✅ Participe au planning
4. ✅ Participe aux astreintes

#### Ajouter un utilisateur
1. **Admin** > **Utilisateurs** > **Ajouter**
2. Nom : `Jean Dupont`
3. Email : `jean@entreprise.com`
4. Groupe : `Équipe Technique`
5. Mot de passe : `monmotdepasse123`

---

## 📅 Utilisation Quotidienne

### Pour les Administrateurs

#### 🔹 Ajouter un shift
1. **Planning** > **Ajouter un shift**
2. Sélectionnez : Utilisateur + Type de shift + Date
3. **Enregistrer**

#### 🔹 Planifier une astreinte
1. **Astreintes** > **Ajouter une astreinte**
2. Sélectionnez : Utilisateur + **Vendredi** comme date de début
3. **Enregistrer**

#### 🔹 Configurer l'automatisation
1. **Admin** > **Automatisation** > **Génération complète**
2. Configurez l'ordre de rotation
3. Sélectionnez la période
4. **Simuler** → **Générer**

---

### Pour les Utilisateurs

#### 🔹 Consulter son planning
- **Accueil** : Calendrier interactif
- **Planning** : Liste de tous vos shifts

#### 🔹 Prendre un congé
1. **Congés** > **Ajouter un congé**
2. Sélectionnez : Date de début + Date de fin
3. **Enregistrer**

#### 🔹 Exporter vers Google Calendar
1. **Profil** > **Token ICS**
2. **Générer un nouveau token**
3. Copiez l'URL : `http://localhost:5000/export/shifts?scope=my&token=VOTRE_TOKEN`
4. Dans Google Calendar : **Paramètres** > **Ajouter un calendrier** > **À partir d'une URL**

---

## ⚡ Astuces Rapides

### Raccourcis

| Action | Chemin |
|--------|--------|
| Tableau de bord | `/` ou `/index` |
| Planning | `/schedule` |
| Astreintes | `/oncall` |
| Congés | `/leave` |
| Admin | `/admin` |
| Profil | `/profile` |

### Commandes Utiles

```bash
# Lancer les tests
make test

# Vérifier la qualité du code
make lint

# Formater le code
make format-fix

# Tout en une fois
make all
```

---

## 🆘 Dépannage Express

| Problème | Solution |
|----------|----------|
| **Erreur 404** | Vérifiez l'URL et vos permissions |
| **Connexion échouée** | Vérifiez email/mot de passe |
| **Shifts non visibles** | Vérifiez la période dans le calendrier |
| **Export ICS ne fonctionne pas** | Régénérez votre token |
| **Base de données manquante** | `mkdir -p instance` puis relancez |

---

## 📚 Documentation Complète

- [📖 Guide Utilisateur Complet](USER_GUIDE.md)
- [🛡️ Guide Administrateur](ADMIN_GUIDE.md)
- [❓ FAQ](FAQ.md)
- [🗺️ Feuille de Route](../../ROADMAP.md)
- [📋 README Technique](../../README.md)

---

## 📞 Support

- **Issues** : [GitHub Issues](https://github.com/FoxOps/leviia-schedule/issues)
- **Discussions** : [GitHub Discussions](https://github.com/FoxOps/leviia-schedule/discussions)
- **Licence** : CeCILL v2.1

---

*© 2026 Leviia Schedule - Tous droits réservés*
