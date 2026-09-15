# Cross-Seed Companion (CSC) — Design

Date : 2026-09-15
Statut : approuvé pour passage en plan d'implémentation

## Contexte et objectif

Cross-Seed Companion (CSC) est un compagnon web self-hosted, open source, pour
[cross-seed](https://www.cross-seed.org/). Il vise à être publié publiquement
(ex: r/selfhosted), donc conçu pour être configurable et fonctionner sur des
setups variés, pas seulement celui de l'auteur.

Contrainte transversale : **CSC est un projet ouvertement "vibe codé"**
(développé avec assistance IA), et la communauté self-hosted/open-source est
historiquement méfiante envers ce type de projet, en particulier sur les
questions de sécurité. En conséquence, chaque décision de design privilégie
le mécanisme le moins sensible disponible, même quand une alternative plus
"puissante" existerait :

- pas de SSH (clés/config embarquées dans le container)
- pas d'accès au socket Docker
- pas d'exécution de commande shell arbitraire depuis la config utilisateur

## Périmètre (MVP)

CSC est livré comme **une seule image Docker**. Quatre fonctionnalités,
livrables indépendamment (phases) mais formant un seul produit :

1. Synchronisation des indexers Prowlarr → cross-seed
2. Déclenchement d'actions API cross-seed depuis l'UI, extensible
3. Logs cross-seed en temps réel
4. Liste des torrents ajoutés par cross-seed

Hors périmètre v1 : intégration qBittorrent, redémarrage automatique de
cross-seed, support multi-hôtes (cross-seed sur un serveur différent de CSC).

## Stack

**Python (FastAPI) + htmx/Alpine.js**, rendu côté serveur, pas de build
frontend séparé ni de Node.js dans l'image. Justification : cohérent avec le
langage du script existant de l'utilisateur (`/opt/scripts/sync-crossseed-indexers.py`,
facilite la maintenance/évolution par vibe coding), FastAPI a du SSE natif
(utile pour les logs temps réel), et une UI server-rendered en htmx suffit
largement pour un dashboard de boutons/tableaux — pas besoin d'une SPA.

