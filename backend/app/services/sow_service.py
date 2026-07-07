"""Statement of Work intake — configurable parameters + rules-driven staffing.

The set of project parameters is data-driven (see DEFAULT_DEFINITIONS). Each parameter
carries staffing rules that decide which agents to deploy and how many. Admins can edit
the definitions, so new parameters (budget, duration, compliance, …) influence the team
without code changes.
"""

from __future__ import annotations

import json
import re

from app.services import llm

# The deployable roster.
ROLE_CATALOG: dict[str, dict] = {
    "pmo": {"name": "PMO Agent", "type": "leadership",
            "brief": "coordinate the team, synthesize status reports from every agent's work, "
                     "track risks and progress, and set direction from leadership",
            "capabilities": ["status-reporting", "coordination", "risk-tracking", "stakeholder-comms"]},
    "requirements": {"name": "Requirements Agent", "type": "functional",
                     "brief": "translate the SOW into PRDs, user stories, and acceptance criteria",
                     "capabilities": ["prd-generation", "user-story-writing", "acceptance-criteria"]},
    "ux": {"name": "UX Agent", "type": "functional",
           "brief": "design user flows, wireframes, and the design system (incl. localization)",
           "capabilities": ["wireframing", "user-flow-design", "design-systems"]},
    "business": {"name": "Business Logic Agent", "type": "functional",
                 "brief": "define data models, business rules, validation, and governance",
                 "capabilities": ["data-modeling", "business-rule-definition", "validation-logic"]},
    "architect": {"name": "Architect Agent", "type": "technical",
                  "brief": "choose the tech stack and design the system and database schema",
                  "capabilities": ["system-design", "tech-selection", "schema-design"]},
    "developer": {"name": "Developer Agent", "type": "technical",
                  "brief": "implement features, write clean code, and refactor",
                  "capabilities": ["code-generation", "implementation", "refactoring"]},
    "tester": {"name": "Tester Agent", "type": "technical",
               "brief": "plan and execute test cycles across unit, integration, and e2e levels",
               "capabilities": ["unit-testing", "integration-testing", "e2e-testing"]},
    "devops": {"name": "DevOps Agent", "type": "technical",
               "brief": "set up CI/CD and deploy to the TEST/staging environment, and keep that "
                        "environment provisioned, healthy, and running",
               "capabilities": ["ci-cd-config", "test-env-deploy", "health-checks"]},
    "release": {"name": "Release Agent", "type": "technical",
                "brief": "promote and deploy the release to the PRODUCTION environment with rollout "
                         "and rollback plans, and keep production provisioned, healthy, and running",
                "capabilities": ["production-deploy", "rollback-planning", "uptime-monitoring"]},
}

# PMO leads; functional/technical do the work; release deploys to prod last.
_ROLE_ORDER = ["pmo", "requirements", "ux", "business", "architect", "developer",
               "tester", "devops", "release"]

APPROACH_ROLES: dict[str, list[str]] = {
    "waterfall": ["pmo", "requirements", "business", "architect", "developer", "tester", "devops", "release"],
    "agile": ["pmo", "requirements", "ux", "architect", "developer", "tester"],
    "devops": ["pmo", "requirements", "architect", "developer", "tester", "devops", "release"],
    "hybrid": ["pmo", "requirements", "ux", "business", "architect", "developer", "tester", "devops", "release"],
}

_COUNTRIES = [
    "United States", "USA", "US", "United Kingdom", "UK", "Canada", "Mexico", "Brazil",
    "Germany", "France", "Spain", "Italy", "Netherlands", "Belgium", "Switzerland", "Sweden",
    "Norway", "Denmark", "Poland", "Ireland", "Portugal", "Austria", "India", "China", "Japan",
    "Singapore", "Australia", "New Zealand", "UAE", "Saudi Arabia", "South Africa", "Nigeria",
    "Kenya", "Argentina", "Chile", "Colombia", "South Korea", "Indonesia", "Malaysia", "Thailand",
]

