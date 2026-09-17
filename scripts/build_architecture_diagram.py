#!/usr/bin/env python3
"""Regenerate docs/architecture.excalidraw: the architecture and workflow map.

Deterministic layout engine (cards, titled groups, numbered flows) plus geometric
self-checks: no overlapping shapes, no text spilling out of its card.

    python scripts/build_architecture_diagram.py
"""

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "architecture.excalidraw"

rng = random.Random(20260917)
els = []
by_id = {}
_uid = [0]

# ---------------------------------------------------------------- palette
PAL = {
    "entry":    ("#1971c2", "#e7f5ff"),   # blue   - entry points / interfaces
    "ingest":   ("#6741d9", "#f3f0ff"),   # violet - ingestion / runtime services
    "detect":   ("#e8590c", "#fff4e6"),   # orange - business logic / détection
    "data":     ("#2f9e44", "#ebfbee"),   # green  - data, config on disk
    "external": ("#c2255c", "#ffe3e3"),   # pink   - external systems
    "infra":    ("#495057", "#f1f3f5"),   # grey   - infra / tooling / notes
    "model":    ("#0c8599", "#e3fafc"),   # teal   - shared contracts
}
INK = "#1e1e1e"
DIM = "#5c636a"

TS, PS, BS = 17, 13, 14           # title / path / body font sizes
CW = 0.545                        # avg char-width ratio for Helvetica


def nid(prefix="el"):
    _uid[0] += 1
    return f"{prefix}{_uid[0]}"


def tw(s, size):
    return len(s) * size * CW


def wrap(text_, size, maxw):
    words, lines, cur = text_.split(), [], ""
    for w in words:
        cand = f"{cur} {w}".strip()
        if cur and tw(cand, size) > maxw:
            lines.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines or [""]


def base(kind, x, y, w, h, **kw):
    e = {
        "id": kw.pop("id", None) or nid(),
        "type": kind,
        "x": round(float(x), 2), "y": round(float(y), 2),
        "width": round(float(w), 2), "height": round(float(h), 2),
        "angle": 0,
        "strokeColor": kw.pop("strokeColor", INK),
        "backgroundColor": kw.pop("backgroundColor", "transparent"),
        "fillStyle": kw.pop("fillStyle", "solid"),
        "strokeWidth": kw.pop("strokeWidth", 1),
        "strokeStyle": kw.pop("strokeStyle", "solid"),
        "roughness": 0,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "roundness": kw.pop("roundness", None),
        "seed": rng.randint(1, 2**31),
        "version": 1,
        "versionNonce": rng.randint(1, 2**31),
        "isDeleted": False,
        "boundElements": kw.pop("boundElements", []),
        "updated": 1,
        "link": None,
        "locked": False,
    }
    e.update(kw)
    els.append(e)
    by_id[e["id"]] = e
    return e


def text(x, y, s, size=BS, color=INK, align="left"):
    lines = s.split("\n")
    w = max(tw(ln, size) for ln in lines)
    h = len(lines) * size * 1.25
    return base("text", x, y, w, h, strokeColor=color, text=s, fontSize=size,
                fontFamily=2, textAlign=align, verticalAlign="top", containerId=None,
                baseline=round(size * 0.8), lineHeight=1.25, originalText=s)


def rect(x, y, w, h, kind="infra", fill=True, dashed=False, stroke_w=1, radius=3):
    st, bg = PAL[kind]
    return base("rectangle", x, y, w, h, strokeColor=st,
                backgroundColor=bg if fill else "transparent",
                fillStyle="solid", strokeWidth=stroke_w,
                strokeStyle="dashed" if dashed else "solid",
                roundness={"type": radius} if radius else None)


def hline(x, y, w, color=DIM):
    return base("line", x, y, w, 0, strokeColor=color, strokeWidth=2,
                points=[[0, 0], [float(w), 0]], lastCommittedPoint=None,
                roundness={"type": 2})


def arrow(p1, p2, color=INK, style="solid", label=None, width=2,
          waypoints=(), start=None, end=None, label_dx=8, label_dy=-20,
          label_color=None):
    pts = [(0.0, 0.0)]
    for wx, wy in waypoints:
        pts.append((wx - p1[0], wy - p1[1]))
    pts.append((p2[0] - p1[0], p2[1] - p1[1]))
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    a = base("arrow", p1[0], p1[1], max(xs) - min(xs), max(ys) - min(ys),
             strokeColor=color, strokeWidth=width, strokeStyle=style,
             roundness={"type": 2},
             points=[[round(u, 2), round(v, 2)] for u, v in pts],
             lastCommittedPoint=None, startArrowhead=None, endArrowhead="arrow",
             startBinding=({"elementId": start, "focus": 0, "gap": 6}
                           if start and not waypoints else None),
             endBinding=({"elementId": end, "focus": 0, "gap": 6}
                         if end and not waypoints else None))
    if start and not waypoints and start in by_id:
        by_id[start]["boundElements"].append({"id": a["id"], "type": "arrow"})
    if end and not waypoints and end in by_id:
        by_id[end]["boundElements"].append({"id": a["id"], "type": "arrow"})
    if label:
        if waypoints:
            mx = (waypoints[0][0] + waypoints[-1][0]) / 2
            my = (waypoints[0][1] + waypoints[-1][1]) / 2
        else:
            mx = (p1[0] + p2[0]) / 2
            my = (p1[1] + p2[1]) / 2
        text(mx + label_dx, my + label_dy, label, 13, label_color or color)
    return a


