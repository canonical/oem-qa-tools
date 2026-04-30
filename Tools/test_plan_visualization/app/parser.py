import os
import re
import json
from .database import Job, ManifestEntry, TestPlan, PlanMembership, SessionLocal, engine, Base


# ---------------------------------------------------------------------------
# Pattern-matching helpers (shared between parser and main.py)
# ---------------------------------------------------------------------------

def _match_pat(pattern: str, jid: str) -> bool:
    """Match a checkbox glob pattern (may contain .*) against a job ID."""
    try:
        esc = (
            pattern.replace(".*", "\x00")
            .replace(".", r"\.")
            .replace("\x00", ".*")
        )
        return bool(re.match("^" + esc + "$", jid))
    except re.error:
        return pattern == jid


def _normalize_for_template(s: str) -> str:
    """
    Normalise a job ID or include pattern for fuzzy template matching.
    Collapses /{N}_ and /{var}_ index prefixes → /INDEX_
    and _.*  / _{variable} suffixes → _WILDCARD.
    """
    s = re.sub(r"/(\d+|\{[^}]+\})_", "/INDEX_", s)
    s = re.sub(r"_(\.\*|\{+[^}]+\}+)", "_WILDCARD", s)
    return s


def job_matches_pattern(pattern: str, job_id: str) -> bool:
    """Return True if *job_id* matches the include/exclude *pattern*."""
    bare_pat = pattern.split("::")[-1]
    bare_job = job_id.split("::")[-1]
    if _match_pat(bare_pat, bare_job) or _match_pat(bare_pat, job_id):
        return True
    # Template fuzzy match
    if _normalize_for_template(bare_pat) == _normalize_for_template(bare_job):
        return True
    return False


# ---------------------------------------------------------------------------
# PXU file parser
# ---------------------------------------------------------------------------

def parse_pxu(file_path):
    """
    Parses a PXU file and yields unit definitions as dictionaries.
    """
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    blocks = re.split(r"\n\s*\n", content)

    for block in blocks:
        if not block.strip():
            continue

        unit = {}
        current_key = None
        for line in block.splitlines():
            if line.startswith("#") or not line.strip():
                continue

            if line.startswith(" ") or line.startswith("\t"):
                if current_key:
                    unit[current_key] += "\n" + line.strip()
            else:
                if ":" in line:
                    key, value = line.split(":", 1)
                    current_key = key.strip()
                    unit[current_key] = value.strip()

        if unit:
            yield unit


def extract_environ_from_command(command_str: str) -> list:
    """
    Extracts environment variable names referenced in a command string.
    Matches both $VAR and ${VAR} patterns.
    """
    if not command_str:
        return []
    matches = re.findall(
        r"\$\{([A-Z_][A-Z0-9_]*)\}|\$([A-Z_][A-Z0-9_]*)", command_str
    )
    return list(set(m[0] or m[1] for m in matches))


def extract_manifest_requirements(requires_str):
    """
    Extracts manifest keys from the 'requires' field.
    e.g., "manifest.has_thunderbolt == 'True'" -> ["has_thunderbolt"]
    """
    if not requires_str:
        return []
    matches = re.findall(r"manifest\.([a-zA-Z0-9_]+)", requires_str)
    return list(set([m for m in matches if m != "ns"]))


