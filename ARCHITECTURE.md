# Architecture

Résumé d'onboarding généré à partir du code de la branche `feature/referentiel_detection`.
Le diagramme détaillé est dans [`docs/architecture.excalidraw`](docs/architecture.excalidraw).

Pour la spécification des règles, voir [`docs/detections_rules.md`](docs/detections_rules.md) ;
pour la watchlist, [`docs/watchlist.md`](docs/watchlist.md).

## Architecture overview

Vigil est un **monolithe Python mono-processus, organisé en couches**, piloté par une CLI.
Il n'y a ni serveur HTTP, ni frontend, ni base de données, ni broker de messages, ni
authentification : un analyste lance un binaire console, qui consomme un flux de
certificats et écrit sur le terminal.

```
Logs Certificate Transparency
        │  (via un serveur CertStream auto-hébergé)
        ▼
CLI vigil  ──►  Ingestion  ──►  CertEvent  ──►  Détection  ──►  [Reason]  ──►  stdout / stderr
(Typer + menu)  vigil.ingest    vigil.models    vigil.detect                   (rich / typer.echo)
                                                    ▲
                                    data/watchlist.yml, data/detection_terms.yml
```

Le découpage en trois couches est explicitement conçu pour être remplaçable : les couches
ne se parlent qu'à travers `CertEvent` et `Finding` (`src/vigil/models.py`), ce qui permet
de réécrire l'ingestion dans un autre langage sans toucher à la détection.

Deux caractéristiques structurantes de l'état actuel :

- **La détection est partielle.** 2 familles de règles sur 6 sont implémentées
  (morphologique, référentielle) ; les 4 autres sont des stubs qui lèvent
  `NotImplementedError` et ne sont jamais appelées par le pipeline.
- **La chaîne de restitution s'arrête au terminal.** `detect_event()` renvoie des tuples
  `(domaine, [Reason])` ; aucun `Finding` n'est construit, aucun score n'est calculé
  (`Reason.points` vaut toujours `0`) et `JSONLWriter` n'est importé nulle part.

## Main components

| Composant | Chemin | Responsabilité |
|---|---|---|
| CLI | `src/vigil/cli/commands.py` | App Typer. `watch` en mode options, callback sans sous-commande en mode interactif. |
| Menu interactif | `src/vigil/cli/menu.py` | Prompts `questionary` (source, familles, règles, métriques) → `MenuConfig`. Ne propose que les familles listées dans `IMPLEMENTED_FAMILIES`. |
| Boucle de run | `src/vigil/cli/stream.py` | `asyncio.run()` sur `Source.stream()` : filtrage des wildcards, appel de la détection, affichage, panneau `rich.Live` des métriques. |
| Contrat d'ingestion | `src/vigil/ingest/base.py` | `Source` : `async def stream() -> AsyncIterator[CertEvent]`. Seule interface exposée par la couche. |
| Source live | `src/vigil/ingest/certstream.py` | Client websocket : reconnexion avec backoff 1 s → 60 s, idle timeout 45 s, mapping message brut → `CertEvent`. |
| Source offline | `src/vigil/ingest/fixtures.py` | Replay d'un JSONL de messages CertStream bruts, via le même parseur que la source live. |
| Filtre | `src/vigil/ingest/filters.py` | `strip_wildcards()` retire les SAN `*.` ; le certificat est ignoré s'il ne reste aucun domaine. |
| Modèles partagés | `src/vigil/models.py` | `CertEvent`, `Reason`, `DomainVerdict`, `Finding` (pydantic, validation UTC des dates). |
| Orchestration détection | `src/vigil/detect/pipeline.py` | `detect_event()` boucle sur les SAN ; `evaluate_domain()` enchaîne les familles actives. |
| Registre | `src/vigil/detect/registry.py` | Enums `Family` (6) et `Rule` (18) + `RULE_FAMILY`. Les identifiants (`R-01`, `M-04`, …) sont le contrat stable des findings. |
| Familles de règles | `src/vigil/detect/families/` | Une famille par module. Au plus **une** règle retenue par famille et par domaine (première correspondance, par spécificité décroissante). |
| Primitives | `src/vigil/detect/techniques/` | Fonctions pures : `names.parse_domain()` (découpage PSL via `tldextract`, snapshot hors ligne), `levenshtein.bounded_levenshtein()`. |
| Entrées de détection | `src/vigil/detect/data/` | `watchlist.py` (marques + domaines légitimes), `terms.py` (termes lexicaux validés pydantic), `thresholds.py` (seuils numériques). |
| Métriques | `src/vigil/reporting/metrics.py` | `DetectionMetrics` : débit, temps d'analyse min/moyen/max, compteur par règle, rendu via `snapshot()`. |
| Sortie | `src/vigil/output/jsonl.py` | `JSONLWriter` : un `Finding` par ligne. **Non câblé** — `--output` est accepté mais ignoré. |
| Scripts | `scripts/` | `build_watchlist.py` (build de la watchlist), `certstream_kpis.py` / `detection_kpis.py` (mesures de débit), `start-certstream.sh` (lancement du feed local), `build_architecture_diagram.py` (régénère le diagramme). |