def top(g):
    return (g["x"] + g["width"] / 2, g["y"])


def bottom(g):
    return (g["x"] + g["width"] / 2, g["y"] + g["height"])


def left(g):
    return (g["x"], g["y"] + g["height"] / 2)


def right(g):
    return (g["x"] + g["width"], g["y"] + g["height"] / 2)


# ---------------------------------------------------------------- cards
PAD = 14


def card(x, y, w, spec, emit=True):
    """spec = (title, path|None, [body lines], kind, badge|None)"""
    title, path, body, kind, badge = spec
    badge_w = (tw(badge, 12) + 22) if badge else 0
    tlines = wrap(title, TS, w - 2 * PAD - badge_w - 6)
    plines = wrap(path, PS, w - 2 * PAD) if path else []
    blines = []
    for b in body:
        blines.extend(wrap("- " + b, BS, w - 2 * PAD - 4))

    cy = PAD
    cy += len(tlines) * TS * 1.25
    if plines:
        cy += 3 + len(plines) * PS * 1.25
    if blines:
        cy += 8 + len(blines) * BS * 1.25
    h = cy + PAD - 2

    if not emit:
        return h, None

    r = rect(x, y, w, h, kind)
    st, _ = PAL[kind]
    yy = y + PAD - 2
    text(x + PAD, yy, "\n".join(tlines), TS, st)
    yy += len(tlines) * TS * 1.25
    if plines:
        yy += 3
        text(x + PAD, yy, "\n".join(plines), PS, DIM)
        yy += len(plines) * PS * 1.25
    if blines:
        yy += 8
        text(x + PAD, yy, "\n".join(blines), BS, "#343a40")
    if badge:
        bw = tw(badge, 12) + 14
        rect(x + w - bw - 10, y + 9, bw, 22, "infra", radius=3)
        text(x + w - bw - 3, y + 12, badge, 12, "#868e96")
    return h, r


def group(x, y, w, title, specs, cols, kind="infra", gap=28, subtitle=None):
    """Emit a titled container with a grid of cards. Returns (container, {i: rect})."""
    gpad = 22
    sub_lines = wrap(subtitle, 13, w - 2 * gpad) if subtitle else []
    head = 30 + (12 + 18 * len(sub_lines) if sub_lines else 0)
    cw = (w - 2 * gpad - (cols - 1) * gap) / cols

    heights = [card(0, 0, cw, s, emit=False)[0] for s in specs]
    rows = [specs[i:i + cols] for i in range(0, len(specs), cols)]
    row_h = [max(heights[i:i + cols]) for i in range(0, len(specs), cols)]
    total = gpad + head + sum(row_h) + gap * (len(rows) - 1) + gpad

    st, _ = PAL[kind]
    cont = rect(x, y, w, total, kind, fill=False, dashed=True, stroke_w=2, radius=3)
    text(x + gpad, y + gpad - 4, title, 21, st)
    for i, ln in enumerate(sub_lines):
        text(x + gpad, y + gpad + 28 + i * 18, ln, 13, DIM)

    cards = {}
    cy = y + gpad + head
    k = 0
    for ri, row in enumerate(rows):
        cx = x + gpad
        for spec in row:
            _, r = card(cx, cy, cw, spec)
            cards[k] = r
            k += 1
            cx += cw + gap
        cy += row_h[ri] + gap
    return cont, cards


def zone_title(x, y, label, desc):
    text(x, y, label, 28, INK)
    for i, ln in enumerate(wrap(desc, 14, 2560)):
        text(x, y + 38 + i * 18, ln, 14, DIM)
    n = len(wrap(desc, 14, 2560))
    hline(x, y + 44 + n * 18, 2600)
    return y + 72 + n * 18


# ================================================================ TITLE
text(60, 40, "Vigil - architecture & workflows", 36, INK)
text(60, 92,
     "Détection d'infrastructure de phishing à partir des logs Certificate Transparency  |  "
     "Python 3.12  |  CLI mono-processus  |  généré depuis le code "
     "(branche feature/referentiel_detection)",
     14, DIM)
hline(60, 124, 2600)

# ================================================================ LEGEND
LX, LY = 1740, 190
rect(LX, LY, 920, 486, "infra", radius=3)
text(LX + 22, LY + 16, "Légende", 21, "#495057")

chips = [
    ("entry", "Point d'entrée / interface (CLI, scripts)"),
    ("ingest", "Ingestion & runtime (async, réseau)"),
    ("detect", "Logique métier - détection"),
    ("model", "Contrats partages (models, JSON Schema)"),
    ("data", "Données & configuration sur disque"),
    ("external", "Système externe au dépôt"),
    ("infra", "Infra / outillage / notes"),
]
cy = LY + 54
for kind, lbl in chips:
    rect(LX + 24, cy, 34, 20, kind, radius=2)
    text(LX + 70, cy + 1, lbl, 14, "#343a40")
    cy += 28

cy += 12
text(LX + 24, cy, "Flèches", 17, "#495057")
cy += 30
arrow_legend = [
    (INK, "solid", "appel interne / flux de données in-process"),
    ("#6741d9", "solid", "flux réseau (websocket CertStream)"),
    ("#2f9e44", "dashed", "lecture de fichier (YAML / JSONL / CSV)"),
    ("#868e96", "dotted", "non câblé aujourd'hui / prévu"),
]
for color, style, lbl in arrow_legend:
    arrow((LX + 24, cy + 9), (LX + 130, cy + 9), color=color, style=style, width=2)
    text(LX + 150, cy, lbl, 14, "#343a40")
    cy += 30