# ─── Configurable parameter definitions ─────────────────────────────────────
# type: number | text | select | list
# staffing rule types:
#   set_base_roles      — by_value: {option: [roles]}            (select)
#   add_roles_if_gt     — threshold: N, roles: [...]             (number)
#   add_roles_if_len_gt — threshold: N, roles: [...]             (list)
#   add_roles_if_contains_any — values: [...], roles: [...]      (list/text)
#   scale_role          — role: str, cap: N                      (number → count)
DEFAULT_DEFINITIONS: list[dict] = [
    {"key": "approach", "label": "Delivery approach", "type": "select",
     "options": ["agile", "waterfall", "devops", "hybrid"], "default": "agile",
     "keywords": ["approach", "methodology", "agile", "scrum", "sprint", "waterfall", "v-model", "devops", "hybrid"],
     "staffing": [{"type": "set_base_roles", "by_value": APPROACH_ROLES}]},
    {"key": "releases", "label": "Releases", "type": "number", "default": 1,
     "keywords": ["releases", "release"],
     "staffing": [{"type": "add_roles_if_gt", "threshold": 1, "roles": ["devops", "release"]}]},
    {"key": "test_cycles", "label": "Test cycles", "type": "number", "default": 1,
     "keywords": ["test cycles", "test cycle", "cycles of testing", "test phases"],
     "staffing": [{"type": "scale_role", "role": "tester", "cap": 3}]},
    {"key": "countries", "label": "Countries", "type": "list", "default": [],
     "keywords": ["countries", "markets", "regions", "geographies"],
     "staffing": [{"type": "add_roles_if_len_gt", "threshold": 1, "roles": ["ux"]}]},
    {"key": "budget_usd", "label": "Budget (USD)", "type": "number", "default": 0,
     "keywords": ["budget", "cost", "value of the contract", "contract value"],
     "staffing": [{"type": "add_roles_if_gt", "threshold": 250000, "roles": ["business"]}]},
    {"key": "duration_months", "label": "Duration (months)", "type": "number", "default": 1,
     "keywords": ["duration", "months", "timeline", "engagement length"],
     "staffing": [{"type": "add_roles_if_gt", "threshold": 6, "roles": ["devops"]}]},
    {"key": "compliance", "label": "Compliance", "type": "list", "default": [],
     "options": ["GDPR", "HIPAA", "SOC2", "PCI", "ISO27001"],
     "keywords": ["compliance", "regulatory", "gdpr", "hipaa", "soc2", "pci", "iso27001"],
     "staffing": [{"type": "add_roles_if_contains_any",
                   "values": ["GDPR", "HIPAA", "SOC2", "PCI", "ISO27001"], "roles": ["business", "tester"]}]},
]


def default_values(definitions: list[dict]) -> dict:
    return {d["key"]: d.get("default") for d in definitions}


def normalize_values(values: dict, definitions: list[dict]) -> dict:
    out = default_values(definitions)
    for d in definitions:
        k = d["key"]
        v = (values or {}).get(k, d.get("default"))
        t = d["type"]
        if t == "number":
            try:
                v = int(float(v))
            except (TypeError, ValueError):
                v = int(d.get("default") or 0)
        elif t == "list":
            if isinstance(v, str):
                v = [x.strip() for x in re.split(r"[,;/]", v) if x.strip()]
            elif not isinstance(v, list):
                v = []
        elif t == "select":
            opts = d.get("options") or []
            v = v if v in opts else d.get("default")
        out[k] = v
    return out