### État des règles

| Famille | Règles | État |
|---|---|---|
| Morphologique | M-01 ≥ 3 tirets · M-02 registrable > 40 car. · M-03 ≥ 4 labels · M-04 ≥ 3 chiffres consécutifs | implémentée |
| Référentielle | R-01 marque hors du domaine enregistrable · R-02 marque + token type TLD · R-03 Levenshtein ≤ 2 · R-04 marque + terme d'auth | implémentée |
| Lexicale | L-01 → L-04 | stub (termes déjà présents dans `data/detection_terms.yml`) |
| Encodage | E-01 scripts Unicode mélangés · E-02 punycode | stub |
| Statistique | S-01 → S-03 | stub (nécessite une baseline de corpus) |
| Métadonnées certificat | C-01 SAN > 200 | stub (seuil défini dans `thresholds.py`) |

## Main workflows

### W1 — Run de détection live

`vigil watch --source certstream --detection --metrics`

1. `commands.watch()` lit les options Typer et avertit si la watchlist est absente.
2. Construction de la `Source` : `CertStreamSource(url)` ou `FixtureSource(path)`.
3. Chargement des entrées de détection : marques surveillées, exceptions chiffrées pour
   M-04 (dérivées des domaines légitimes), termes lexicaux.
4. `stream._run_stream()` → `asyncio.run()` : un seul event loop, aucun thread.
5. Connexion websocket, `recv()` sous garde d'inactivité de 45 s, reconnexion avec backoff.
6. `parse_certstream_message()` → `CertEvent` ; les messages autres que
   `certificate_update` sont ignorés.
7. `strip_wildcards()` retire les SAN `*.`.
8. `detect_event()` : pour chaque SAN, `parse_domain()` puis les familles actives (voir W3).
9. Résultat : `[(domaine, [Reason])]`.
10. Sortie : avec `--metrics`, `DetectionMetrics.record()` agrège et masque les lignes
    individuelles ; sinon une ligne `DETECT …` par domaine sur stdout.