text(LX + 24, cy + 8,
     "Badges : \"stub\" = NotImplementedError  |  \"non câblé\" = code présent,", 13, DIM)
text(LX + 24, cy + 26,
     "jamais appelé  |  \"dérive\" = doc ou contrat en désaccord avec le code", 13, DIM)

# ================================================================ ZONE A
ay = zone_title(60, 200, "Zone A - System overview",
                "Vue d'ensemble : qui déclenche quoi, et par où passent les données.")

AW, AG = 520, 52
ax = 460
overview = [
    ("Analyste / opérateur", None,
     ["lance la CLI dans un terminal",
      "aucun compte, aucune authentification, aucun RBAC"], "entry", None),
    ("CLI `vigil` (Typer + menu interactif)", "src/vigil/cli/",
     ["parse les options ou pose les questions",
      "charge watchlist + termes, pilote la boucle asyncio"], "entry", None),
    ("Ingestion - flux de certificats", "src/vigil/ingest/",
     ["websocket CertStream ou replay JSONL",
      "-> CertEvent (SAN bruts, non normalises)"], "ingest", None),
    ("Détection - règles par famille", "src/vigil/detect/",
     ["un verdict par domaine, 2 familles actives sur 6",
      "-> liste de Reason (family, rule, points=0)"], "detect", None),
    ("Reporting & Output", "src/vigil/reporting/ + src/vigil/output/",
     ["métriques live (stderr) / lignes DETECT (stdout)",
      "écriture JSONL de Finding : présente mais non câblée"], "ingest", None),
    ("Terminal de l'analyste", None,
     ["stdout : détections  |  stderr : panneau métriques",
      "aucune base, aucune API, aucun stockage persistant"], "entry", None),
]
a_rects = []
cy = ay
for spec in overview:
    h, r = card(ax, cy, AW, spec)
    a_rects.append(r)
    cy += h + AG
a_bottom = cy - AG

for i in range(len(a_rects) - 1):
    arrow(bottom(a_rects[i]), top(a_rects[i + 1]),
          start=a_rects[i]["id"], end=a_rects[i + 1]["id"])

# external feed column (left)
fx = 60
h1, ct_logs = card(fx, ay + 150, 340,
                   ("Logs Certificate Transparency", None,
                    ["Let's Encrypt, Google, Sectigo,",
                     "IPng Networks, TrustAsia...",
                     "~300 certs/s observes (fichier rate_result)"], "external", "externe"))
h2, cs_srv = card(fx, ay + 150 + h1 + 70, 340,
                  ("certstream-server-rust", "démarré par scripts/start-certstream.sh",
                   ["instance auto-hébergée, ws://127.0.0.1:8080/",
                    "certstream.calidog.io est HS -> non utilisé"], "external", "externe"))
arrow(bottom(ct_logs), top(cs_srv), color="#c2255c", start=ct_logs["id"], end=cs_srv["id"])
arrow((cs_srv["x"] + cs_srv["width"], cs_srv["y"] + 40),
      (a_rects[2]["x"], a_rects[2]["y"] + 40),
      color="#6741d9", label="websocket JSON", label_dx=-58, label_dy=-26)

# config column (right)
gx = 1120
h3, wl_file = card(gx, ay + 330, 380,
                   ("data/watchlist.yml", "généré par scripts/build_watchlist.py",
                    ["~10 000 marques (tiers core + extended)",
                     "noms de marque -> R-01..R-04",
                     "domaines légitimes -> exceptions M-04"], "data", None))
h4, terms_file = card(gx, ay + 330 + h3 + 40, 380,
                      ("data/detection_terms.yml", None,
                       ["vocabulaire L-01 / L-02 / L-04 et R-04",
                        "éditable par un analyste"], "data", None))
arrow((wl_file["x"], wl_file["y"] + 40),
      (a_rects[3]["x"] + a_rects[3]["width"], a_rects[3]["y"] + 34),
      color="#2f9e44", style="dashed", label="lu au démarrage", label_dx=-60, label_dy=-30)
arrow((terms_file["x"], terms_file["y"] + 40),
      (a_rects[3]["x"] + a_rects[3]["width"], a_rects[3]["y"] + 66),
      color="#2f9e44", style="dashed")

zone_a_bottom = max(a_bottom, ay + 330 + h3 + 40 + h4, LY + 486)

# ================================================================ ZONE B
by = zone_title(60, zone_a_bottom + 110, "Zone B - Detailed architecture",
                "Modules réels du dépôt, leurs responsabilités et leurs dépendances. "
                "Monolithe mono-processus organisé en couches : "
                "ingestion -> contrats -> détection -> restitution.")

cur = by