# ─── Analysis ────────────────────────────────────────────────────────────────
async def analyze_sow(text: str, definitions: list[dict]) -> dict:
    text = (text or "").strip()
    if not text:
        vals = default_values(definitions)
        return {"project_name": "New Engagement", "summary": "", "parameters": vals,
                "agents": derive_team(vals, definitions, ""), "source": "heuristic"}

    extracted = await _llm_extract(text, definitions)
    source = "llm"
    if not extracted:
        extracted = _heuristic_extract(text, definitions)
        source = "heuristic"

    values = normalize_values(extracted.get("parameters", {}), definitions)
    summary = extracted.get("summary", "")
    return {
        "project_name": extracted.get("project_name") or _guess_name(text),
        "summary": summary,
        "parameters": values,
        "agents": derive_team(values, definitions, summary),
        "source": source,
    }


async def _llm_extract(text: str, definitions: list[dict]) -> dict | None:
    schema = ", ".join(
        f'"{d["key"]}" ({d["type"]}'
        + (f", one of {d.get('options')}" if d.get("options") else "")
        + ")"
        for d in definitions
    )
    system = (
        "Extract the delivery parameters from a signed Statement of Work. "
        f"The parameters to extract are: {schema}. "
        'Return ONLY JSON: {"project_name": str, "summary": str, "parameters": {<key>: <value>}}. '
        "Infer sensible defaults for anything unstated. No prose outside the JSON."
    )
    out, provider = await llm.chat_complete(system, text[:12000], max_tokens=700)
    if not out or provider == "none":
        return None
    try:
        match = re.search(r"\{.*\}", out, re.DOTALL)
        data = json.loads(match.group(0) if match else out)
        return data if "parameters" in data else None
    except Exception:
        return None


def _heuristic_extract(text: str, definitions: list[dict]) -> dict:
    low = text.lower()
    params: dict = {}
    for d in definitions:
        k, t = d["key"], d["type"]
        if t == "select":
            chosen = d.get("default")
            for opt in d.get("options") or []:
                syn = [opt.lower()] + (["scrum", "sprint"] if opt == "agile" else [])
                if any(s in low for s in syn):
                    chosen = opt
                    break
            params[k] = chosen
        elif t == "number":
            params[k] = _find_count(low, d.get("keywords", [k]), int(d.get("default") or 0))
        elif t == "list":
            if k == "countries":
                params[k] = _detect_countries(text, low, d)
            elif d.get("options"):
                params[k] = [o for o in d["options"] if o.lower() in low]
            else:
                n = _find_count(low, d.get("keywords", [k]), 0)
                params[k] = [f"{d['label']} {i}" for i in range(1, n + 1)]
        else:
            params[k] = d.get("default")
    return {"project_name": _guess_name(text), "summary": _summary(text), "parameters": params}


def _detect_countries(text: str, low: str, d: dict) -> list[str]:
    found = [c for c in _COUNTRIES if re.search(rf"\b{re.escape(c)}\b", text, re.IGNORECASE)]
    countries = _dedup_countries(found)
    if not countries:
        n = _find_count(low, d.get("keywords", ["countries"]), 0)
        countries = [f"Country {i}" for i in range(1, n + 1)] if n else []
    return countries


def _find_count(low: str, terms: list[str], default: int) -> int:
    # strict: "3 releases" or "releases: 3"
    for term in terms:
        m = re.search(rf"(\d[\d,]*)\s+{re.escape(term)}", low) or re.search(
            rf"{re.escape(term)}\s*[:\-]?\s*\$?(\d[\d,]*)", low
        )
        if m:
            try:
                return max(0, int(m.group(1).replace(",", "")))
            except ValueError:
                continue
    # lenient: "budget is 750000", "duration of 12" — allow a few words in between,
    # stopping before any other digit so we don't grab an unrelated number.
    for term in terms:
        m = re.search(rf"{re.escape(term)}[^.\d]{{0,15}}\$?(\d[\d,]*)", low)
        if m:
            try:
                return max(0, int(m.group(1).replace(",", "")))
            except ValueError:
                continue
    return default


