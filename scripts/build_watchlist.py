#!/usr/bin/env python3
"""Regenerate data/watchlist.yml from the curated core plus a Tranco extension."""

from __future__ import annotations

import csv
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SEED_PATH = ROOT / "data" / "brands_core.seed.yml"
OUTPUT_PATH = ROOT / "data" / "watchlist.yml"
TRANCO_CACHE = ROOT / "data" / "state" / "tranco_top1m.csv"
TRANCO_URL = "https://tranco-list.eu/top-1m.csv.zip"

MAX_ENTRIES = 10_000
MIN_LABEL_LEN = 3

SECTORS = ("banking", "health", "insurance", "it_services")
REGIONS = ("us", "eu", "global")

# two-label public suffixes, EU/US subset
MULTI_SUFFIXES = {
    "co.uk", "org.uk", "gov.uk", "ac.uk", "me.uk", "ltd.uk", "plc.uk", "net.uk", "sch.uk",
}

EU_TLDS = {
    "uk", "eu", "fr", "de", "es", "it", "nl", "be", "lu", "ie", "pt", "at", "ch",
    "se", "no", "dk", "fi", "pl", "cz", "sk", "hu", "ro", "bg", "gr", "hr", "si",
    "ee", "lv", "lt", "cy", "mt", "is", "li",
}
GLOBAL_GTLDS = {
    "com", "net", "org", "io", "co", "app", "dev", "cloud", "ai", "info", "biz",
    "online", "site", "tech", "xyz", "me", "tv", "live", "shop", "store", "cc", "pro",
}

# infrastructure / CDN, never a brand target
DENYLIST = {
    "cloudfront.net", "cloudflare.com", "googleusercontent.com", "gstatic.com",
    "akamaihd.net", "akamai.net", "fastly.net", "amazonaws.com", "windows.net",
    "cloudflare.net", "cloudflare-dns.com", "cloudflareinsights.com",
    "root-servers.net", "gtld-servers.net", "registrar-servers.com",
    "paypalobjects.com",
}

# content / aggregator / infra words, skip the label
NEGATIVE_TOKENS = (
    "news", "media", "journal", "magazine", "mag", "blog", "wiki", "forum",
    "tips", "guide", "review", "ratings", "bazaar", "compare", "advisor",
    "expert", "xpress", "server", "dns", "cdn", "static", "objects", "insights",
    "registrar", "gtld", "root", "line", "today",
)

# non-EU/US brands leaking via generic gTLDs
FOREIGN_TOKENS = (
    "huawei", "tencent", "qcloud", "yandex", "baidu", "alibaba", "aliyun",
    "xiaomi", "samsung", "sberbank", "naver", "kakao", "rakuten", "weibo",
    "gosuslugi", "icici", "hdfc", "denizbank", "sbi", "shia", "venezuela",
)


def split_domain(domain: str) -> tuple[str, str, str]:
    """Return (label, registrable_domain, region_tld) for a domain."""
    parts = domain.split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in MULTI_SUFFIXES:
        return parts[-3], ".".join(parts[-3:]), parts[-1]
    if len(parts) >= 2:
        return parts[-2], ".".join(parts[-2:]), parts[-1]
    return domain, domain, ""


def region_of(region_tld: str) -> str | None:
    """Return 'us'/'eu'/'global', or None if outside EU/US scope."""
    if region_tld == "us":
        return "us"
    if region_tld in EU_TLDS:
        return "eu"
    if region_tld in GLOBAL_GTLDS:
        return "global"
    return None


# per sector: substring / prefix / suffix tokens matched on the brand label
SECTOR_TOKENS: dict[str, dict[str, tuple[str, ...]]] = {
    "banking": {
        "contains": ("sparkasse", "volksbank", "raiffeisen", "bancorp", "finanz",
                     "fintech", "neobank", "paypal"),
        "prefix": ("bank", "banque", "banco", "banca", "banka", "kredit", "bancaire"),
        "suffix": ("bank",),
    },
    "insurance": {
        "contains": ("insurance", "versicherung", "assicura", "verzekering",
                     "forsikring", "assurance"),
        "prefix": ("insur", "assur", "seguro", "mutuelle"),
        "suffix": ("insurance", "versicherung", "mutual", "seguros"),
    },
    "health": {
        "contains": ("healthcare", "medicare", "medicaid", "pharma", "pharmacy",
                     "pharmacie", "farmacia", "apotheke", "hospital", "krankenkasse",
                     "gesundheit", "medical", "clinic"),
        "prefix": ("klinik", "salud"),
        "suffix": (),
    },
    "it_services": {
        # precise tokens only; generic 'cloud'/'saas' pulled in CDN/infra
        "contains": ("hosting", "webhost", "datacenter", "hebergement", "antivirus",
                     "cybersecurity"),
        "prefix": ("hostinger",),
        "suffix": ("hosting",),
    },
}


def _seg_match(label: str, token: str) -> bool:
    return f"-{token}" in label or f"{token}-" in label