cli_cont, _ = group(
    60, cur, 1560, "Points d'entrée - CLI `vigil`", [
        ("commands.py", "src/vigil/cli/commands.py",
         ["app Typer ; callback sans sous-commande -> menu",
          "`watch` : --source --certstream-url --watchlist",
          "--detection --metrics --skip-wildcards --output"], "entry", None),
        ("menu.py", "src/vigil/cli/menu.py",
         ["prompts questionary : source, familles, règles",
          "lit registry.RULE_FAMILY et IMPLEMENTED_FAMILIES",
          "-> MenuConfig(src, détection, rules, metrics)"], "entry", None),
        ("stream.py", "src/vigil/cli/stream.py",
         ["asyncio.run() sur Source.stream()",
          "filtre wildcards -> detect_event -> affichage",
          "panneau rich.Live des métriques sur stderr"], "entry", None),
        ("defaults.py", "src/vigil/cli/defaults.py",
         ["data/watchlist.yml",
          "tests/fixtures/certs.jsonl"], "entry", None),
    ], cols=4, kind="entry",
    subtitle="entry point console déclaré dans pyproject : vigil = \"vigil.cli:app\"")

scr_cont, _ = group(
    1660, cur, 1000, "Scripts autonomes", [
        ("certstream_kpis.py", "scripts/",
         ["KPI d'ingestion à 1 / 5 / 10 min",
          "certs/s, domaines uniques, repartition par log CT"], "infra", None),
        ("detection_kpis.py", "scripts/",
         ["fenêtre de 5 min sur le flux live",
          "réutilise detect_event + DetectionMetrics",
          "ne charge ni marques ni termes : seules les",
          "règles M-* peuvent matcher"], "infra", None),
        ("build_watchlist.py", "scripts/",
         ["reconstruit data/watchlist.yml hors ligne",
          "seed curé + Tranco top-1M, cap 10 000"], "infra", None),
        ("start-certstream.sh", "scripts/",
         ["démarré certstream-server-rust en local",
          "attend http://localhost:8080/health"], "infra", None),
    ], cols=2, kind="infra",
    subtitle="exécutés à la main, en dehors de la CLI")

cur = max(cli_cont["y"] + cli_cont["height"], scr_cont["y"] + scr_cont["height"]) + 90

ing_cont, _ = group(
    60, cur, 2600, "Ingestion - `vigil.ingest`", [
        ("Source (Protocol)", "ingest/base.py",
         ["async def stream() -> AsyncIterator[CertEvent]",
          "seul contrat expose par la couche",
          "pensé pour être réécrit (Rust) sans toucher detect"], "ingest", None),
        ("CertStreamSource", "ingest/certstream.py",
         ["client websocket + boucle de reconnexion",
          "backoff exponentiel 1 s -> 60 s, idle timeout 45 s",
          "parse_certstream_message() -> CertEvent"], "ingest", None),
        ("FixtureSource", "ingest/fixtures.py",
         ["rejoue un JSONL de messages CertStream bruts",
          "même parseur que la source live (offline / tests)"], "ingest", None),
        ("strip_wildcards", "ingest/filters.py",
         ["retire les SAN `*.` avant détection",
          "certificat ignoré s'il ne reste aucun domaine",
          "les wildcards ne sont pas comptabilisés"], "ingest", None),
    ], cols=4, kind="ingest",
    subtitle="ne connaît ni watchlist, ni marques, ni scoring : "
             "mappe seulement le flux brut vers CertEvent")

arrow(bottom(cli_cont), top(ing_cont), label="instancie une Source et itere stream()",
      start=cli_cont["id"], end=ing_cont["id"], label_dx=16, label_dy=-26)
arrow(bottom(scr_cont), (ing_cont["x"] + ing_cont["width"] - 300, ing_cont["y"]),
      color="#495057",
      waypoints=[(scr_cont["x"] + scr_cont["width"] / 2, cur - 45),
                 (ing_cont["x"] + ing_cont["width"] - 300, cur - 45)],
      label="les scripts KPI réutilisent CertStreamSource", label_dx=-160, label_dy=-26,
      label_color="#495057")

cur += ing_cont["height"] + 100

mod_cont, _ = group(
    60, cur, 2600, "Contrats partages - `vigil.models` + `schemas/`", [
        ("CertEvent", "src/vigil/models.py",
         ["serial, algo, émetteur, validite (UTC validée)",
          "domains = SAN bruts, sans normalisation",
          "source (nom du log CT), cert_index, is_precert"], "model", None),
        ("Reason", "src/vigil/models.py",
         ["(family, rule, points)",
          "identifiants stables : R-01, M-04, ...",
          "points vaut toujours 0 : pas encore de scoring"], "model", None),
        ("DomainVerdict / Finding", "src/vigil/models.py",
         ["Finding = cert + verdicts + score + skipped_domains",
          "modélisés mais jamais construits par le pipeline"], "model", "non câblé"),
        ("finding.v1.json", "schemas/finding.v1.json",
         ["contrat JSON Schema pour consommateurs externes",
          "diverge du modèle Python (matched_watch_target et",
          "reasons à plat vs verdicts[] imbriques)"], "model", "dérive"),
    ], cols=4, kind="model",
    subtitle="les trois couches ne s'accordent que sur ces types : "
             "c'est la frontière qui rend l'ingestion remplaçable")

arrow(bottom(ing_cont), top(mod_cont), label="produit des CertEvent",
      start=ing_cont["id"], end=mod_cont["id"], label_dx=16, label_dy=-26)

cur += mod_cont["height"] + 100