def get_provider_namespace(file_path, repo_root):
    """
    Walks up the directory tree to find manage.py and extracts the namespace.
    """
    current_dir = os.path.dirname(os.path.abspath(file_path))
    repo_root = os.path.abspath(repo_root)

    while current_dir.startswith(repo_root):
        manage_path = os.path.join(current_dir, "manage.py")
        if os.path.exists(manage_path):
            try:
                with open(manage_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    match = re.search(
                        r'namespace\s*=\s*[\'"]([^\'"]+)[\'"]', content
                    )
                    if match:
                        return match.group(1)
            except Exception:
                pass
            return "unknown"

        if current_dir == repo_root:
            break
        current_dir = os.path.dirname(current_dir)

    return "unknown"


def parse_include_ids(raw: str) -> list:
    """
    Parse an include, nested_part, or bootstrap_include field value into
    a list of IDs/patterns, stripping inline options and comments.
    """
    ids = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        token = line.split()[0]
        ids.append(token)
    return ids


# ---------------------------------------------------------------------------
# DB scanning
# ---------------------------------------------------------------------------

# Unit types that produce no runnable jobs and are not manifest entries.
_SKIP_UNIT_TYPES = {"category", "packaging meta-data", "exporter"}


def _scan_path(
    db,
    scan_path: str,
    repo_root: str,
    seen_job_ids: set,
    seen_plan_ids: set,
    seen_manifest_ids: set,
    priority: bool,
):
    """
    Walk *scan_path* for .pxu files and insert units into *db*.

    Stores:
    - test plans  → TestPlan table
    - regular jobs, resource jobs, attachment jobs → Job table
    - manifest entries → ManifestEntry table

    priority=True  → local providers folder; always insert, record IDs.
    priority=False → checkbox git repo; skip IDs already seen.

    Returns (job_count, skipped_counts_dict).
    """
    count = 0
    skipped_counts = {}

    for root, _dirs, files in os.walk(scan_path):
        for file in files:
            if not file.endswith(".pxu"):
                continue
            file_path = os.path.join(root, file)
            try:
                for unit in parse_pxu(file_path):
                    unit_type = unit.get("unit", "").strip()

                    # ── Infer unit type for legacy-style units ─────────────
                    if not unit_type:
                        flags_val = unit.get("flags", "")
                        flag_tokens = flags_val.split()
                        if (
                            unit.get("plugin")
                            or "simple" in flag_tokens
                            or unit.get("command")
                        ):
                            unit_type = "job"
                        else:
                            continue

                    # ── Skip non-job/non-plan/non-manifest types ───────────
                    if unit_type in _SKIP_UNIT_TYPES:
                        skipped_counts[unit_type] = (
                            skipped_counts.get(unit_type, 0) + 1
                        )
                        continue

                    provider = get_provider_namespace(file_path, repo_root)

                    # ── Test plans ─────────────────────────────────────────
                    if unit_type == "test plan":
                        plan_id = unit.get("id", "")
                        if not plan_id:
                            continue
                        if not priority and plan_id in seen_plan_ids:
                            skipped_counts["test plan (dup)"] = (
                                skipped_counts.get("test plan (dup)", 0) + 1
                            )
                            continue
                        full_id = (
                            f"{provider}::{plan_id}"
                            if "::" not in plan_id
                            else plan_id
                        )
                        db.add(
                            TestPlan(
                                plan_id=plan_id,
                                full_id=full_id,
                                provider=provider,
                                name=unit.get("_name", ""),
                                include=json.dumps(
                                    parse_include_ids(unit.get("include", ""))
                                ),
                                exclude=json.dumps(
                                    parse_include_ids(unit.get("exclude", ""))
                                ),
                                nested_part=json.dumps(
                                    parse_include_ids(unit.get("nested_part", ""))
                                ),
                                bootstrap_include=json.dumps(
                                    parse_include_ids(unit.get("bootstrap_include", ""))
                                ),
                                data=json.dumps(unit),
                            )
                        )
                        seen_plan_ids.add(plan_id)
                        skipped_counts["test plan"] = (
                            skipped_counts.get("test plan", 0) + 1
                        )
                        continue

                    # ── Manifest entries ───────────────────────────────────
                    if unit_type == "manifest entry":
                        entry_id = unit.get("id", "")
                        if not entry_id:
                            continue
                        if not priority and entry_id in seen_manifest_ids:
                            skipped_counts["manifest entry (dup)"] = (
                                skipped_counts.get("manifest entry (dup)", 0) + 1
                            )
                            continue
                        full_id = (
                            f"{provider}::{entry_id}"
                            if "::" not in entry_id
                            else entry_id
                        )
                        db.add(
                            ManifestEntry(
                                entry_id=entry_id,
                                full_id=full_id,
                                provider=provider,
                                name=unit.get("_name", ""),
                                value_type=unit.get("value-type", ""),
                                summary=unit.get("_summary", ""),
                                data=json.dumps(unit),
                            )
                        )
                        seen_manifest_ids.add(entry_id)
                        skipped_counts["manifest entry"] = (
                            skipped_counts.get("manifest entry", 0) + 1
                        )
                        continue

                    # ── Jobs (regular, resource, attachment, template, …) ──
                    job_id = unit.get("id")
                    if not job_id:
                        key = f"{unit_type} (no id)"
                        skipped_counts[key] = (
                            skipped_counts.get(key, 0) + 1
                        )
                        continue

                    if not priority and job_id in seen_job_ids:
                        skipped_counts["job (dup)"] = (
                            skipped_counts.get("job (dup)", 0) + 1
                        )
                        continue

                    requires = unit.get("requires", "")
                    manifest_deps = extract_manifest_requirements(requires)

                    environ = unit.get("environ", "")
                    command = unit.get("command", "")
                    command_envs = extract_environ_from_command(command)

                    declared_envs = environ.split() if environ else []
                    all_envs = sorted(
                        set(declared_envs) | set(command_envs)
                    )

                    plugin_val = unit.get("plugin", "")

                    db.add(
                        Job(
                            job_id=job_id,
                            provider=provider,
                            category_id=unit.get("category_id", ""),
                            environ=json.dumps(all_envs),
                            manifest=json.dumps(manifest_deps),
                            command=command,
                            summary=unit.get("_summary", unit.get("summary", "")),
                            description=unit.get("_description", unit.get("description", "")),
                            unit_type=unit_type,
                            plugin=plugin_val,
                            data=json.dumps(unit),
                        )
                    )
                    seen_job_ids.add(job_id)
                    count += 1

                    # Mirror also-after-suspend variants
                    flags = unit.get("flags", "")
                    if "also-after-suspend" in flags:
                        as_id = "after-suspend-" + job_id
                        if priority or as_id not in seen_job_ids:
                            as_unit = dict(unit, id=as_id)
                            db.add(
                                Job(
                                    job_id=as_id,
                                    provider=provider,
                                    category_id=unit.get("category_id", ""),
                                    environ=json.dumps(all_envs),
                                    manifest=json.dumps(manifest_deps),
                                    command=command,
                                    summary=unit.get("_summary", unit.get("summary", "")),
                                    description=unit.get("_description", unit.get("description", "")),
                                    unit_type=unit_type,
                                    plugin=plugin_val,
                                    data=json.dumps(as_unit),
                                )
                            )
                            seen_job_ids.add(as_id)
                            count += 1

            except Exception as e:
                print(f"Error parsing {file_path}: {e}")

    return count, skipped_counts


# ---------------------------------------------------------------------------
# Plan membership computation
# ---------------------------------------------------------------------------

def _compute_all_effective_jobs(all_plans, all_job_ids):
    """
    For every TestPlan, compute the set of job IDs that are effectively
    included (after applying excludes at every level).  Follows both
    nested_part *and* bootstrap_include chains so that resource/bootstrap
    jobs referenced by sub-plans are included, matching `checkbox expand`.

    Returns a dict: plan_full_id → frozenset of job_ids.
    """
    by_full_id = {p.full_id: p for p in all_plans}
    by_bare_id = {p.plan_id: p for p in all_plans}

    def resolve(ref):
        return by_full_id.get(ref) or by_bare_id.get(ref.split("::")[-1])

    memo = {}

    def effective(plan_full_id, computing=None):
        if plan_full_id in memo:
            return memo[plan_full_id]
        if computing is None:
            computing = set()
        if plan_full_id in computing:
            return frozenset()  # cycle guard
        computing = computing | {plan_full_id}

        plan = by_full_id.get(plan_full_id)
        if not plan:
            return frozenset()

        own_excludes = json.loads(plan.exclude) if plan.exclude else []
        include_patterns = json.loads(plan.include) if plan.include else []
        bootstrap_refs = json.loads(plan.bootstrap_include) if plan.bootstrap_include else []
        nested_refs = json.loads(plan.nested_part) if plan.nested_part else []

        result = set()

        # 1. Direct include patterns matched against all job IDs
        for pattern in include_patterns:
            bare_pat = pattern.split("::")[-1]
            norm_pat = _normalize_for_template(bare_pat)
            for job_id in all_job_ids:
                bare_job = job_id.split("::")[-1]
                if (
                    _match_pat(bare_pat, bare_job)
                    or _match_pat(bare_pat, job_id)
                    or _normalize_for_template(bare_job) == norm_pat
                ):
                    result.add(job_id)

        # 2. Bootstrap include: resource jobs run before template expansion
        for ref in bootstrap_refs:
            bare_ref = ref.split("::")[-1]
            for job_id in all_job_ids:
                bare_job = job_id.split("::")[-1]
                if (
                    bare_ref == bare_job
                    or ref == job_id
                    or _match_pat(bare_ref, bare_job)
                ):
                    result.add(job_id)
                    break

        # 3. Recurse into nested_part (children carry their own excludes)
        for ref in nested_refs:
            child = resolve(ref)
            if child:
                result |= effective(child.full_id, computing)

        # 4. Apply this plan's own excludes to the full accumulated set
        if own_excludes:
            result = {
                jid
                for jid in result
                if not any(
                    _match_pat(ep.split("::")[-1], jid.split("::")[-1])
                    or _match_pat(ep.split("::")[-1], jid)
                    for ep in own_excludes
                )
            }

        result = frozenset(result)
        memo[plan_full_id] = result
        return result

    return {p.full_id: effective(p.full_id) for p in all_plans}


def compute_plan_membership(db):
    """
    Populate the plan_membership table with precomputed effective job sets.
    Called once at the end of update_db() after all units are committed.
    """
    print("Computing plan membership…")
    all_plans = db.query(TestPlan).all()
    all_job_ids = [row.job_id for row in db.query(Job.job_id)]

    membership = _compute_all_effective_jobs(all_plans, all_job_ids)

    db.query(PlanMembership).delete()

    rows = []
    for plan_full_id, job_ids in membership.items():
        for job_id in job_ids:
            rows.append(PlanMembership(plan_full_id=plan_full_id, job_id=job_id))

    db.bulk_save_objects(rows)
    db.commit()

    total = sum(len(v) for v in membership.values())
    print(
        f"Plan membership computed: {len(membership)} plans, "
        f"{total} (plan, job) pairs."
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def update_db(repo_path: str, providers_path: str = None):
    """
    Build the database from two sources:

    1. Local *providers_path* directory (priority) — parsed first; its IDs
       are recorded so duplicates from the upstream repo are skipped.
    2. Upstream checkbox git repo at *repo_path* — parsed second.

    After loading all units, computes PlanMembership for fast compare.
    """
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    db.query(Job).delete()
    db.query(TestPlan).delete()
    db.query(ManifestEntry).delete()
    db.query(PlanMembership).delete()
    db.commit()

    seen_job_ids: set = set()
    seen_plan_ids: set = set()
    seen_manifest_ids: set = set()
    total_count = 0
    all_skipped: dict = {}

    # ── 1. Local providers (priority) ─────────────────────────────────────
    if providers_path is None:
        providers_path = "providers"
    if os.path.isdir(providers_path):
        print(f"Scanning local providers at '{providers_path}'…")
        cnt, skipped = _scan_path(
            db,
            providers_path,
            providers_path,
            seen_job_ids,
            seen_plan_ids,
            seen_manifest_ids,
            priority=True,
        )
        total_count += cnt
        print(f"  {cnt} jobs loaded from local providers.")
        for k, v in skipped.items():
            all_skipped[k] = all_skipped.get(k, 0) + v
    else:
        print(
            f"No local providers folder found at '{providers_path}', "
            "skipping."
        )

    # ── 2. Checkbox git repo ───────────────────────────────────────────────
    print(f"Scanning checkbox repo at '{repo_path}'…")
    cnt, skipped = _scan_path(
        db,
        repo_path,
        repo_path,
        seen_job_ids,
        seen_plan_ids,
        seen_manifest_ids,
        priority=False,
    )
    total_count += cnt
    for k, v in skipped.items():
        all_skipped[k] = all_skipped.get(k, 0) + v

    db.commit()

    print(f"Database updated. {total_count} jobs total.")
    print("Unit summary:")
    for k, v in sorted(all_skipped.items()):
        print(f"  {k}: {v}")

    # ── 3. Precompute plan membership ──────────────────────────────────────
    compute_plan_membership(db)

    db.close()


if __name__ == "__main__":
    pass