def classify_sector(label: str) -> str | None:
    """Return the sector for a brand label, or None if not classifiable."""
    for sector in SECTORS:
        toks = SECTOR_TOKENS[sector]
        if any(t in label for t in toks["contains"]):
            return sector
        if any(label == t or label.startswith(t) or _seg_match(label, t) for t in toks["prefix"]):
            return sector
        if any(label == t or label.endswith(t) or _seg_match(label, t) for t in toks["suffix"]):
            return sector
    return None


def load_core() -> tuple[list[dict], set[str], set[str]]:
    """Load the curated seed -> (entries, claimed_registrables, used_names)."""
    seed = yaml.safe_load(SEED_PATH.read_text(encoding="utf-8"))
    entries: list[dict] = []
    claimed_reg: set[str] = set()
    used_names: set[str] = set()
    for sector in SECTORS:
        by_region = seed.get(sector) or {}
        for region in REGIONS:
            brands = by_region.get(region) or {}
            for name, domains in brands.items():
                name = name.strip().lower()
                if name in used_names:
                    raise SystemExit(f"duplicate brand name in seed: {name!r}")
                used_names.add(name)
                norm = [d.strip().lower() for d in domains]
                for d in norm:
                    claimed_reg.add(split_domain(d)[1])
                entries.append({
                    "name": name,
                    "sector": sector,
                    "region": region,
                    "tier": "core",
                    "legitimate_domains": norm,
                })
    return entries, claimed_reg, used_names


def ensure_tranco() -> Path:
    """Return the cached Tranco CSV, downloading it once if missing."""
    if TRANCO_CACHE.exists():
        return TRANCO_CACHE
    TRANCO_CACHE.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading {TRANCO_URL} ...", file=sys.stderr)
    with urllib.request.urlopen(TRANCO_URL, timeout=180) as resp:
        blob = resp.read()
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        member = zf.namelist()[0]
        TRANCO_CACHE.write_bytes(zf.read(member))
    return TRANCO_CACHE


def iter_tranco(path: Path):
    """Yield domains from the Tranco CSV in rank order."""
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.reader(fh):
            if len(row) >= 2:
                yield row[1].strip().lower()


def build_extension(claimed_reg: set[str], used_names: set[str], budget: int) -> list[dict]:
    """Walk Tranco by rank and build up to `budget` extended entries."""
    entries: list[dict] = []
    for domain in iter_tranco(ensure_tranco()):
        if len(entries) >= budget:
            break
        if not domain or domain in DENYLIST:
            continue
        label, registrable, region_tld = split_domain(domain)
        if len(label) < MIN_LABEL_LEN or registrable in claimed_reg:
            continue
        if any(t in label for t in NEGATIVE_TOKENS) or any(t in label for t in FOREIGN_TOKENS):
            continue
        region = region_of(region_tld)
        if region is None:
            continue
        sector = classify_sector(label)
        if sector is None:
            continue
        name = label
        if name in used_names:
            name = registrable.replace(".", "-")
            if name in used_names:
                continue
        used_names.add(name)
        claimed_reg.add(registrable)
        entries.append({
            "name": name,
            "sector": sector,
            "region": region,
            "tier": "extended",
            "legitimate_domains": [domain],
        })
    return entries


# written verbatim as the output file header
HEADER = """\
# Vigil watchlist — brands monitored for impersonation detection.
#
# GENERATED by scripts/build_watchlist.py — do not edit by hand.
# Curated source: data/brands_core.seed.yml (tier: core).
# Extension: Tranco top-1M filtered by sector/region (tier: extended).
#
# sector: banking | health | insurance | it_services
# region: us | eu | global
# tier: core (threat-intel) | extended (Tranco coverage)
"""


def write_watchlist(entries: list[dict]) -> None:
    """Write entries to data/watchlist.yml with the header."""
    body = yaml.safe_dump(
        {"brands": entries},
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=120,
    )
    OUTPUT_PATH.write_text(HEADER + body, encoding="utf-8")


def main() -> None:
    core, claimed_reg, used_names = load_core()
    budget = MAX_ENTRIES - len(core)
    if budget < 0:
        raise SystemExit(f"core already exceeds the cap ({len(core)} > {MAX_ENTRIES})")
    extension = build_extension(claimed_reg, used_names, budget)
    entries = core + extension
    if len(entries) > MAX_ENTRIES:
        raise SystemExit(f"total {len(entries)} > cap {MAX_ENTRIES}")
    write_watchlist(entries)

    per_sector: dict[str, int] = dict.fromkeys(SECTORS, 0)
    for e in entries:
        per_sector[e["sector"]] += 1
    print(f"wrote {OUTPUT_PATH.relative_to(ROOT)}: {len(entries)} brands "
          f"({len(core)} core + {len(extension)} extended, cap {MAX_ENTRIES})")
    for sector in SECTORS:
        print(f"  {sector:12s} {per_sector[sector]}")


if __name__ == "__main__":
    main()