orch_cont, _ = group(
    60, cur, 1220, "Détection - orchestration", [
        ("pipeline.py", "src/vigil/detect/pipeline.py",
         ["detect_event(cert, ...) -> [(domain, [Reason])]",
          "evaluate_domain() : morphologique puis référentiel",
          "IMPLEMENTED_FAMILIES = (MORPHOLOGICAL, REFERENTIAL)",
          "aucun Finding, aucun score agrégé aujourd'hui"], "detect", None),
        ("registry.py", "src/vigil/detect/registry.py",
         ["enums Family (6) et Rule (18)",
          "RULE_FAMILY : règle -> famille",
          "les ids sont le contrat stable des findings"], "detect", None),
    ], cols=2, kind="detect",
    subtitle="synchrone et pur : aucune I/O dans la détection")

rep_cont, _ = group(
    1440, cur, 1220, "Reporting & Output", [
        ("DetectionMetrics", "src/vigil/reporting/metrics.py",
         ["certs, domaines, détections, temps d'analyse",
          "min/max par cert, compteur par règle, débit glissant",
          "snapshot() -> panneau rich.Live sur stderr"], "ingest", None),
        ("JSONLWriter", "src/vigil/output/jsonl.py",
         ["sérialise un Finding par ligne (stdout ou fichier)",
          "importé nulle part : --output est accepté mais ignoré"], "ingest", "non câblé"),
    ], cols=2, kind="ingest",
    subtitle="observabilité de la boucle ; pas de log structuré ni d'export")

arrow(bottom(mod_cont), top(orch_cont), label="detect_event(cert)", label_dx=16, label_dy=-26,
      waypoints=[(mod_cont["x"] + mod_cont["width"] / 2, cur - 50),
                 (orch_cont["x"] + orch_cont["width"] / 2, cur - 50)])
arrow(right(orch_cont), left(rep_cont), label="Reason par règle\n+ durées",
      start=orch_cont["id"], end=rep_cont["id"], label_dx=-57, label_dy=-42)

cur += max(orch_cont["height"], rep_cont["height"]) + 100

fam_cont, _ = group(
    60, cur, 2600, "Détection - familles (`detect/families/`)", [
        ("morphological.py", "M-01 -> M-04",
         ["M-01 >= 3 tirets  |  M-02 registrable > 40 car.",
          "M-03 >= 4 labels  |  M-04 >= 3 chiffres consecutifs",
          "exceptions chiffrees issues des domaines légitimes"], "detect", "actif"),
        ("referential.py", "R-01 -> R-04",
         ["R-01 marque hors du domaine enregistrable",
          "R-02 marque + token type TLD  |  R-04 marque + terme d'auth",
          "R-03 Levenshtein <= 2 (match exact exclu)"], "detect", "actif"),
        ("lexical.py", "L-01 -> L-04",
         ["vocabulaire MFA / documents / www / urgence",
          "termes déjà présents en YAML, evaluateur absent"], "detect", "stub"),
        ("encoding.py", "E-01 -> E-02",
         ["E-01 scripts Unicode mélangés dans un label",
          "E-02 label punycode (xn--)"], "detect", "stub"),
        ("statistical.py", "S-01 -> S-03",
         ["entropie, mot + bruit, TLD sur-représenté",
          "nécessite une baseline de corpus observe"], "detect", "stub"),
        ("certificate.py", "C-01",
         ["nombre de SAN > 200 (seuil déjà defini)",
          "contexte plutot que détection"], "detect", "stub"),
    ], cols=3, kind="detect",
    subtitle="une règle au maximum par famille et par domaine : première correspondance "
             "gagnante, par spécificité décroissante. docs/detections_rules.md est la "
             "spécification de référence.")

arrow(bottom(orch_cont), (fam_cont["x"] + 400, fam_cont["y"]),
      label="evaluate_domain() : 2 familles appelées sur 6", label_dx=-120, label_dy=-28,
      waypoints=[(orch_cont["x"] + orch_cont["width"] / 2, cur - 50),
                 (fam_cont["x"] + 400, cur - 50)])

cur += fam_cont["height"] + 100

tech_cont, _ = group(
    60, cur, 1500, "Détection - primitives (`detect/techniques/`)", [
        ("names.py", "parse_domain()",
         ["découpage PSL via tldextract",
          "snapshot hors ligne : aucun appel réseau",
          "-> fqdn / registrable / suffix / subdomain / labels"], "detect", "actif"),
        ("levenshtein.py", "bounded_levenshtein()",
         ["distance d'edition bornée, sortie anticipée",
          "utilisée par R-03"], "detect", "actif"),
        ("permutations.py", "generate_permutations()",
         ["génération de variantes typosquattees"], "detect", "stub"),
        ("homoglyphs.py", "is_homoglyph_match()",
         ["confusables Unicode / bitsquatting"], "detect", "stub"),
    ], cols=2, kind="detect",
    subtitle="fonctions pures sur des chaînes, sans dépendance à vigil.models")

din_cont, _ = group(
    1600, cur, 1060, "Détection - entrées (`detect/data/`)", [
        ("watchlist.py", None,
         ["load_brand_names() -> frozenset (R-01..R-04)",
          "load_legitimate_domains() -> exceptions M-04",
          "renvoie vide si le fichier est absent"], "detect", None),
        ("terms.py", None,
         ["load_terms() -> {Rule: frozenset}",
          "YAML valide par pydantic (DetectionTerms)"], "detect", None),
        ("thresholds.py", None,
         ["3 tirets | 40 caractères | 4 labels | 3 chiffres",
          "Levenshtein <= 2 | SAN > 200 | TLD_LIKE_TOKENS"], "detect", None),
    ], cols=1, kind="detect",
    subtitle="tunables et chargeurs, isolés du code de règles")

