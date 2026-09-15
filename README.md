# Cross-Seed Companion (CSC)

Compagnon web self-hosted pour [cross-seed](https://www.cross-seed.org/).

> Ce projet est développé avec l'assistance d'IA ("vibe codé"), assumé
> ouvertement. Par prudence, il évite volontairement tout mécanisme
> sensible : pas de SSH, pas d'accès au socket Docker, pas d'exécution de
> commande shell depuis la configuration.

## Fonctionnalités (phase 1)

- Synchronisation des indexers activés dans Prowlarr vers le bloc `torznab`
  de `config.js` de cross-seed, avec aperçu du diff, confirmation, et
  sauvegarde automatique avant toute écriture.

## Prérequis de déploiement

CSC doit tourner **sur le même hôte Docker que cross-seed**, avec le
répertoire de configuration de cross-seed monté en bind mount (lecture et
écriture) dans le container CSC.

## Installation

1. Copier `.env.example` vers `.env` et renseigner les valeurs.
2. Copier `docker-compose.example.yml` vers `docker-compose.yml`, ajuster le
   chemin du volume vers le répertoire de config de cross-seed.
3. `docker compose up -d`
4. Ouvrir `http://<host>:8000/sync`.

## Sécurité

CSC n'a **aucune authentification et aucune protection CSRF intégrée**.
`POST /sync/apply` réécrit un vrai fichier sur disque (`config.js` de
cross-seed), et l'écran de diff affiche la clé API Prowlarr **en clair**.
N'exposez jamais ce port directement sur internet : placez-le derrière
l'authentification de votre propre reverse proxy, ou restreignez-le à un
réseau privé/VPN.

## Variables d'environnement

| Variable | Requis | Rôle |
|---|---|---|
| `PROWLARR_URL` | oui | URL de base de Prowlarr |
| `PROWLARR_API_KEY` | oui | Clé API Prowlarr |
| `CROSSSEED_URL` | oui* | URL de base du daemon cross-seed |
| `CROSSSEED_API_KEY` | oui* | Clé API cross-seed |
| `CROSSSEED_CONFIG_PATH` | oui | Chemin (bind mount) vers le répertoire de config cross-seed |
| `SYNC_EXCLUDE_PUBLIC` | non | Exclut les indexers publics de la sync (défaut : `false`) |
| `SYNC_EXCLUDE_TAG` | non | Nom d'un tag Prowlarr à exclure de la sync |
| `SYNC_INTERVAL_MINUTES` | non | **Pas encore implémenté en phase 1** — réservé pour une phase future, n'a aucun effet pour l'instant |
| `DOCKER_MANAGER_URL` | non | Lien affiché après une sync vers votre outil de gestion Docker |

\* `CROSSSEED_URL`/`CROSSSEED_API_KEY` sont requis au démarrage (validation
de config) mais ne sont utilisés par aucune fonctionnalité de la phase 1 —
ce sont des emplacements réservés pour une fonctionnalité future.

## Important

Après une synchronisation, cross-seed doit être **redémarré manuellement**
pour prendre en compte la nouvelle configuration (CSC ne redémarre jamais de
container automatiquement).

## Licence

MIT — voir [`LICENSE`](./LICENSE).
