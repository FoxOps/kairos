# Analyse : la fenêtre ±30 jours du rééquilibrage d'astreintes

> Rapport d'investigation suite à un retour terrain : "l'automatisation à
> -30/+30 jours laisse quelques trous dans le planning, il faut trouver
> le meilleur écart qui n'en laisse pas, sans que ce soit trop gros -
> laisser des trous doit être un cas très rare, pas récurrent."
>
> **Conclusion en une phrase : la taille de la fenêtre n'est pas le
> facteur limitant. Le facteur limitant est le nombre d'utilisateurs
> réellement disponibles pendant la période concernée, et c'est une
> contrainte mathématique démontrable, pas un paramètre réglable.**

Ce document reproduit intégralement le raisonnement, les simulations
(5 scripts, tous exécutant le vrai code de production, pas une
réimplémentation) et la preuve mathématique qui sous-tend cette
conclusion.

---

## 1. Où vit la fenêtre ±30 jours

`AdvancedShiftAutomation.rebalance_after_leave()`
(`app/utils/automation/advanced_shift_automation.py`), déclenché
automatiquement à chaque ajout/modification de congé :

```python
first_friday = leave.start_date
while first_friday.weekday() != 4:
    first_friday -= timedelta(days=1)
last_friday = leave.end_date
while last_friday.weekday() != 4:
    last_friday += timedelta(days=1)

shift_period_start = first_friday - timedelta(days=30)
shift_period_end = last_friday + timedelta(days=30)
```

Puis :

```python
OnCallRepository.delete_overlapping_range(shift_period_start, shift_period_end)
OnCallAutomation.generate_oncall_schedule(shift_period_start, shift_period_end, ...)
```

**Tout** le contenu de cette fenêtre est supprimé puis régénéré depuis
zéro par la recherche par backtracking (`_solve_max_filled_weeks`,
même fichier) - pas seulement les semaines réellement affectées par le
congé.

---

## 2. Preuve mathématique : la contrainte des 2 semaines

### 2.1 Formulation exacte du contrôle

`AvailabilityIndex.meets_spacing_constraint()`
(`app/utils/automation/oncall_automation.py`) :

```python
gap_days = (start_time - existing_end).days
if gap_days / 7 < 2:
    return False
```

Une astreinte dure exactement 7 jours : vendredi 21h00 → vendredi
suivant 07h00.

### 2.2 Calcul de l'écart minimal réel entre deux astreintes du même utilisateur

Soit une astreinte assignée à la semaine `i` (vendredi `F_i`) et une
autre à la semaine `j` (vendredi `F_j = F_i + 7·(j-i)` jours), au même
utilisateur, avec `j > i` :

- fin de l'astreinte `i` : `F_i + 7 jours, 07h00`
- début de l'astreinte `j` : `F_i + 7·(j-i) jours, 21h00`
- écart : `7·(j-i-1) jours + 14 heures`

Vérification numérique directe (script exécuté, pas une estimation) :

| `j - i` | fin de l'astreinte `i` | début de l'astreinte `j` | écart calculé | `écart.jours / 7` | passe le test `>= 2` ? |
|---|---|---|---|---|---|
| 1 | 2026-01-09 07:00 | 2026-01-09 21:00 | 14h00 | 0.0 | ❌ |
| 2 | 2026-01-09 07:00 | 2026-01-16 21:00 | 7j 14h00 | 1.0 | ❌ |
| **3** | 2026-01-09 07:00 | 2026-01-23 21:00 | 14j 14h00 | **2.0** | ✅ |