arrow(bottom(fam_cont), top(tech_cont), label="parse_domain() / bounded_levenshtein()",
      label_dx=16, label_dy=-28,
      waypoints=[(fam_cont["x"] + 400, cur - 50),
                 (tech_cont["x"] + tech_cont["width"] / 2, cur - 50)])
arrow(top(din_cont), (fam_cont["x"] + fam_cont["width"] - 300, fam_cont["y"] + fam_cont["height"]),
      label="marques surveillees, termes, seuils", label_dx=-130, label_dy=-50,
      waypoints=[(din_cont["x"] + din_cont["width"] / 2, cur - 50),
                 (fam_cont["x"] + fam_cont["width"] - 300, cur - 50)])

cur += max(tech_cont["height"], din_cont["height"]) + 100

dat_cont, _ = group(
    60, cur, 2600, "Données & configuration (fichiers du dépôt)", [
        ("data/watchlist.yml", "50 858 lignes, généré",
         ["name / sector / region / tier / legitimate_domains",
          "tiers core (threat-intel) et extended (Tranco)"], "data", None),
        ("data/brands_core.seed.yml", "écrit à la main",
         ["secteur -> region -> marque -> domaines",
          "sources : Check Point, APWG, Cofense..."], "data", None),
        ("data/detection_terms.yml", "éditable analyste",
         ["clés l-01, l-02, l-04, r-04"], "data", None),
        ("tests/fixtures/certs.jsonl", "replay offline",
         ["5 messages CertStream bruts",
          "wildcard et IDN inclus"], "data", None),
        ("data/state/tranco_top1m.csv", "gitignoré",
         ["cache de téléchargement Tranco",
          "utilisé seulement au build de la watchlist"], "data", None),
    ], cols=5, kind="data",
    subtitle="aucune base de données, aucun cache, aucun stockage objet : "
             "tout l'état persistant est un fichier du dépôt")

arrow((din_cont["x"] + din_cont["width"] / 2, dat_cont["y"]),
      (din_cont["x"] + din_cont["width"] / 2, din_cont["y"] + din_cont["height"]),
      color="#2f9e44", style="dashed",
      label="YAML lu au démarrage du run", label_dx=16, label_dy=-30)

zone_b_bottom = dat_cont["y"] + dat_cont["height"]

# ================================================================ ZONE C
cy0 = zone_title(60, zone_b_bottom + 110, "Zone C - Main workflows",
                 "Parcours d'exécution réels. Tout est synchrone dans un unique "
                 "event loop asyncio : "
                 "pas de queue, pas de worker, pas de webhook, pas de job planifié.")

FW, FGAP = 620, 40


def flow(x, y, title, subtitle, steps, kind):
    st, _ = PAL[kind]
    text(x, y, title, 21, st)
    for i, ln in enumerate(wrap(subtitle, 13, FW)):
        text(x, y + 28 + i * 17, ln, 13, DIM)
    yy = y + 28 + len(wrap(subtitle, 13, FW)) * 17 + 14
    prev = None
    for i, (label, note) in enumerate(steps, start=1):
        lines = wrap(f"{i}. {label}", BS, FW - 2 * PAD)
        nlines = wrap(note, 12.5, FW - 2 * PAD) if note else []
        h = (2 * PAD - 6) + len(lines) * BS * 1.25
        if nlines:
            h += 3 + len(nlines) * 12.5 * 1.25
        r = rect(x, yy, FW, h, kind)
        text(x + PAD, yy + PAD - 4, "\n".join(lines), BS, "#212529")
        if nlines:
            text(x + PAD, yy + PAD - 4 + len(lines) * BS * 1.25 + 3, "\n".join(nlines), 12.5, DIM)
        if prev is not None:
            arrow(bottom(prev), (x + FW / 2, yy), color=st, width=2,
                  start=prev["id"], end=r["id"])
        prev = r
        yy += h + 26
    return yy


f1 = flow(60, cy0, "W1 - Run de détection live",
          "vigil watch --source certstream --detection --metrics", [
    ("commands.watch() lit les options Typer",
     "source, URL, watchlist, sortie, intervalle de métriques"),
    ("Construction de la Source",
     "CertStreamSource(url) ou FixtureSource(path)"),
    ("Chargement des entrées de détection",
     "marques surveillees, exceptions chiffrees, termes lexicaux (YAML)"),
    ("stream._run_stream() -> asyncio.run()",
     "un seul event loop, aucun thread, aucun worker"),
    ("Connexion websocket et reception",
     "idle timeout 45 s, reconnexion avec backoff 1 -> 60 s"),
    ("parse_certstream_message() -> CertEvent",
     "les messages qui ne sont pas certificate_update sont ignorés"),
    ("strip_wildcards() retire les SAN *.",
     "le certificat est sauté s'il ne reste aucun domaine"),
    ("detect_event() : boucle sur chaque SAN",
     "parse_domain() puis familles actives - detail en W3"),
    ("Resultat : [(domaine, [Reason])]",
     "liste vide = aucune sortie pour ce certificat"),
    ("Sortie : métriques ou lignes DETECT",
     "--metrics agrège et masque les lignes individuelles"),
    ("Snapshot toutes les --metrics-interval s",
     "panneau rich.Live sur stderr, reprint simple si non-TTY"),
    ("Fin de flux ou Ctrl-C",
     "snapshot final puis 'done: N detection(s)' sur stderr"),
], "ingest")