Alternative envisagée et écartée : Go (binaire unique, image minimale, très
idiomatique dans l'écosystème r/selfhosted) — écarté pour rester dans un
langage que l'utilisateur peut relire et retoucher facilement lui-même.

## Topologie de déploiement

Contrainte de topologie explicitement acceptée : **CSC doit tourner sur le
même hôte Docker que cross-seed**. Toute donnée provenant de cross-seed passe
par un bind mount, jamais par SSH ni par un agent réseau :

- Le répertoire de config de cross-seed (`/config` côté cross-seed, contenant
  `config.js`, `logs/`, `cross-seed.db`) est monté en bind mount dans le
  container CSC.
- `config.js` doit être accessible en lecture **et** écriture (fonctionnalité 1).
- `logs/` peut être monté en lecture seule (fonctionnalités 3 et 4).
- `cross-seed.db` (SQLite interne) n'est **pas** utilisé : son schéma n'est
  pas documenté/stable, contrairement aux logs qui sont la sortie publique de
  l'outil.

Prowlarr n'a pas besoin d'être sur le même hôte : il est joignable via son URL
HTTP + clé API, comme n'importe quelle intégration *arr classique.

## Configuration

Entièrement piloté par variables d'environnement, plus un fichier optionnel
pour les actions API custom (fonctionnalité 2) :

| Variable | Rôle |
|---|---|
| `PROWLARR_URL` | URL de base de Prowlarr |
| `PROWLARR_API_KEY` | Clé API Prowlarr |
| `CROSSSEED_URL` | URL de base du daemon cross-seed (ex: `http://localhost:2468`) |
| `CROSSSEED_API_KEY` | Clé API cross-seed (`/api/job`, `/api/webhook`, `/api/ping`) |
| `CROSSSEED_CONFIG_PATH` | Chemin (bind mount) vers le répertoire de config cross-seed |
| `SYNC_EXCLUDE_PUBLIC` | bool — exclut les indexers `privacy=public` de la sync |
| `SYNC_EXCLUDE_TAG` | Nom d'un tag Prowlarr — indexers portant ce tag exclus de la sync |
| `SYNC_INTERVAL_MINUTES` | Optionnel — active une sync périodique automatique. Absent = déclenchement manuel uniquement |
| `DOCKER_MANAGER_URL` | Optionnel — lien affiché après une sync pour aller redémarrer cross-seed (Portainer, Dockge, etc.) |

CSC ne maintient pas sa propre base de données au démarrage : son état est
recalculé à la volée depuis Prowlarr, `config.js`, et les logs cross-seed.

## Fonctionnalité 1 — Synchronisation indexers Prowlarr → cross-seed

Remplace la logique du script existant, généralisée pour n'importe quel
setup (pas d'hypothèse sur un hôte NAS, un nom de container, ou un accès SSH).

**Déclenchement** : bouton "Sync now" dans l'UI, et/ou sync périodique
automatique si `SYNC_INTERVAL_MINUTES` est défini.

**Flux** :

1. `GET {PROWLARR_URL}/api/v1/indexer` avec `X-Api-Key`.
2. `GET {PROWLARR_URL}/api/v1/tag` pour résoudre `SYNC_EXCLUDE_TAG` (nom) en id de tag.
3. Filtrer : `enable == true`, exclure `privacy == "public"` si
   `SYNC_EXCLUDE_PUBLIC`, exclure les indexers portant le tag exclu.
4. Construire les URLs torznab au format officiel cross-seed :
   `{PROWLARR_URL}/{indexer_id}/api?apikey={PROWLARR_API_KEY}`.
5. Lire `config.js` depuis `CROSSSEED_CONFIG_PATH`, repérer le bloc
   `torznab: [...]` par une expression régulière tolérante (couvre un simple
   tableau plat ou un tableau suivi d'un `.map(...)`, comme dans certains
   tutoriels communautaires). **Si le motif n'apparaît pas exactement une
   fois, abandon sans rien écrire**, avec message d'erreur explicite —
   reprend la sécurité déjà présente dans le script existant.
6. Calculer le diff (URLs ajoutées/retirées) et l'afficher dans l'UI pour
   confirmation avant écriture.
7. Sur confirmation : backup horodaté (`config.js.bak.<timestamp>`), puis
   remplacement du bloc torznab repéré par un **tableau plat d'URLs
   complètes** (normalise n'importe quel format d'origine).

**Pas de redémarrage automatique** de cross-seed (cf. contraintes
transversales — pas de socket Docker, et aucun mécanisme de rechargement à
chaud documenté chez cross-seed). Après écriture, l'UI affiche un message
"redémarre cross-seed pour appliquer" et, si `DOCKER_MANAGER_URL` est défini,
un lien direct vers l'outil de gestion Docker de l'utilisateur.

## Fonctionnalité 2 — Actions API déclaratives

Chaque action est une définition structurée exécutée par le backend via un
appel HTTP — jamais de `subprocess`/shell. Schéma d'une action :

```yaml
- id: crossseed-search
  title: "Cross-seed : lancer une recherche"
  method: POST
  url: "${CROSSSEED_URL}/api/job?apikey=${CROSSSEED_API_KEY}"
  body:
    name: search
  confirm: "Lance une recherche cross-seed sur les torrents éligibles. Confirmer ?"
```

**Actions intégrées** (livrées par défaut, basées sur l'API HTTP officielle
de cross-seed découverte dans sa doc) :

- Recherche (`job: search`)
- Recherche complète, ignore les exclusions (`job: search` +
  `ignoreExcludeRecentSearch`/`ignoreExcludeOlder`)
- Notifier un infoHash (`/api/webhook`, argument `infoHash`)
- Cleanup, RSS, mise à jour des capacités indexers (`job: cleanup` / `rss` /
  `updateIndexerCaps`)
- Badge d'état santé cross-seed, basé sur `GET /api/ping` (affiché en continu
  dans l'UI, pas un bouton d'action)

**Actions custom** : un fichier YAML optionnel monté dans le container permet
d'ajouter de nouvelles actions suivant le même schéma (méthode, URL templatée
avec variables d'environnement, corps de requête, arguments typés —
confirmation, texte libre, etc.), sans toucher au code.

## Fonctionnalité 3 — Logs cross-seed en temps réel

Format confirmé sur un vrai déploiement (`/config/logs/` de cross-seed) :

- Trois fichiers par niveau, rotation quotidienne : `error.<YYYY-MM-DD>.log`,
  `info.<YYYY-MM-DD>.log`, `verbose.<YYYY-MM-DD>.log`, chacun avec un
  symlink `<level>.current.log` pointant vers le fichier du jour.
  `verbose.current.log` est le superset le plus complet (contient aussi les
  entrées `info`) — c'est la source à utiliser pour l'affichage temps réel.