**Résultat démontré : le même utilisateur ne peut être réassigné que 3
semaines calendaires ou plus après sa précédente astreinte (`j - i ≥
3`), jamais 2.** Ce n'est pas un arrondi ou une approximation - le
calcul en `timedelta` tombe exactement sur `2.0` à `j-i=3`, la portion
`14h00` ne contribuant jamais à un jour entier supplémentaire (`.days`
tronque, il ne s'agit jamais de `< 24h` en trop).

### 2.3 Théorème de capacité minimale

**Affirmation** : couvrir *toutes* les semaines sans exception exige un
minimum de **3 utilisateurs éligibles distincts**.

**Preuve** (argument des tiroirs / pigeonhole) : soit 3 semaines
calendaires consécutives quelconques `{i, i+1, i+2}`. D'après 2.2, un
même utilisateur ne peut occuper deux de ces trois semaines (il
faudrait `j - i ≥ 3`, impossible dans une fenêtre de 3 semaines
consécutives). Donc les 3 utilisateurs qui couvrent ces 3 semaines sont
nécessairement **deux à deux distincts**. Comme ce raisonnement
s'applique à *toute* fenêtre de 3 semaines consécutives du planning,
couvrir 100% des semaines exige au moins 3 utilisateurs distincts au
total. **CQFD.**

**Cette condition est également suffisante** : une simple rotation
round-robin de période exactement 3 (A, B, C, A, B, C, ...) donne à
chaque utilisateur un écart de exactement 3 semaines entre deux
astreintes - satisfait la contrainte avec une égalité stricte, **sans
aucune marge de manœuvre (slack = 0)**.

### 2.4 Conséquence directe : le cas N=2 est mathématiquement impossible à combler à 100%

Avec seulement 2 utilisateurs, le théorème 2.3 est violé par
construction (2 < 3) : il est **information-théoriquement impossible**
de couvrir 100% des semaines, quel que soit l'algorithme, quelle que
soit la taille de la fenêtre. Le taux de remplissage maximal
atteignable est de **2 semaines remplies sur 3** (`2/3 ≈ 66.7%`) - par
exemple le cycle A, B, *(vide)*, A, B, *(vide)*, ...

### 2.5 Notion de "slack" (marge)

On définit `slack(N) = N - 3` : le nombre d'utilisateurs au-delà du
minimum théorique strict.

| N (utilisateurs éligibles) | slack | Marge de manœuvre |
|---|---|---|
| 2 | -1 | Impossible par construction (2.4) |
| 3 | 0 | Rotation à zéro redondance - **toute** perturbation (congé) crée un trou, car aucun autre utilisateur ne peut absorber la semaine sans lui-même violer son propre espacement |
| 4 | 1 | Marge fine - absorbe un congé isolé, mais s'épuise progressivement sous charge répétée (voir §3.4) |
| 5 | 2 | Marge confortable - trous rares même sous charge soutenue |
| 6 | 3 | Marge large - zéro trou observé dans tous les tests, même les plus chargés |

---

## 3. Simulations (code réel exécuté, pas une réimplémentation)

Méthodologie commune : `OnCallAutomation.generate_oncall_schedule()` et
`AdvancedShiftAutomation.rebalance_after_leave()` (le vrai code de
`app/utils/automation/`) tournent contre une base SQLite en mémoire,
avec un planning propre pré-généré sur une large plage (±150 à ±180
jours au-delà de la période testée) pour que les conditions aux limites
soient réalistes, pas un artefact de "rien avant/après".

### 3.1 Simulation 1 - un seul congé isolé

Variables : 2 à 8 utilisateurs, congé de 1 à 4 semaines, fenêtre de
30 à 120 jours.

| Utilisateurs | Résultat |
|---|---|
| 2 | Trous **systématiques**, et qui **augmentent** avec la fenêtre (30j → 3 trous, 120j → 5-6 trous) |
| 3 | Exactement 1 trou dès que le congé dépasse 1 semaine, **constant** de 30 à 120 jours |
| 4, 5, 6, 8 | **0 trou**, sur toutes les tailles de fenêtre testées (30 à 120 jours) |

### 3.2 Simulation 2 - deux congés proches mais non superposés, traités séquentiellement

Reproduit l'usage réel : chaque congé ajouté déclenche son propre
rééquilibrage indépendant, qui ne voit que sa propre fenêtre.

- N=3 : 1 à 3 trous selon l'écart entre les deux congés, **indépendant
  de la fenêtre** (30/45/60/90j donnent des résultats quasi identiques)
- N≥4 : **0 trou**, dans toutes les combinaisons testées

### 3.3 Simulation 3 - congés simultanés (plusieurs personnes en même temps)

Le nombre de trous dépend uniquement de l'effectif *réellement
disponible pendant le congé* (N moins le nombre de congés simultanés),
jamais de la fenêtre :

| Effectif dispo pendant le congé | Trous |
|---|---|
| ≥ 4 | 0 |
| = 3 | 1 |
| ≤ 2 | Trous fréquents |

### 3.4 Simulation 4 - accumulation dans le temps (le scénario réel)

Série de 5 à 30 congés aléatoires (utilisateur, date, durée 1-3
semaines) répartis sur 2 ans, traités un par un comme en production
réelle - **c'est ce test qui reproduit le retour terrain**.

| N | 5 congés | 10 congés | 20 congés | 30 congés |
|---|---|---|---|---|
| 4 | 0-1 | 0-2 | 0-3 | **5 à 13** |
| 5 | 0 | 0 | 0 | 0-2 |
| 6 | 0 | 0 | 0 | **0** |

**Constat clé : les trous n'apparaissent qu'à charge soutenue (beaucoup
de congés cumulés), pas sur un événement isolé - exactement le
"quelques trous au fil du temps" rapporté.** Et la fenêtre 60 jours ne
fait pas mieux que 30 jours dans ce test - parfois pire (ex : N=4/30
congés/seed=2 → 10 trous à 30j contre 13 trous à 60j).

### 3.5 Simulation 5 - pourquoi élargir la fenêtre n'aide pas (et pourquoi la rétrécir est pire)

Deux approches comparées sur la même charge (10-30 congés/2 ans) :

- **Fenêtre actuelle** (supprime et régénère tout le ±30j) : 0 à 20
  trous cumulés selon N et la charge (voir §3.4)
- **Réparation "chirurgicale"** (ne touche que l'exacte semaine du
  congé, sans marge autour) : **bien pire** - 7 à 20 trous cumulés dès
  10 congés, y compris à N=5

**Explication** : sans marge, le solveur n'a aucune liberté de
réarranger les semaines voisines si le remplacement direct viole
l'espacement légal - il échoue immédiatement. La fenêtre ±30j sert
justement à donner cette marge de manœuvre à la recherche par
backtracking ; elle n'est pas superflue.

**Donc élargir la fenêtre (30→120j) n'aide pas** (§3.1-3.4, aucun gain
mesurable, parfois une légère dégradation - probablement parce que plus
de semaines réécrites à chaque congé = plus de risque de perturber une
zone du planning qui fonctionnait déjà), **et la rétrécir aide encore
moins** (§3.5, dégradation nette). Le problème n'est ni "fenêtre trop
petite" ni "fenêtre trop grande" - c'est l'absence de mémoire entre les
rééquilibrages successifs : chaque congé réécrit sa fenêtre depuis zéro
sans savoir que telle semaine, déjà bonne, n'avait pas besoin de
changer.