f2 = flow(60 + (FW + FGAP), cy0, "W2 - Run interactif (menu)",
          "vigil, sans sous-commande", [
    ("Callback Typer : aucune sous-commande invoquee",
     "logging configuré en INFO"),
    ("_prompt_menu() : choix de la source",
     "certstream (URL) ou fixtures (chemin)"),
    ("Activer la détection ?",
     "si non, les certificats sont simplement affiches"),
    ("Choix des familles puis des règles",
     "seules les familles implémentées sont proposees"),
    ("Métriques uniquement ? (oui par defaut)",
     "masque les détections individuelles"),
    ("_print_recap() : panneau de configuration",
     "source, règles activées, métriques"),
    ("Chargement watchlist + termes si détection",
     "avertissement si data/watchlist.yml est absent"),
    ("_run_stream(...) - même boucle que W1",
     "les wildcards sont toujours filtres dans ce mode"),
], "entry")

f3 = flow(60 + 2 * (FW + FGAP), cy0, "W3 - Évaluation d'un domaine",
          "chemin synchrone et pur, exécuté pour chaque SAN", [
    ("parse_domain(domain)",
     "minuscules, point final retiré, découpage PSL hors ligne"),
    ("Famille morphologique, dans l'ordre",
     "M-01 -> M-02 -> M-03 -> M-04"),
    ("M-04 ignore les suites de chiffres légitimes",
     "dérivées des domaines de la watchlist (ex. 365)"),
    ("Premiere règle vraie -> un Reason, stop famille",
     "points=0 : aucune pondération pour l'instant"),
    ("Famille référentielle, dans l'ordre",
     "R-01 -> R-02 -> R-03 -> R-04"),
    ("Tokenisation du cœur enregistrable sur [.-]",
     "R-01 compare sous-domaine et cœur enregistrable"),
    ("R-03 : Levenshtein borne contre chaque marque",
     "pré-filtre sur la difference de longueur, match exact exclu"),
    ("Au plus 2 Reason par domaine (1 par famille)",
     "familles lexicale / encodage / statistique / certificat non appelées"),
    ("Domaine retenu s'il reste au moins un Reason",
     "remonté au pipeline puis aux métriques ou à stdout"),
], "detect")

f4 = flow(60 + 3 * (FW + FGAP), cy0, "W4 - Reconstruction de la watchlist",
          "python scripts/build_watchlist.py - hors ligne, manuel", [
    ("load_core() lit brands_core.seed.yml",
     "secteur -> region -> marque ; doublon = échec du build"),
    ("ensure_tranco() : cache ou téléchargement",
     "https://tranco-list.eu/top-1m.csv.zip -> data/state/"),
    ("Parcours de Tranco par rang",
     "budget = 10 000 - taille du core"),
    ("Filtres d'exclusion",
     "denylist CDN, label < 3 car., tokens negatifs et étrangers"),
    ("region_of(TLD) : us / eu / global",
     "les autres ccTLD sont écartés"),
    ("classify_sector(label)",
     "banking | health | insurance | it_services"),
    ("Déduplication",
     "par domaine enregistrable et par nom de marque"),
    ("Écriture de data/watchlist.yml",
     "en-tête + dump YAML, puis récapitulatif par secteur"),
], "data")

zone_c_bottom = max(f1, f2, f3, f4)

# ================================================================ ZONE D
dy = zone_title(60, zone_c_bottom + 90, "Zone D - External dependencies",
                "Tout ce qui vit en dehors du dépôt. Aucun SaaS, aucun fournisseur cloud, "
                "aucun service "
                "de paiement, d'e-mail, d'analytics, de CDN ni d'authentification.")

ext_cont, _ = group(60, dy, 2600, "Systèmes externes", [
    ("Logs Certificate Transparency", "runtime, indirect",
     ["Let's Encrypt, Google, Sectigo, IPng, TrustAsia",
      "atteints uniquement via le serveur CertStream"], "external", None),
    ("certstream-server-rust", "runtime, direct",
     ["websocket ws://127.0.0.1:8080/ par defaut",
      "endpoint /health utilisé par le script de démarrage",
      "hors dépôt : à construire et lancer séparément"], "external", None),
    ("tranco-list.eu", "build-time uniquement",
     ["HTTPS, top-1m.csv.zip, urllib standard",
      "mis en cache dans data/state/, jamais au runtime"], "external", None),
    ("Public Suffix List (tldextract)", "embarquée",
     ["snapshot du paquet, suffix_list_urls=()",
      "aucune requête réseau pendant la détection"], "external", None),
], cols=4, kind="external")

dep_cont, _ = group(60, ext_cont["y"] + ext_cont["height"] + 50, 2600,
                    "Dépendances Python", [
    ("Runtime", "pyproject [project.dependencies]",
     ["pydantic >= 2.7 - modèles et validation",
      "websockets >= 12 - client CertStream",
      "typer / questionary / rich - CLI, menu, affichage",
      "pyyaml - watchlist et termes  |  tldextract - PSL"], "infra", None),
    ("Développement", "extra dev",
     ["pytest >= 8 et pytest-asyncio (asyncio_mode strict)",
      "ruff >= 0.5 - lint E,F,I,UP,B, ligne 100"], "infra", None),
    ("Build", "hatchling",
     ["paquet src/vigil",
      "script console `vigil`"], "infra", None),
], cols=3, kind="infra")

zone_d_bottom = dep_cont["y"] + dep_cont["height"]