- Ligne standard : `YYYY-MM-DD HH:MM:SS.mmm <level>: [<component>] <message>`
  (ex: `2026-09-15 00:19:28.390 info: [scheduler] starting job: inject`).
- **Entrées multi-lignes** : une entrée `error:` peut être suivie de lignes
  de continuation sans préfixe timestamp (stack trace JS). Le parseur doit
  détecter l'absence de timestamp en tête de ligne et rattacher cette ligne
  à l'entrée précédente plutôt que d'en créer une nouvelle.
- **Rotation** : le fichier `current.log` est un **symlink** dont la cible
  change chaque jour (pas une simple troncature). Le tail doit détecter le
  changement de cible du symlink et ré-ouvrir le nouveau fichier cible.
- Bind mount lecture seule du répertoire `logs/`.
- Diffusion vers l'UI via Server-Sent Events (SSE), filtre texte libre côté
  client (pas de recherche côté serveur).

## Fonctionnalité 4 — Torrents ajoutés par cross-seed

Confirmé sur un vrai log (`verbose.2026-09-14.log`) : la ligne de succès
n'est **pas** émise par le composant `[inject]`, mais par celui du job qui a
trouvé le match (`[rss]` pour un scan RSS, `[search]`/`[announce]` selon le
déclencheur) :

```
info: [rss] Found <name> [<hash8>...] on <tracker> by MATCH from torrentClient (<name> [<hash8>...@<client>]) - injected
```

Le hash de torrent n'apparaît dans les logs que tronqué à 8 caractères
(troncature faite par cross-seed lui-même) — suffisant pour l'affichage
prévu (nom, tracker, date), pas pour retrouver l'infoHash complet.

Le suffixe final (`- injected`) dépend du mode d'action configuré dans
cross-seed (`action: 'inject'` vs `'save'`) ; le parseur capture la fin de
ligne après "by MATCH from torrentClient (...) - " comme un champ `outcome`
libre plutôt que de figer `injected` en dur, pour rester correct si
l'utilisateur tourne en mode `save` (`- saved` ou équivalent, à confirmer si
besoin le jour où ce mode sera testé — non bloquant, traité par défensivité :
toute ligne "Found ... by MATCH from torrentClient" est comptée comme un
ajout réussi, quel que soit l'`outcome` exact).

Les lignes `[inject] Linking ...` / `error: [qbittorrent@...] Injection
failed ...` (vues dans l'échantillon du 14/09, torrent "Fight Club" en échec
répété — problème pré-existant côté qBittorrent de l'utilisateur, sans lien
avec CSC) sont explicitement **ignorées** par ce parseur : ce sont des
tentatives/échecs, pas des ajouts réussis.

Affichage : liste simple (nom du torrent, tracker source, date/heure).
- Intégration qBittorrent explicitement **hors scope v1** — envisageable
  plus tard si des informations supplémentaires (statut, ratio) sont
  nécessaires, mais la fonctionnalité de base ne doit pas en dépendre.

## Gestion des erreurs

- Prowlarr ou cross-seed injoignables → badge de statut visible dans l'UI,
  aucune fonctionnalité ne doit planter silencieusement.
- Échec de détection fiable du bloc torznab dans `config.js` → abandon propre
  sans écriture, message d'erreur explicite à l'utilisateur.
- Répertoire de logs absent ou chemin de bind mount incorrect → message
  clair ("logs introuvables, vérifie le bind mount"), pas d'erreur muette.

## Tests

Unitaires (mockés, pas d'e2e contre de vrais services) :

- Génération des URLs torznab à partir d'indexers Prowlarr.
- Filtrage des indexers (exclusion public / tag).
- Détection et remplacement du bloc torznab dans `config.js`, sur plusieurs
  formats d'entrée (tableau plat, `.map()`).
- Parsing des lignes de log : découpage en entrées, rattachement des lignes
  de continuation sans timestamp (stack traces) à l'entrée précédente,
  extraction des lignes "Found ... by MATCH from torrentClient (...) - ..."
  (plusieurs composants : `rss`, `search`, `announce`).

## Licence et structure du dépôt

- Licence **MIT** (standard dans l'écosystème r/selfhosted, pas de risque de
  "cloud strip-mining" à couvrir pour un outil companion comme celui-ci).
- `LICENSE`, `README.md` (installation Docker, variables d'environnement,
  transparence assumée sur le côté vibe-codé du projet), `.env.example`,
  `CONTRIBUTING.md` minimal.