### 3.6 Simulation 6 - validation empirique de la piste "perturbation minimale"

Hypothèse formulée en conclusion de la première version de ce rapport :
faire préférer au solveur, pour chaque semaine de la fenêtre,
l'utilisateur *déjà assigné* (capturé juste avant la suppression),
plutôt que de rejouer l'ordre de rotation en aveugle - sans changer ni
la recherche par backtracking, ni la contrainte d'espacement, ni le
budget `_MAX_SEARCH_NODES`. Seul l'**ordre de préférence par semaine**
change.

**Méthodologie** : même scénario que la simulation 4 (série de congés
aléatoires sur 2 ans, traités un par un), rejoué avec **20 graines
aléatoires indépendantes** par configuration (contre 3 dans les
simulations précédentes, pour un signal statistique plus fiable face au
bruit déjà observé sur un petit échantillon).

**N=4, 30 congés cumulés, 20 essais indépendants** :

| Configuration | Total trous cumulés (20 essais) | Moyenne |
|---|---|---|
| Fenêtre actuelle, ordre rotation, 30j | 98 | 4.9 |
| Fenêtre actuelle, ordre rotation, 60j | 119 | 6.0 |
| **Perturbation minimale, 30j** | **90** | **4.5** |
| Perturbation minimale, 60j | 100 | 5.0 |

Comparaison essai-par-essai (30j) : la perturbation minimale fait
**mieux** dans 11 essais sur 20, **pire** dans 6, égalité dans 3 -
amélioration nette et reproductible (**-8%** au total), pas un artefact
d'une seule graine favorable. À 60j l'écart est encore plus net (13
mieux / 3 pire / 4 égal, **-16%** au total) - la perturbation minimale
profite d'autant plus d'une fenêtre large qu'elle ne gâche plus cette
marge en réécrivant des semaines qui n'avaient pas besoin de changer.

**N=5, 30 congés cumulés, 20 essais indépendants** : **résultat
strictement identique** dans les 20 essais, 0 mieux / 0 pire / 20
égalités, quelle que soit la fenêtre (30 ou 60j). Confirme le
raisonnement en slack (§2.5) : à partir de slack=2, il y a déjà assez
de marge pour que l'ordre de préférence par semaine n'ait plus
d'incidence - le gain de la perturbation minimale est concentré
exactement là où il compte, le régime à marge fine (N=4, slack=1).

**Meilleure combinaison trouvée sur l'ensemble des tests** : perturbation
minimale + fenêtre **30 jours actuelle, inchangée** (90 trous, la plus
basse de toutes les combinaisons testées) - élargir la fenêtre reste
contre-productif même en combinaison avec cette amélioration.

**Conclusion de cette validation : l'hypothèse est confirmée, avec un
gain modeste mais réel et reproductible (-8 à -16% de trous cumulés à
N=4, le régime concerné), sans aucune régression observée à N=5+.**
Une implémentation réelle nécessiterait de faire remonter l'assignation
existante avant suppression dans `rebalance_after_leave()` (actuellement
la fenêtre entière est supprimée avant tout calcul, l'information est
donc perdue) et de l'injecter dans l'ordre de préférence de
`_generate_for_fridays()` - un changement ciblé, pas une réécriture de
l'algorithme.

### 3.7 Implémentation réelle : un piège trouvé en cours de route