11. Toutes les `--metrics-interval` secondes, `snapshot()` alimente un panneau
    `rich.Live` sur stderr (simple reprint si la sortie n'est pas un terminal).
12. Fin de flux ou Ctrl-C : snapshot final puis `done: N detection(s)` sur stderr.

### W2 — Run interactif

`vigil` sans sous-commande : le callback Typer détecte l'absence de sous-commande, pose les
questions (source, détection, familles puis règles, métriques), affiche un récapitulatif,
charge la watchlist et les termes si la détection est active, puis entre dans la même
boucle que W1 (les wildcards y sont toujours filtrés).

### W3 — Évaluation d'un domaine

Chemin synchrone et pur, exécuté pour chaque SAN :

1. `parse_domain()` : minuscules, point final retiré, découpage PSL hors ligne.
2. Famille morphologique dans l'ordre M-01 → M-04 ; M-04 ignore les suites de chiffres
   présentes dans les domaines légitimes de la watchlist (pour ne pas déclencher sur `365`).
3. Première règle vraie → un `Reason`, la famille s'arrête là.
4. Famille référentielle dans l'ordre R-01 → R-04 ; R-01, R-02 et R-04 tokenisent le cœur
   enregistrable sur `[.-]`, R-03 compare par Levenshtein borné à chaque marque surveillée
   (pré-filtre sur la différence de longueur, correspondance exacte exclue).
5. Au plus 2 `Reason` par domaine (un par famille active). Le domaine est retenu s'il en
   reste au moins un.

### W4 — Reconstruction de la watchlist

`python scripts/build_watchlist.py` — hors ligne, manuel, jamais déclenché par la CLI :
lecture du seed curé, téléchargement (ou cache) de la liste Tranco, parcours par rang avec
filtres (denylist CDN, longueur de label, tokens négatifs et étrangers), classification
région puis secteur, déduplication, cap à 10 000 entrées, écriture de `data/watchlist.yml`.

## External dependencies

| Dépendance | Nature | Moment |
|---|---|---|
| Logs Certificate Transparency (Let's Encrypt, Google, Sectigo, IPng, TrustAsia…) | source de données, atteinte **indirectement** | runtime |
| [`certstream-server-rust`](https://github.com/reloading01/certstream-server-rust) | websocket `ws://127.0.0.1:8080/` par défaut, endpoint `/health` ; **hors dépôt**, à construire et lancer séparément. `certstream.calidog.io` est hors service et n'est pas utilisé | runtime |
| `tranco-list.eu` | HTTPS, `top-1m.csv.zip`, `urllib` standard | build de la watchlist uniquement |
| Public Suffix List | snapshot embarqué dans `tldextract` (`suffix_list_urls=()`) — aucune requête réseau pendant la détection | runtime, local |

Aucun SaaS, aucun fournisseur cloud, aucun service de paiement, d'e-mail, d'analytics, de
CDN, de monitoring ni d'authentification.

Dépendances Python : `pydantic`, `websockets`, `typer`, `questionary`, `rich`, `pyyaml`,
`tldextract`. Dev : `pytest`, `pytest-asyncio` (mode strict), `ruff`. Build : `hatchling`,
avec l'entry point console `vigil = "vigil.cli:app"`.

## Data stores

Il n'y a **aucune base de données, aucun cache et aucun stockage objet**. Tout l'état
durable est un fichier :

| Fichier | Rôle |
|---|---|
| `data/watchlist.yml` | ~10 000 marques (`name`, `sector`, `region`, `tier`, `legitimate_domains`), généré. Lu au démarrage d'un run avec détection. |
| `data/brands_core.seed.yml` | Source curée du tier `core`, écrite à la main. |
| `data/detection_terms.yml` | Vocabulaire des règles L-01/L-02/L-04 et R-04, éditable par un analyste. |
| `tests/fixtures/certs.jsonl` | 5 messages CertStream bruts pour le replay offline et les tests. |
| `data/state/tranco_top1m.csv` | Cache de téléchargement Tranco, gitignoré, utilisé seulement au build de la watchlist. |
| `schemas/finding.v1.json` | Contrat JSON Schema destiné aux consommateurs externes. |

Rien n'est écrit au runtime : l'état de détection vit en mémoire et disparaît à l'arrêt.

## Async processing

L'asynchronisme se limite à l'itération du flux réseau :

- **Un seul event loop `asyncio`**, lancé par `asyncio.run()` dans `cli/stream.py`.
- La détection est entièrement **synchrone** et exécutée dans cet event loop ; elle
  n'effectue aucune I/O.
- Le seul mécanisme de résilience est la boucle de reconnexion de `CertStreamSource`
  (backoff exponentiel 1 s → 60 s, idle timeout 45 s).
- **Pas de queue, pas de worker, pas de tâche planifiée, pas d'événement publié, pas de
  webhook.** Les reconstructions de watchlist et les mesures de KPI sont des scripts
  lancés à la main.

## Infrastructure

Le dépôt ne contient **ni Dockerfile, ni docker-compose, ni manifeste Kubernetes, ni IaC,
ni pipeline CI** (`.github/` est absent). Ce qui est déductible est une exécution locale à
deux processus :

1. `certstream-server-rust` — externe au dépôt, écoute sur le port 8080. Lancé par
   `scripts/start-certstream.sh` (`nohup` + `disown`, binaire attendu sous
   `~/Projet/certstream-server-rust`, santé vérifiée sur `http://localhost:8080/health`).
2. La CLI `vigil` — processus Python unique, arrêté par Ctrl-C (`KeyboardInterrupt`
   absorbé).

Qualité : `pytest` (9 fichiers de tests couvrant ingestion, filtres, pipeline, familles
morphologique et référentielle, registre, métriques, CLI et watchlist ; `vigil.output`
n'est pas testé) et `ruff` (`E,F,I,UP,B`, ligne 100), tous deux configurés dans
`pyproject.toml`.

## Écarts relevés entre le code, la documentation et les contrats

Points à trancher, tous visibles dans la zone E du diagramme :

- `detect/scoring.py` est décrit dans `docs/architecture.md` et dans
  `src/vigil/detect/__init__.py`, mais le module n'existe pas. Aucun score n'est calculé et
  `docs/scoring.md` est vide.
- La chaîne `Finding` n'est pas branchée : `detect_event()` renvoie des tuples,
  `DomainVerdict` et `Finding` ne sont jamais construits, `JSONLWriter` n'est jamais importé.
- `schemas/finding.v1.json` diverge de `models.Finding` : le schéma expose
  `matched_watch_target` et `reasons` à plat, le modèle expose `verdicts[]` et
  `skipped_domains`.
- `Finding.skipped_domains` et `docs/detections_rules.md` demandent de compter et lister les
  wildcards ; `strip_wildcards()` les retire dès l'ingestion sans les conserver.
- `docs/architecture.md` référence `docs/adr/0001-python-first.md` ; le dossier `docs/adr/`
  n'existe pas.
- `scripts/detection_kpis.py` ne charge ni marques surveillées ni termes : seules les règles
  `M-*` peuvent y correspondre, ses KPI ne sont donc pas représentatifs d'un run complet.

## Diagram

Le diagramme détaillé est dans **`docs/architecture.excalidraw`** (ouvrable sur
[excalidraw.com](https://excalidraw.com) via *Open* / glisser-déposer). Il est organisé en
cinq zones :

- **Zone A — System overview** : vue d'ensemble, du terminal de l'analyste au flux CT.
- **Zone B — Detailed architecture** : modules réels, responsabilités, dépendances.
- **Zone C — Main workflows** : les quatre parcours W1 à W4, étape par étape.
- **Zone D — External dependencies** : systèmes externes et dépendances Python.
- **Zone E — Infrastructure / runtime** : processus locaux et écarts relevés.

Une légende en haut à droite donne le code couleur (bleu = points d'entrée, violet =
ingestion et runtime, orange = logique de détection, turquoise = contrats partagés, vert =
données sur disque, rose = systèmes externes, gris = infra et notes), la sémantique des
flèches et la signification des badges `stub`, `non câblé`, `dérive` et `à confirmer`.

Le fichier est généré : `python scripts/build_architecture_diagram.py`. Le script vérifie
qu'aucune forme ne se chevauche et qu'aucun texte ne dépasse de sa carte.
