"""Shared PSL name decomposition, used by every detection family."""

from dataclasses import dataclass

import tldextract

# offline: use the bundled PSL snapshot, never hit the network at runtime
# include_psl_private_domains: treat PaaS suffixes (pages.dev, workers.dev, ...) as
# suffixes too, otherwise their platform label is misparsed as the registrable domain
_EXTRACT = tldextract.TLDExtract(suffix_list_urls=(), include_psl_private_domains=True)


@dataclass(frozen=True)
class DomainName:
    fqdn: str
    registrable: str
    suffix: str
    subdomain: str
    labels: tuple[str, ...]


def parse_domain(domain: str) -> DomainName:
    """Split a domain into its PSL parts."""
    fqdn = domain.strip().rstrip(".").lower()
    ext = _EXTRACT(fqdn)
    return DomainName(
        fqdn=fqdn,
        registrable=ext.top_domain_under_public_suffix,
        suffix=ext.suffix,
        subdomain=ext.subdomain,
        labels=tuple(fqdn.split(".")) if fqdn else (),
    )