Implémenté dans `OnCallAutomation.capture_existing_assignments()`
(nouvelle méthode) + un paramètre `preferred_assignments` sur
`_generate_for_fridays()`/`generate_oncall_schedule()`, câblé dans les
deux points d'appel concernés (rééquilibrage automatique après congé,
et "Rafraîchir > Régénérer entièrement" - jamais "Générer", qui reste
un reset explicite volontaire).

Un premier jet excluait l'utilisateur en congé de la capture
(`exclude_user_id=leave.user_id`), en supposant que le préférer pour sa
propre semaine désormais en conflit n'avait aucun sens. Un test
d'intégration a immédiatement révélé le problème : sur une fenêtre de 2
mois avec 4 utilisateurs, cette exclusion supprime **aussi** les
*autres* semaines - parfaitement valides - que cet utilisateur occupait
ailleurs dans la même fenêtre, forçant leur réassignation inutile alors
même qu'il n'y avait aucun conflit sur ces semaines-là. Vérifié
directement : sur une fenêtre à 4 utilisateurs/rotation de 4 semaines,
l'utilisateur revient 3 fois dans une fenêtre de 2 mois - l'exclusion
supprimait bien les 2 occurrences non concernées par le congé, pas
seulement la première.

Le filtrage `has_leave_conflict()` déjà présent dans
`_generate_for_fridays()` suffit à écarter précisément la seule semaine
réellement en conflit, sans qu'aucune exclusion préalable ne soit
nécessaire - `capture_existing_assignments()` ne prend donc **aucun**
paramètre d'exclusion, capture toutes les astreintes existantes sans
distinction, et laisse le filtrage habituel faire son travail semaine
par semaine.

---

## 4. Conclusion et recommandations

1. **Aucune valeur de fenêtre ne rend les trous "très rares" pour un
   effectif de 4 utilisateurs éligibles** - c'est le régime observé en
   production (retour terrain : "l'algo à 4 laisse toujours 2 trous").
   Le slack de 1 (§2.5) s'épuise sous charge cumulée, mathématiquement
   inévitable indépendamment du code.

2. **Recommandation organisationnelle (la plus fiable, prouvée par
   simulation)** : porter l'effectif éligible à l'astreinte à **6
   utilisateurs** (slack=3) - zéro trou observé dans toutes les
   simulations, y compris la plus chargée (30 congés/2 ans). Un
   effectif de 5 (slack=2) est déjà très proche de "rare" (0-2 trous
   sous charge lourde synthétique, probablement plus rare en usage
   réel typique).

3. **Ne pas toucher à la fenêtre ±30 jours** - aucune valeur testée (30
   à 120 jours) ne change significativement le résultat pour un
   effectif donné ; l'élargir peut même légèrement dégrader (plus de
   semaines réécrites, risque accru d'épuiser le budget de recherche
   `_MAX_SEARCH_NODES` ou de perturber une zone déjà stable).

4. **Amélioration algorithmique validée (§3.6)** : faire préférer au
   solveur l'utilisateur *déjà assigné* sur chaque semaine de la
   fenêtre plutôt que de rejouer l'ordre de rotation en aveugle -
   confirmé sur 20 essais indépendants : **-8% de trous cumulés à 30j,
   -16% à 60j**, exactement dans le régime à marge fine (N=4) où ça
   compte, **zéro régression** à N=5+. Gain réel mais modeste - ne
   remplace pas le levier organisationnel (point 2), le complète.
   Combiné à la fenêtre actuelle de 30 jours (ne pas l'élargir, même
   avec cette amélioration - §3.6), c'est la meilleure combinaison
   trouvée sur l'ensemble des tests.

5. En attendant, le mécanisme déjà en place (alerte de trous détectés
   sur `/admin/automation` + bouton "Combler les trous") reste le
   filet de sécurité correct pour rattraper les cas résiduels - conçu
   précisément pour ce type de trou résiduel plutôt rare.

---

## Annexe : scripts de simulation

Les 6 scripts Python utilisés (exécutent directement
`app.utils.automation.oncall_automation`/`advanced_shift_automation`,
aucune réimplémentation de la logique métier) :

- `window_sim.py` - simulation 1 (congé isolé, 2-8 utilisateurs, 30-120j)
- `window_sim2.py` - simulation 2 (deux congés séquentiels non superposés)
- `window_sim3.py` - simulation 3 (congés simultanés)
- `window_sim4.py` - simulation 4 (accumulation sur 2 ans, charge réaliste)
- `window_sim5.py` - simulation 5 (comparaison fenêtre vs réparation chirurgicale)
- `window_sim6.py` - simulation 6 (validation de la perturbation minimale, 20 graines)

Conservés dans le répertoire scratchpad de cette session
(non commités - purement des scripts d'investigation, pas du code
applicatif).
