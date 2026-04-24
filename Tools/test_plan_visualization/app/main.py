from fastapi import FastAPI, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional
import json

from .database import get_db, Job, TestPlan, engine, Base

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def read_items(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/jobs")
def get_jobs(
    provider: Optional[str] = None,
    category: Optional[str] = None,
    environ: Optional[str] = None,
    manifest: Optional[str] = None,
    has_template_id: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    import re as _re

    query = db.query(Job)

    if provider:
        query = query.filter(Job.provider == provider)
    if category:
        query = query.filter(Job.category_id == category)

    if environ:
        query = query.filter(Job.environ.contains(environ))

    if manifest:
        query = query.filter(Job.manifest.contains(manifest))

    jobs = query.all()

    if has_template_id is not None:
        jobs = [
            j
            for j in jobs
            if bool(
                (json.loads(j.data) if j.data else {}).get("template-id", "")
            )
            == has_template_id
        ]

    if search:
        sl = search.lower()

        # helper: convert checkbox glob pattern to regex
        def _matches(pattern: str, jid: str) -> bool:
            try:
                esc = _re.sub(r"\.(?!\*)", r"\\.", pattern)
                esc = esc.replace(".*", "\x00")
                esc = esc.replace(".", r"\.")
                esc = esc.replace("\x00", ".*")
                return bool(_re.match("^" + esc + "$", jid))
            except _re.error:
                return pattern == jid

        # 1. Jobs whose own ID contains the search term
        job_id_set = {j.job_id for j in jobs if sl in j.job_id.lower()}

        # 2. Jobs that belong to test plans whose ID contains the search term
        all_plans = db.query(TestPlan).all()
        by_full_id = {p.full_id: p for p in all_plans}
        by_bare_id = {p.plan_id: p for p in all_plans}

        def _resolve(ref: str):
            return by_full_id.get(ref) or by_bare_id.get(ref.split("::")[-1])

        def _collect_patterns(plan, visited=None):
            """Recursively collect include patterns from a plan
            and all its nested_parts."""
            if visited is None:
                visited = set()
            if plan.full_id in visited:
                return set()
            visited.add(plan.full_id)
            patterns = set(json.loads(plan.include) if plan.include else [])
            for child_ref in (
                json.loads(plan.nested_part) if plan.nested_part else []
            ):
                child = _resolve(child_ref)
                if child:
                    patterns |= _collect_patterns(child, visited)
            return patterns

        matching_plans = [
            p
            for p in all_plans
            if sl in p.full_id.lower() or sl in p.plan_id.lower()
        ]

        plan_job_id_set = set()
        for plan in matching_plans:
            patterns = _collect_patterns(plan)
            for job in jobs:
                bare_job = job.job_id.split("::")[-1]
                import re as _re3

                def _norm(s):
                    s = _re3.sub(r"/(\d+|\{[^}]+\})_", "/INDEX_", s)
                    s = _re3.sub(r"_(\.\*|\{+[^}]+\}+)", "_WILDCARD", s)
                    return s

                norm_job = _norm(bare_job)
                for pat in patterns:
                    bare_pat = pat.split("::")[-1]
                    matched = (
                        _matches(bare_pat, bare_job)
                        or _matches(bare_pat, job.job_id)
                        or _norm(bare_pat) == norm_job
                    )
                    if matched:
                        plan_job_id_set.add(job.job_id)
                        break

        combined = job_id_set | plan_job_id_set
        jobs = [j for j in jobs if j.job_id in combined]

    # Convert to dict for JSON response
    results = []
    for job in jobs:
        job_data = json.loads(job.data) if job.data else {}
        results.append(
            {
                "id": job.job_id,
                "template_id": job_data.get("template-id", ""),
                "provider": job.provider,
                "category": job.category_id,
                "environ": json.loads(job.environ) if job.environ else [],
                "manifest": json.loads(job.manifest) if job.manifest else [],
                "summary": job.summary,
                "command": job.command,
                "data": job_data,
            }
        )

    return results


@app.get("/api/options")
def get_options(
    provider: Optional[str] = None,
    category: Optional[str] = None,
    environ: Optional[str] = None,
    manifest: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Job)

    if provider:
        query = query.filter(Job.provider == provider)
    if category:
        query = query.filter(Job.category_id == category)
    if environ:
        # Exact match or contains? For options, if we selected one,
        # we probably keep it.
        # But filtering the *options* usually means:
        # "Show me what's available given these filters".
        # If I selected environ=X, the available environs should still
        # include X, and others that exist in the *same subset*.
        # Actually usually dropdowns show *other* compatible options.
        query = query.filter(Job.environ.contains(environ))
    if manifest:
        query = query.filter(Job.manifest.contains(manifest))

    jobs = query.all()

    # Aggregate options from the filtered result set
    providers = set()
    categories = set()
    environs = set()
    manifests = set()

    for job in jobs:
        if job.provider:
            providers.add(job.provider)
        if job.category_id:
            categories.add(job.category_id)

        # Parse environ JSON list
        if job.environ:
            try:
                envs = json.loads(job.environ)
                for e in envs:
                    environs.add(e)
            except (json.JSONDecodeError, ValueError):
                pass

        # Parse manifest JSON list
        if job.manifest:
            try:
                mans = json.loads(job.manifest)
                for m in mans:
                    manifests.add(m)
            except (json.JSONDecodeError, ValueError):
                pass

    return {
        "providers": sorted(list(providers)),
        "categories": sorted(list(categories)),
        "environs": sorted(list(environs)),
        "manifests": sorted(list(manifests)),
    }


@app.get("/api/testplans")
def get_job_testplans(job_id: str, db: Session = Depends(get_db)):
    """
    For a given job ID, return all test plans that directly or indirectly
    include it, with full ancestry chain.
    """
    all_plans = db.query(TestPlan).all()

    # Build lookup: full_id -> plan, also bare id -> plan
    by_full_id = {}
    by_bare_id = {}
    for p in all_plans:
        by_full_id[p.full_id] = p
        by_bare_id[p.plan_id] = p

    def resolve(ref: str):
        """Resolve a plan reference to a TestPlan,
        tolerating missing namespace."""
        if ref in by_full_id:
            return by_full_id[ref]
        # strip namespace if present
        bare = ref.split("::")[-1]
        return by_bare_id.get(bare)

    # Find plans that directly include this job_id (regex/glob pattern match)
    import re

    def matches(pattern: str, jid: str) -> bool:
        # Checkbox uses .* globs; convert to regex
        # Escape dots except those that are part of .* wildcards
        try:
            escaped = re.sub(r"\.(?!\*)", r"\\.", pattern)
            escaped = escaped.replace(".*", "___WILDCARD___")
            escaped = escaped.replace(".", r"\.")
            escaped = escaped.replace("___WILDCARD___", ".*")
            regex = re.compile("^" + escaped + "$")
            return bool(regex.match(jid))
        except re.error:
            return pattern == jid

    # bare job id (without namespace)
    bare_job_id = job_id.split("::")[-1]

    direct_plans = set()
    for p in all_plans:
        includes = json.loads(p.include) if p.include else []
        for pattern in includes:
            bare_pattern = pattern.split("::")[-1]
            if matches(bare_pattern, bare_job_id) or matches(
                bare_pattern, job_id
            ):
                direct_plans.add(p.full_id)
                break

    # Build reverse nested_part map: child_full_id -> set of parent full_ids
    parent_map = {}
    for p in all_plans:
        nested = json.loads(p.nested_part) if p.nested_part else []
        for child_ref in nested:
            child = resolve(child_ref)
            if child:
                parent_map.setdefault(child.full_id, set()).add(p.full_id)

    # BFS upward from direct_plans through nested_part parents
    def build_ancestors(start_ids):
        visited = {}
        queue = list(start_ids)
        while queue:
            fid = queue.pop(0)
            if fid in visited:
                continue
            plan = by_full_id.get(fid)
            if not plan:
                continue
            parents = sorted(parent_map.get(fid, set()))
            visited[fid] = {
                "id": plan.full_id,
                "name": plan.name or plan.plan_id,
                "parents": parents,
            }
            queue.extend(parents)
        return visited

    ancestors = build_ancestors(direct_plans)

    # Build ordered tree: direct plans first, then their parents etc.
    # Return as flat list with level indicator for easy rendering
    def to_ordered_list(start_ids, ancestors, depth=0, seen=None):
        if seen is None:
            seen = set()
        result = []
        for fid in sorted(start_ids):
            if fid in seen or fid not in ancestors:
                continue
            seen.add(fid)
            node = ancestors[fid]
            result.append(
                {"id": node["id"], "name": node["name"], "depth": depth}
            )
            result.extend(
                to_ordered_list(node["parents"], ancestors, depth + 1, seen)
            )
        return result

    ordered = to_ordered_list(direct_plans, ancestors)
    return {"job_id": job_id, "test_plans": ordered}


@app.get("/api/plan-tree")
def get_plan_tree(search: str, db: Session = Depends(get_db)):
    """
    Search for test plans by name/ID and return each as a recursive tree
    (nested_part children + directly included jobs).
    """
    import re as _re

    all_plans = db.query(TestPlan).all()
    all_jobs_list = db.query(Job).all()

    by_full_id = {p.full_id: p for p in all_plans}
    by_bare_id = {p.plan_id: p for p in all_plans}

    def resolve_plan(ref: str):
        return by_full_id.get(ref) or by_bare_id.get(ref.split("::")[-1])

    def _matches_job(pattern: str, job_id: str) -> bool:
        try:
            esc = _re.sub(r"\.(?!\*)", r"\\.", pattern)
            esc = esc.replace(".*", "\x00")
            esc = esc.replace(".", r"\.")
            esc = esc.replace("\x00", ".*")
            return bool(_re.match("^" + esc + "$", job_id))
        except _re.error:
            return pattern == job_id

    def _normalize_for_template(s: str) -> str:
        """Normalize a pattern or job ID for fuzzy template matching:
        Collapse '/{N}_' and '/{var}_' index prefixes to '/INDEX_', and
        collapse '_.*' and '_{variable}' suffixes to '_WILDCARD' so that
        include patterns match their template unit counterparts.
        (after-suspend- prefix is no longer stripped — those jobs are stored
        explicitly in the DB via also-after-suspend flag expansion.)
        """
        s = _re.sub(r"/(\d+|\{[^}]+\})_", "/INDEX_", s)
        s = _re.sub(r"_(\.\*|\{+[^}]+\}+)", "_WILDCARD", s)
        return s

    def get_direct_jobs(plan, accumulated_excludes=None):
        includes = json.loads(plan.include) if plan.include else []
        if not includes:
            return []
        if accumulated_excludes is None:
            accumulated_excludes = []
        seen = set()
        result = []
        for pattern in includes:
            bare_pat = pattern.split("::")[-1]
            norm_pat = _normalize_for_template(bare_pat)
            for j in all_jobs_list:
                if j.job_id in seen:
                    continue
                bare_job = j.job_id.split("::")[-1]
                matched = (
                    _matches_job(bare_pat, bare_job)
                    or _matches_job(bare_pat, j.job_id)
                    or _normalize_for_template(bare_job) == norm_pat
                )
                if matched:
                    seen.add(j.job_id)
                    jdata = json.loads(j.data) if j.data else {}
                    excluded = any(
                        _matches_job(ep.split("::")[-1], bare_job)
                        or _matches_job(ep.split("::")[-1], j.job_id)
                        for ep in accumulated_excludes
                    )
                    result.append(
                        {
                            "id": j.job_id,
                            "summary": j.summary or "",
                            "plugin": jdata.get(
                                "plugin", j.unit_type or "job"
                            ),
                            "excluded": excluded,
                        }
                    )
        return result

    def build_tree(plan, visited=None, accumulated_excludes=None):
        if visited is None:
            visited = set()
        if accumulated_excludes is None:
            accumulated_excludes = []
        if plan.full_id in visited:
            return None  # cycle guard
        visited = visited | {plan.full_id}
        own_excludes = json.loads(plan.exclude) if plan.exclude else []
        new_accumulated = accumulated_excludes + own_excludes
        children = []
        for ref in (json.loads(plan.nested_part) if plan.nested_part else []):
            child = resolve_plan(ref)
            if child:
                child_tree = build_tree(child, visited, new_accumulated)
                if child_tree:
                    children.append(child_tree)
        return {
            "id": plan.full_id,
            "name": plan.name or plan.plan_id,
            "exclude_patterns": own_excludes,
            "children": children,
            "jobs": get_direct_jobs(plan, new_accumulated),
        }

    sl = search.strip().lower()
    matching = [
        p
        for p in all_plans
        if sl in p.full_id.lower()
        or sl in p.plan_id.lower()
        or sl in (p.name or "").lower()
    ]

    trees = [t for t in (build_tree(p) for p in matching) if t is not None]
    return {"plans": trees, "total": len(trees)}


@app.get("/api/plan-details")
def get_plan_details(plan_id: str, db: Session = Depends(get_db)):
    """Return full details of a single test plan."""
    all_plans = db.query(TestPlan).all()

    by_full_id = {p.full_id: p for p in all_plans}
    by_bare_id = {p.plan_id: p for p in all_plans}

    plan = by_full_id.get(plan_id) or by_bare_id.get(plan_id.split("::")[-1])
    if not plan:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Plan not found")

    raw = json.loads(plan.data) if plan.data else {}
    return {
        "id": plan.full_id,
        "plan_id": plan.plan_id,
        "provider": plan.provider,
        "name": plan.name or plan.plan_id,
        "include": json.loads(plan.include) if plan.include else [],
        "exclude": json.loads(plan.exclude) if plan.exclude else [],
        "nested_part": (
            json.loads(plan.nested_part) if plan.nested_part else []
        ),
        "data": raw,
    }


@app.get("/api/compare-plans")
def compare_plans(plan1: str, plan2: str, db: Session = Depends(get_db)):
    """
    Compute the effective job sets of two test plans (respecting excludes
    from each plan and all its nested parts) and return the diff.
    """
    import re as _re

    all_plans = db.query(TestPlan).all()
    all_jobs_list = db.query(Job).all()

    by_full_id = {p.full_id: p for p in all_plans}
    by_bare_id = {p.plan_id: p for p in all_plans}

    def resolve_plan(ref: str):
        return by_full_id.get(ref) or by_bare_id.get(ref.split("::")[-1])

    def _matches(pattern: str, jid: str) -> bool:
        try:
            esc = _re.sub(r"\.(?!\*)", r"\\.", pattern)
            esc = (
                esc.replace(".*", "\x00")
                .replace(".", r"\.")
                .replace("\x00", ".*")
            )
            return bool(_re.match("^" + esc + "$", jid))
        except _re.error:
            return pattern == jid

    def _normalize(s: str) -> str:
        s = _re.sub(r"/(\d+|\{[^}]+\})_", "/INDEX_", s)
        s = _re.sub(r"_(\.\*|\{+[^}]+\}+)", "_WILDCARD", s)
        return s

    jobs_by_id = {j.job_id: j for j in all_jobs_list}

    def effective_jobs(plan, visited=None, inherited_excludes=None):
        """Return set of job_ids effectively included
        after applying excludes."""
        if visited is None:
            visited = set()
        if inherited_excludes is None:
            inherited_excludes = []
        if plan.full_id in visited:
            return set()
        visited = visited | {plan.full_id}

        own_excludes = json.loads(plan.exclude) if plan.exclude else []
        all_excludes = inherited_excludes + own_excludes

        result = set()
        for pattern in (json.loads(plan.include) if plan.include else []):
            bare_pat = pattern.split("::")[-1]
            norm_pat = _normalize(bare_pat)
            for j in all_jobs_list:
                bare_job = j.job_id.split("::")[-1]
                if (
                    _matches(bare_pat, bare_job)
                    or _matches(bare_pat, j.job_id)
                    or _normalize(bare_job) == norm_pat
                ):
                    result.add(j.job_id)

        for ref in (json.loads(plan.nested_part) if plan.nested_part else []):
            child = resolve_plan(ref)
            if child:
                result |= effective_jobs(child, visited, all_excludes)

        # Apply this plan's own excludes to the full accumulated set
        if own_excludes:
            result = {
                jid
                for jid in result
                if not any(
                    _matches(ep.split("::")[-1], jid.split("::")[-1])
                    or _matches(ep.split("::")[-1], jid)
                    for ep in own_excludes
                )
            }
        return result

    p1 = resolve_plan(plan1)
    p2 = resolve_plan(plan2)

    if not p1 or not p2:
        from fastapi import HTTPException

        missing = plan1 if not p1 else plan2
        # Log all known bare IDs to help debug
        known = sorted(by_bare_id.keys())[:20]
        raise HTTPException(
            status_code=404,
            detail=(
                f"Plan not found: '{missing}'."
                f" Sample known plan IDs: {known}"
            ),
        )

    set1 = effective_jobs(p1)
    set2 = effective_jobs(p2)

    def _job_info(jid):
        j = jobs_by_id.get(jid)
        return {"id": jid, "summary": j.summary or "" if j else ""}

    only1 = sorted(set1 - set2)
    only2 = sorted(set2 - set1)
    both = sorted(set1 & set2)

    return {
        "plan1": {
            "id": p1.full_id,
            "name": p1.name or p1.plan_id,
            "total": len(set1),
        },
        "plan2": {
            "id": p2.full_id,
            "name": p2.name or p2.plan_id,
            "total": len(set2),
        },
        "only_in_plan1": [_job_info(j) for j in only1],
        "only_in_plan2": [_job_info(j) for j in only2],
        "in_both": [_job_info(j) for j in both],
    }
