# FAQ

> Contenu vérifié contre le code réel en Phase 5 (2026-07). Anciennement
> une section de `USER_GUIDE.md`, extraite ici pour éviter la
> duplication et corrigée sur plusieurs points inexacts (voir notes
> inline).

## Questions fréquentes

### Comment réinitialiser mon mot de passe ?

Contactez votre administrateur — il n'y a pas de fonctionnalité de
réinitialisation en libre-service (pas de "mot de passe oublié"). Un
administrateur peut définir un nouveau mot de passe via
**Admin > Utilisateurs > Modifier**.

### Je ne vois pas mes shifts dans le calendrier

Vérifiez que :
1. Vous êtes connecté avec le bon compte.
2. Vos shifts sont bien attribués à votre utilisateur.
3. La période sélectionnée couvre vos shifts — le calendrier de la page
   d'accueil affiche une fenêtre de ±180 jours autour d'aujourd'hui ; la
   page **Planning** liste tout, avec pagination.

### Je ne peux pas ajouter un shift pour un utilisateur

Vérifiez que :
1. L'utilisateur appartient à un groupe qui participe au planning
   (`is_part_of_schedule`).
2. Vous êtes administrateur — seuls les admins peuvent ajouter des
   shifts (`/schedule/add`).
3. Le type de shift existe bien.
4. La période ne tombe pas uniquement sur un week-end — les shifts ne
   sont créés que pour les jours ouvrés (lundi-vendredi).

### Je ne peux pas ajouter un congé

Vérifiez que :
1. Vous êtes administrateur, ou vous ajoutez le congé pour vous-même
   (un non-admin ne peut créer un congé que pour son propre compte).
2. Les dates sont valides (début ≤ fin).
3. Le congé ne chevauche pas un **autre congé existant** du même
   utilisateur.

> **Correction** : contrairement à ce que documentaient les versions
> précédentes de ce guide, un congé qui chevauche un shift ou une
> astreinte existants **n'est pas bloqué** — l'application rééquilibre
> automatiquement les shifts concernés à la place. Les dates dans le
> passé sont également acceptées (aucune vérification de date future).

### L'export ICS ne fonctionne pas

Vérifiez que :
1. Votre token ICS est valide (régénérez-le depuis **Profil > Token ICS**
   si besoin).
2. L'URL est correcte (`scope=my` pour votre planning personnel,
   `scope=all` pour tout le monde — nécessite d'être admin ou d'avoir
   un token admin pour être utile).
3. Votre application de calendrier supporte les abonnements ICS par URL.

### Comment modifier un shift/une astreinte/un congé existant ?

Il n'y a pas de formulaire de modification dédié. Deux options :
1. **Glisser-déposer sur le calendrier** (page d'accueil), en mode
   édition — **réservé aux administrateurs**, y compris pour les congés
   d'un utilisateur normal.
2. Supprimer l'entrée et en recréer une nouvelle via le formulaire
   d'ajout correspondant.

### Comment désactiver l'authentification pour le développement ?

Dans le fichier `.env` (pas `config.py`) :

```bash
LOGIN_DISABLED=true
```

> ⚠️ **Ne jamais utiliser cette option en production !**

### Quel est le mot de passe administrateur par défaut ?

`admin@leviia.local` / `admin123` — **mais seulement si vous avez copié
`.env.example` vers `.env`** avant le premier démarrage (`cp .env.example .env`).
Sans ce fichier, `DEFAULT_ADMIN_PASSWORD` n'est pas défini et
l'application génère un mot de passe aléatoire au démarrage, jamais
affiché nulle part. Voir
[`guides/QUICK_START.md`](QUICK_START.md).

## Problèmes techniques

### Erreur 404 (Page non trouvée)

- Vérifiez que l'URL est correcte.
- Vérifiez que vous êtes connecté.
- Vérifiez que vous avez les permissions nécessaires (certaines pages
  sont réservées aux administrateurs).

### Erreur 500 (Erreur serveur)

- Vérifiez les logs de l'application (`logs/` en local, voir
  [`reference/ERROR_HANDLING.md`](../reference/ERROR_HANDLING.md)).
- Contactez l'administrateur.
- Signalez le bug sur GitHub avec les étapes de reproduction.

### La base de données ne se crée pas

- Vérifiez que le dossier `instance/` existe et est accessible en
  écriture : `mkdir -p instance`.
- Vérifiez que vous avez bien copié `.env.example` en `.env`.

### Les modifications ne sont pas enregistrées

- Vérifiez que vous avez cliqué sur **"Enregistrer"**.
- Vérifiez que vous avez les permissions nécessaires.
- Vérifiez qu'il n'y a pas d'erreur de validation affichée (champ
  obligatoire manquant, format invalide).

### Une requête POST échoue avec "Bad Request" / erreur 400 inattendue

Depuis la Phase 4, toute requête d'écriture (formulaire ou appel API)
nécessite un jeton CSRF valide. Si vous scriptez des appels vers
l'application (curl, requêtes automatisées) plutôt que d'utiliser
l'interface, vous devez d'abord récupérer un jeton CSRF (champ caché
`csrf_token` du formulaire, ou balise `<meta name="csrf-token">`) et
l'inclure dans votre requête. Voir
[`api/API.md`](../api/API.md#authentification).

## Messages d'erreur courants

| Message | Cause | Solution |
|---|---|---|
| "Tous les champs sont obligatoires" | Un champ requis est vide | Remplissez tous les champs marqués comme obligatoires |
| "Format de date invalide" | La date n'est pas au format AAAA-MM-JJ | Utilisez le format `2026-06-15` |
| "L'astreinte doit commencer un vendredi" | La date de début n'est pas un vendredi | Sélectionnez un vendredi |
| "Impossible de supprimer... des données sont associées" | L'élément a des dépendances (ex : utilisateur avec des shifts) | Supprimez d'abord les données associées |
| "Email ou mot de passe incorrect" | Identifiants invalides | Vérifiez votre email et mot de passe |
| "Vous ne pouvez ajouter des congés que pour vous-même" | Tentative d'ajout de congé pour un autre utilisateur (non-admin) | Connectez-vous en tant qu'admin, ou ajoutez le congé pour vous-même |

## Voir aussi

- [Guide de démarrage rapide](QUICK_START.md)
- [Guide utilisateur](USER_GUIDE.md)
- [Guide administrateur](ADMIN_GUIDE.md)
