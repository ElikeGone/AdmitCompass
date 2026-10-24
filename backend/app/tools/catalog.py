"""Program catalog = verified evidence store (authoritative) + discovery index (needs verification).

Deterministic merge, deduplication, search, filtering, and grounded sorting. Read-only.
Discovered records are NEVER passed to the agents; the agents only use EvidenceStore.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from ..schemas.discovery import DiscoveredProgram, DiscoveryIndex, registrable_domain
from .evidence_store import DATA_DIR, EvidenceStore

DISCOVERY_FILE = DATA_DIR / "discovery" / "discovered_programs.json"
LINK_STATUS_FILE = DATA_DIR / "links" / "link_status.json"
PARTIAL_STEM = re.compile(r"\b(only|track|tracks|path|paths|major|option|concentration|dual degree)\b", re.I)
CORE_GROUPS = {"cost": ("tuition", "cost_of_attendance"), "stem": ("stem_designation",), "tests": ("test_policy",),
               "outcomes": ("employment_rate", "median_base_salary")}
STATUS_LABEL = {"detailed": "Detailed evidence", "partial": "Partially verified", "discovered": "Discovered",
                "unavailable": "Retrieval unavailable"}


def stem_is_partial(scope: str) -> bool:
    """True when the source designates only some tracks/majors, not the whole degree."""
    return bool(PARTIAL_STEM.search(scope)) and not re.search(r"\b(entire|all)\b", scope, re.I)


def evidence_status(verified: set[str]) -> str:
    """Detailed = every core group (cost, STEM, tests, outcomes) supported and >= 8 verified facts; else partial."""
    core_ok = all(any(f in verified for f in fs) for fs in CORE_GROUPS.values())
    return "detailed" if core_ok and len(verified) >= 8 else "partial"


def load_link_status(path: Path = LINK_STATUS_FILE) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
_STOP = {"the", "of", "university", "school", "business", "college", "graduate", "management", "and", "at", "in"}


def norm_key(university: str) -> str:
    words = re.sub(r"[^a-z0-9 ]", " ", university.lower()).split()
    return " ".join(w for w in words if w not in _STOP)


@dataclass
class MergeReport:
    duplicates_of_verified: list[dict]
    duplicates_within_discovery: list[dict]


def load_discovery(path: Path = DISCOVERY_FILE) -> DiscoveryIndex | None:
    if not path.exists():
        return None
    return DiscoveryIndex.model_validate(json.loads(path.read_text(encoding="utf-8")))


class Catalog:
    def __init__(self, store: EvidenceStore, discovery: DiscoveryIndex | None, link_status: dict | None = None):
        self.store, self.discovery = store, discovery
        self.links = load_link_status() if link_status is None else link_status
        self.items: list[dict] = []
        self.merge = MergeReport([], [])
        self._build()

    # ----- merge -----
    def _verified_items(self) -> list[dict]:
        out = []
        for p in self.store.dataset.programs:
            f = lambda n: self.store.get_fact(p.program_id, n)  # noqa: E731
            loc, coa, stem, tui = f("location"), f("cost_of_attendance"), f("stem_designation"), f("tuition")
            emp, spon = f("employment_rate"), f("sponsorship")
            verified = {n for n, fl in p.facts.items() if fl.status.value == "verified"}
            req_src = next((self.store.get_evidence(i)["source_url"] for n in ("application_requirements", "test_policy", "location")
                            for i in p.facts[n].evidence_ids), None)
            # Career keywords come ONLY from industries/functions the school itself reports in its employment data.
            kw = []
            for name in ("industry_breakdown", "function_breakdown"):
                fb = f(name)
                if fb.status == "verified":
                    kw += [{"keyword": k, "source_fact": name, "period": fb.period} for k in fb.value]
            domains = {registrable_domain(str(self.store.get_source(e.source_id).url)) for e in p.evidence}
            out.append({
                "id": p.program_id, "tier": "verified", "status": "verified_evidence",
                "university": p.university, "school": p.school, "program_name": p.program_name, "degree_type": p.degree,
                "city": loc.value["city"] if loc.status == "verified" else None,
                "state": loc.value["state"] if loc.status == "verified" else None,
                "cost_of_attendance": {"value": coa.value, "period": coa.period, "evidence_ids": [e["evidence_id"] for e in coa.evidence]} if coa.status == "verified" else None,
                "tuition": {"value": tui.value, "period": tui.period} if tui.status == "verified" else None,
                "stem_designated": stem.value["designated"] if stem.status == "verified" else None,
                "stem_scope": stem.value["scope"] if stem.status == "verified" else None,
                "stem_partial": stem.status == "verified" and stem_is_partial(stem.value["scope"]),
                "evidence_status": evidence_status(verified - ({"stem_designation"} if stem.status == "verified" and stem_is_partial(stem.value["scope"]) else set())), "collection_tier": p.collection_tier,
                "verified_facts": sorted(verified),
                "checked_unknown": sorted(n for n, fl in p.facts.items() if fl.status.value != "verified" and fl.checked),
                "not_checked": sorted(n for n, fl in p.facts.items() if fl.status.value != "verified" and not fl.checked),
                "official_url": req_src,
                "employment": {"rate": emp.value, "period": emp.period, "definition": emp.definition} if emp.status == "verified" else None,
                "sponsorship_evidence": "employer_specific" if spon.status == "verified" else "unknown",
                "career_keywords": kw,
                "verified_fields": sum(1 for fl in p.facts.values() if fl.status.value == "verified"),
                "total_fields": len(p.facts), "provenance_url": None, "domains": sorted(domains),
                "_key": norm_key(p.university),
            })
        return out

    def _discovered_item(self, d: DiscoveredProgram) -> dict:
        return {
            "id": d.discovery_id, "tier": "discovered", "status": d.verification_status,
            "university": d.university, "school": d.school, "program_name": d.program_name, "degree_type": d.degree_type,
            "format": d.format, "city": d.city, "state": d.state, "location_basis": d.location_basis,
            "cost_of_attendance": None, "tuition": None, "stem_designated": None,  # never filled from discovery
            "employment": None, "sponsorship_evidence": "unknown", "career_keywords": [],
            "provenance_url": str(d.provenance_url), "page_title": d.page_title, "excerpt": d.excerpt,
            "official_url": str(d.provenance_url), "evidence_status": "discovered",
            "verified_facts": [], "checked_unknown": [], "not_checked": [],
            "discovered_on": d.discovered_on.isoformat(), "fetched": d.fetched, "notes": d.notes,
            "domains": [d.domain], "_key": norm_key(d.university),
        }

    def _build(self) -> None:
        verified = self._verified_items()
        v_keys = {v["_key"]: v["id"] for v in verified}
        v_domains = {dom: v["id"] for v in verified for dom in v["domains"] if dom.endswith(".edu")}
        items, seen = list(verified), set()
        for d in (self.discovery.programs if self.discovery else []):
            it = self._discovered_item(d)
            hit = v_keys.get(it["_key"]) or v_domains.get(d.domain)
            if hit:
                self.merge.duplicates_of_verified.append({"discovery_id": d.discovery_id, "verified_id": hit})
                # verified record wins; its official program page becomes the confirmed discovery page
                vi = next(v for v in verified if v["id"] == hit)
                if d.fetched or self._link(str(d.provenance_url)).get("status") in ("ok", "redirect_ok") or not vi.get("official_url"):
                    vi["official_url"] = str(d.provenance_url)
                continue
            k = (it["_key"], d.degree_type)
            if k in seen:
                self.merge.duplicates_within_discovery.append({"discovery_id": d.discovery_id})
                continue
            seen.add(k)
            link = self._link(it["official_url"])
            if not d.fetched and link.get("status") not in ("ok", "redirect_ok"):
                it["evidence_status"] = "unavailable"
            items.append(it)
        from . import supplementary as supp
        for it in items:
            it["official_link"] = {"url": it["official_url"], **self._link(it["official_url"])} if it.get("official_url") else None
            it["evidence_label"] = STATUS_LABEL[it["evidence_status"]]
            core_coa = core_tui = None
            if it["tier"] == "verified":
                c = self.store.get_fact(it["id"], "cost_of_attendance"); t = self.store.get_fact(it["id"], "tuition")
                core_coa = {"value": c.value, "period": c.period, "source_url": c.evidence[0]["source_url"]} if c.status == "verified" and c.evidence else None
                core_tui = {"value": t.value, "period": t.period, "source_url": t.evidence[0]["source_url"]} if t.status == "verified" and t.evidence else None
            it["costs"] = supp.cost_summary(it["id"], core_coa, core_tui)
            # an official cost of attendance validated from a supplementary official page fills a core gap (never a secondary value)
            if it["cost_of_attendance"] is None and it["costs"]["official_coa"]:
                oc = it["costs"]["official_coa"]
                it["cost_of_attendance"] = {"value": oc["value"], "period": oc["period"], "evidence_ids": [], "source": "supplementary_official"}
        self.items = items

    def _link(self, url: str | None) -> dict:
        return dict(self.links.get(url or "", {}))

    # ----- search -----
    def search(self, q: str = "", tier: str | None = None, state: str | None = None, stem_verified: bool = False,
               max_cost: float | None = None, sort: str = "relevance", status: str | None = None) -> list[dict]:
        ql = q.strip().lower()
        res = []
        for it in self.items:
            hay = " ".join(str(it.get(k) or "") for k in ("university", "school", "program_name", "city", "state")).lower()
            kws = [k["keyword"] for k in it["career_keywords"]]
            terms = ql.split()
            if terms and not all(t in hay or any(t in k.lower() for k in kws) for t in terms):
                continue
            matched = sorted({k for k in kws for t in terms if t in k.lower() and t not in hay})
            if tier and it["tier"] != tier:
                continue
            if status and it["evidence_status"] != status:
                continue
            if state and it["state"] != state:
                continue
            if stem_verified and it["stem_designated"] is not True:
                continue
            if max_cost is not None and not (it["cost_of_attendance"] and it["cost_of_attendance"]["value"] <= max_cost):
                continue
            res.append({**it, "matched_keywords": matched})
        if sort == "name":
            res.sort(key=lambda i: i["university"].lower())
        elif sort == "cost":  # grounded: only verified costs are ordered; unknown cost always last
            res.sort(key=lambda i: (i["cost_of_attendance"] is None, (i["cost_of_attendance"] or {}).get("value", 0), i["university"]))
        elif sort == "evidence":  # most verified facts first; discovered (0 verified facts) last
            res.sort(key=lambda i: (-(i.get("verified_fields") or 0), i["university"].lower()))
        elif sort == "relevance":  # evidence level first, then most verified facts, then A-Z
            order = {"detailed": 0, "partial": 1, "discovered": 2, "unavailable": 3}
            res.sort(key=lambda i: (order[i["evidence_status"]], -(i.get("verified_fields") or 0), i["university"].lower()))
        elif sort == "state":
            res.sort(key=lambda i: (i["state"] is None, i["state"] or "", i["university"]))
        else:
            res.sort(key=lambda i: (i["tier"] != "verified", i["university"].lower()))
        return [{k: v for k, v in it.items() if not k.startswith("_")} for it in res]

    def get(self, item_id: str) -> dict | None:
        it = next((i for i in self.items if i["id"] == item_id), None)
        return None if it is None else {k: v for k, v in it.items() if not k.startswith("_")}

    def counts(self) -> dict:
        by = {k: sum(i["evidence_status"] == k for i in self.items) for k in STATUS_LABEL}
        return {"by_evidence_status": by, "verified": sum(i["tier"] == "verified" for i in self.items),
                "discovered": sum(i["tier"] == "discovered" for i in self.items),
                "duplicates_of_verified_skipped": len(self.merge.duplicates_of_verified),
                "duplicates_within_discovery_skipped": len(self.merge.duplicates_within_discovery)}


def detailed_program_ids(store: EvidenceStore) -> list[str]:
    """Programs whose computed evidence status is 'detailed' (same rule the UI shows)."""
    return [it["id"] for it in Catalog(store, None).items if it["tier"] == "verified" and it["evidence_status"] == "detailed"]


def store_for_profile(store: EvidenceStore, profile) -> EvidenceStore:
    """Demo runs (fictional fixtures) use only 'detailed' programs so results aren't mostly unknowns.
    Real users always get the full store. Turn off with AC_DEMO_DETAILED_ONLY=0."""
    import os
    if not getattr(profile, "is_fictional", False) or os.getenv("AC_DEMO_DETAILED_ONLY", "1") == "0":
        return store
    keep = set(detailed_program_ids(store))
    return EvidenceStore(store.dataset.model_copy(update={"programs": [p for p in store.dataset.programs if p.program_id in keep]}))