# ================================================================ ZONE E
ey = zone_title(60, zone_d_bottom + 90, "Zone E - Infrastructure / runtime",
                "Ce que le dépôt permet réellement de déduire. Pas de Dockerfile, "
                "pas de docker-compose, "
                "pas de manifeste Kubernetes, pas d'IaC, pas de pipeline CI (.github absent).")

inf_cont, _ = group(60, ey, 2600, "Exécution locale", [
    ("Processus 1 - certstream-server-rust", "externe, port 8080",
     ["lancé via scripts/start-certstream.sh (nohup + disown)",
      "binaire attendu dans ~/Projet/certstream-server-rust",
      "santé vérifiée sur http://localhost:8080/health"], "external", None),
    ("Processus 2 - CLI vigil", "python, mono-processus",
     ["un seul event loop asyncio, pas de parallélisme",
      "état en mémoire uniquement, rien n'est persisté",
      "arrêt sur Ctrl-C, KeyboardInterrupt absorbé"], "entry", None),
    ("Système de fichiers", "seul état durable",
     ["data/watchlist.yml et data/detection_terms.yml en lecture",
      "data/state/ en cache (gitignoré)",
      "--output accepté mais aucun fichier n'est écrit"], "data", None),
], cols=3, kind="infra")

gap_cont, _ = group(60, inf_cont["y"] + inf_cont["height"] + 50, 2600,
                    "Écarts constates entre le code, la documentation et les contrats", [
    ("detect/scoring.py documenté mais absent", "docs/architecture.md, detect/__init__.py",
     ["le module de scoring n'existe pas dans src/",
      "aucun score n'est calculé : Reason.points reste à 0"], "infra", "dérive doc"),
    ("La chaîne Finding n'est pas branchée", "models.py, output/jsonl.py",
     ["detect_event renvoie des tuples, pas des Finding",
      "JSONLWriter n'est importé nulle part",
      "docs/scoring.md est vide"], "infra", "non câblé"),
    ("skipped_domains n'est jamais rempli", "ingest/filters.py vs models.Finding",
     ["les wildcards sont retirés dès l'ingestion",
      "la spec demande de les compter et de les lister"], "infra", "à confirmer"),
    ("finding.v1.json diverge de models.Finding", "schemas/finding.v1.json",
     ["schéma : matched_watch_target + reasons à plat",
      "modèle : verdicts[] + skipped_domains"], "infra", "dérive"),
    ("docs/adr/0001-python-first.md référencé", "docs/architecture.md",
     ["le dossier docs/adr/ n'existe pas dans le dépôt"], "infra", "dérive doc"),
    ("Couverture de tests", "tests/ (9 fichiers)",
     ["ingest, filtres, pipeline, morphologique, référentiel,",
      "registre, métriques, CLI, watchlist",
      "aucun test sur vigil.output"], "infra", None),
], cols=3, kind="infra")

# ---------------------------------------------------------------- write
doc = {
    "type": "excalidraw",
    "version": 2,
    "source": "https://claude.ai/code",
    "elements": els,
    "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
    "files": {},
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")

# ---------------------------------------------------------------- checks
rects = [e for e in els if e["type"] == "rectangle" and e["backgroundColor"] != "transparent"]
overlaps = 0
for i, a in enumerate(rects):
    for b in rects[i + 1:]:
        inter = (a["x"] < b["x"] + b["width"] and b["x"] < a["x"] + a["width"]
                 and a["y"] < b["y"] + b["height"] and b["y"] < a["y"] + a["height"])
        contains = ((a["x"] <= b["x"] and a["y"] <= b["y"]
                     and a["x"] + a["width"] >= b["x"] + b["width"]
                     and a["y"] + a["height"] >= b["y"] + b["height"])
                    or (b["x"] <= a["x"] and b["y"] <= a["y"]
                        and b["x"] + b["width"] >= a["x"] + a["width"]
                        and b["y"] + b["height"] >= a["y"] + a["height"]))
        if inter and not contains:
            overlaps += 1
            if overlaps <= 12:
                print(f"OVERLAP: ({a['x']},{a['y']},{a['width']}x{a['height']}) "
                      f"vs ({b['x']},{b['y']},{b['width']}x{b['height']})")

texts = [e for e in els if e["type"] == "text"]
overflow = 0
for t in texts:
    for r in rects:
        if (r["x"] <= t["x"] <= r["x"] + r["width"]
                and r["y"] <= t["y"] <= r["y"] + r["height"]):
            if t["x"] + t["width"] > r["x"] + r["width"] - 4:
                overflow += 1
                if overflow <= 12:
                    print(f"TEXT OVERFLOW: {t['text'][:70]!r} in rect "
                          f"({r['x']},{r['y']},{r['width']})")
            if t["y"] + t["height"] > r["y"] + r["height"] - 2:
                overflow += 1
                if overflow <= 12:
                    print(f"TEXT VOVERFLOW: {t['text'][:70]!r} in rect "
                          f"({r['x']},{r['y']},{r['width']}x{r['height']})")
            break

print(f"elements={len(els)} filled_rects={len(rects)} texts={len(texts)}")
print(f"canvas x:[{min(e['x'] for e in els):.0f},{max(e['x'] + e['width'] for e in els):.0f}] "
      f"y:[{min(e['y'] for e in els):.0f},{max(e['y'] + e['height'] for e in els):.0f}]")
print(f"overlaps={overlaps} text_overflows={overflow}")
