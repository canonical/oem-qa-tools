import os
import re
import json
from .database import Job, TestPlan, SessionLocal, engine, Base


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

    # Simple regex to find manifest.KEY
    # We look for manifest.KEY
    matches = re.findall(r"manifest\.([a-zA-Z0-9_]+)", requires_str)
    # Filter out 'ns' if it appears (manifest.ns)
    return list(set([m for m in matches if m != "ns"]))


def get_provider_namespace(file_path, repo_root):
    """
    Walks up the directory tree to find manage.py and extracts the namespace.
    """
    current_dir = os.path.dirname(os.path.abspath(file_path))
    repo_root = os.path.abspath(repo_root)

    # Safety check to avoid infinite loop if outside repo
    while current_dir.startswith(repo_root):
        manage_path = os.path.join(current_dir, "manage.py")
        if os.path.exists(manage_path):
            try:
                with open(manage_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Look for namespace="com.foo.bar"
                    # handling both single and double quotes
                    match = re.search(
                        r'namespace\s*=\s*[\'"]([^\'"]+)[\'"]', content
                    )
                    if match:
                        return match.group(1)
            except Exception:
                pass  # If we can't read it, just continue or fallback
            # Found manage.py but failed to parse? Or keep looking?
            return "unknown"
            # Usually manage.py defines the provider,
            # so if found, that's the place.

        if current_dir == repo_root:
            break
        current_dir = os.path.dirname(current_dir)

    return "unknown"


def parse_include_ids(raw: str) -> list:
    """
    Parse an include or nested_part field value into a list of IDs/patterns,
    stripping inline options like 'certification-status=blocker' and comments.
    """
    ids = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # First token is the ID/pattern; rest are options
        token = line.split()[0]
        ids.append(token)
    return ids


def _scan_path(
    db,
    scan_path: str,
    repo_root: str,
    seen_job_ids: set,
    seen_plan_ids: set,
    priority: bool,
):
    """
    Walk *scan_path* for .pxu files and insert jobs/test-plans into *db*.

    priority=True  → local providers folder; add all units unconditionally
                     and record their IDs in the seen sets.
    priority=False → checkbox git repo; skip any unit whose ID was already
                     added by a higher-priority source.

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
                    unit_type = unit.get("unit")
                    if not unit_type:
                        # Legacy plugin: style  OR  modern flags: simple
                        # (which implies a shell job with no explicit
                        # unit/plugin field).
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

                    # ── Test plans ────────────────────────────────────────
                    if unit_type == "test plan":
                        plan_id = unit.get("id", "")
                        if not plan_id:
                            continue
                        if not priority and plan_id in seen_plan_ids:
                            skipped_counts["test plan (dup)"] = (
                                skipped_counts.get("test plan (dup)", 0) + 1
                            )
                            continue
                        provider = get_provider_namespace(
                            file_path, repo_root
                        )
                        full_id = (
                            f"{provider}::{plan_id}"
                            if "::" not in plan_id
                            else plan_id
                        )
                        include_ids = parse_include_ids(
                            unit.get("include", "")
                        )
                        exclude_ids = parse_include_ids(
                            unit.get("exclude", "")
                        )
                        nested_ids = parse_include_ids(
                            unit.get("nested_part", "")
                        )
                        db.add(
                            TestPlan(
                                plan_id=plan_id,
                                full_id=full_id,
                                provider=provider,
                                name=unit.get("_name", ""),
                                include=json.dumps(include_ids),
                                exclude=json.dumps(exclude_ids),
                                nested_part=json.dumps(nested_ids),
                                data=json.dumps(unit),
                            )
                        )
                        seen_plan_ids.add(plan_id)
                        skipped_counts["test plan"] = (
                            skipped_counts.get("test plan", 0) + 1
                        )
                        continue

                    # ── Non-job unit types to skip ─────────────────────────
                    if unit_type in [
                        "manifest entry",
                        "category",
                        "packaging meta-data",
                        "exporter",
                        "attachment",
                        "resource",
                    ]:
                        skipped_counts[unit_type] = (
                            skipped_counts.get(unit_type, 0) + 1
                        )
                        continue

                    # ── Jobs ──────────────────────────────────────────────
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

                    provider = get_provider_namespace(file_path, repo_root)

                    declared_envs = environ.split() if environ else []
                    all_envs = sorted(
                        set(declared_envs) | set(command_envs)
                    )

                    db.add(
                        Job(
                            job_id=job_id,
                            provider=provider,
                            category_id=unit.get("category_id", ""),
                            environ=json.dumps(all_envs),
                            manifest=json.dumps(manifest_deps),
                            command=command,
                            summary=unit.get("summary", ""),
                            description=unit.get("description", ""),
                            unit_type=unit_type,
                            data=json.dumps(unit),
                        )
                    )
                    seen_job_ids.add(job_id)
                    count += 1

                    # Expand also-after-suspend variants explicitly so that
                    # test-plan include patterns resolve correctly.
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
                                    summary=unit.get("summary", ""),
                                    description=unit.get("description", ""),
                                    unit_type=unit_type,
                                    data=json.dumps(as_unit),
                                )
                            )
                            seen_job_ids.add(as_id)
                            count += 1
            except Exception as e:
                print(f"Error parsing {file_path}: {e}")

    return count, skipped_counts


def update_db(repo_path: str, providers_path: str = None):
    """
    Build the database from two sources:

    1. Local *providers_path* directory (default: ``"providers"`` next to
       the working directory) — parsed **first** with priority; its job and
       test-plan IDs are recorded so duplicates from the upstream repo are
       skipped.
    2. Upstream checkbox git repo at *repo_path* — parsed second; any unit
       whose ID was already inserted from the local providers folder is
       silently skipped.

    Pass ``providers_path=None`` (or omit it) to disable local-providers
    loading entirely.
    """
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    db.query(Job).delete()
    db.query(TestPlan).delete()
    db.commit()

    seen_job_ids: set = set()
    seen_plan_ids: set = set()
    total_count = 0
    all_skipped: dict = {}

    # ── 1. Local providers (priority) ─────────────────────────────────────
    if providers_path is None:
        providers_path = "providers"
    if os.path.isdir(providers_path):
        print(f"Scanning local providers at '{providers_path}'...")
        cnt, skipped = _scan_path(
            db,
            providers_path,
            providers_path,
            seen_job_ids,
            seen_plan_ids,
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
    print(f"Scanning checkbox repo at '{repo_path}'...")
    cnt, skipped = _scan_path(
        db,
        repo_path,
        repo_path,
        seen_job_ids,
        seen_plan_ids,
        priority=False,
    )
    total_count += cnt
    for k, v in skipped.items():
        all_skipped[k] = all_skipped.get(k, 0) + v

    db.commit()
    db.close()

    print(f"Database updated. {total_count} jobs total.")
    print("Unit summary:")
    for k, v in all_skipped.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    # Test run
    import sys

    if len(sys.argv) > 1:
        update_db(sys.argv[1])
    else:
        print("Usage: python parser.py <path_to_checkbox_repo>")