def _dedup_countries(found: list[str]) -> list[str]:
    canon = {"usa": "United States", "us": "United States", "united states": "United States",
             "uk": "United Kingdom", "united kingdom": "United Kingdom"}
    seen, out = set(), []
    for c in found:
        key = canon.get(c.lower(), c)
        if key.lower() not in seen:
            seen.add(key.lower())
            out.append(key)
    return out


# ─── Rules engine: parameters → team ────────────────────────────────────────
def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def apply_rules(values: dict, definitions: list[dict]) -> tuple[list[str], dict, dict]:
    """Return (ordered_roles, role_counts, role_reasons)."""
    base: list[str] | None = None
    add: set[str] = set()
    counts: dict[str, int] = {}
    reasons: dict[str, str] = {}

    for d in definitions:
        v = values.get(d["key"], d.get("default"))
        for rule in d.get("staffing", []):
            rt = rule.get("type")
            if rt == "set_base_roles":
                base = list(rule["by_value"].get(str(v), [])) or base
            elif rt == "add_roles_if_gt" and _num(v) > rule["threshold"]:
                for r in rule["roles"]:
                    add.add(r)
                    reasons.setdefault(r, f"{d['label']} > {rule['threshold']}")
            elif rt == "add_roles_if_len_gt" and len(v or []) > rule["threshold"]:
                for r in rule["roles"]:
                    add.add(r)
                    reasons.setdefault(r, f"{len(v)} {d['label'].lower()}")
            elif rt == "add_roles_if_contains_any":
                vals = v if isinstance(v, list) else [v]
                low = [str(x).lower() for x in vals]
                if any(str(x).lower() in low for x in rule["values"]):
                    for r in rule["roles"]:
                        add.add(r)
                        reasons.setdefault(r, f"{d['label']}: {', '.join(map(str, vals))}")
            elif rt == "scale_role":
                counts[rule["role"]] = max(1, min(int(_num(v)), rule.get("cap", 99)))
                if int(_num(v)) > 1:
                    reasons[rule["role"]] = f"{int(_num(v))} {d['label'].lower()}"

    base = base or APPROACH_ROLES["agile"]
    roleset = set(base) | add
    roles = [r for r in _ROLE_ORDER if r in roleset]
    return roles, counts, reasons


def derive_team(values: dict, definitions: list[dict], summary: str = "") -> list[dict]:
    values = normalize_values(values, definitions)
    roles, counts, reasons = apply_rules(values, definitions)
    scope = _scope_note(values, definitions, summary)

    agents: list[dict] = []
    for role in roles:
        n = counts.get(role, 1)
        for k in range(1, n + 1):
            name = ROLE_CATALOG[role]["name"] + (f" — Cycle {k}" if n > 1 else "")
            rationale = reasons.get(role) or (
                "Core role for every engagement." if role == "requirements"
                else ROLE_CATALOG[role]["brief"]
            )
            agents.append(_agent(role, rationale, scope, name))
    return agents


def _scope_note(values: dict, definitions: list[dict], summary: str) -> str:
    parts = []
    for d in definitions:
        v = values.get(d["key"])
        if isinstance(v, list):
            v = ", ".join(map(str, v)) or "none"
        parts.append(f"{d['label']}: {v}")
    note = "Engagement parameters — " + "; ".join(parts) + "."
    if summary:
        note += f" Summary: {summary}"
    return note


def _agent(role: str, rationale: str, scope: str, name: str | None = None) -> dict:
    cat = ROLE_CATALOG[role]
    instructions = (
        f"You are the {name or cat['name']} on this engagement. Your job is to {cat['brief']}. "
        f"Skills: {', '.join(cat['capabilities'])}. {scope} "
        "Be concrete, complete, and ready to hand off to the next agent."
    )
    return {"role": role, "name": name or cat["name"], "rationale": rationale, "instructions": instructions}


def _summary(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()[:400]


def _guess_name(text: str) -> str:
    for line in text.splitlines():
        s = line.strip(" #*-[]")
        if 3 <= len(s) <= 80:
            return s
    return "New Engagement"
