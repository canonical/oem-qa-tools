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


def update_db(repo_path: str):
    """
    Scans the repo and updates the database.
    """
    # Create tables if not exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    db.query(Job).delete()
    db.query(TestPlan).delete()
    db.commit()

    print(f"Scanning {repo_path}...")
    count = 0

    # Walk through the providers directory mainly?
    # The user said "checkbox git repo". We scan everything or specific dirs?
    # Usually jobs are in providers/ folders or similar.
    # We will scan the whole thing but look for .pxu files.

    skipped_counts = {}

    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".pxu"):
                file_path = os.path.join(root, file)
                try:
                    for unit in parse_pxu(file_path):
                        # Filter logic:
                        # Include: unit: job, unit: template, or other
                        # units that might have an ID we care about?
                        # User said: "not include unit: eqiure to
                        # test plan, manifest and category"
                        # Common valid units for "jobs": 'job', 'template'
                        # Explicitly exclude the ones mentioned.

                        unit_type = unit.get("unit")
                        if not unit_type:
                            # PXU job units often omit 'unit:' and identify
                            # themselves via 'plugin:' instead (legacy style).
                            if unit.get("plugin"):
                                unit_type = "job"
                            else:
                                continue

                        # Normalize unit type checking
                        if unit_type == "test plan":
                            plan_id = unit.get("id", "")
                            if not plan_id:
                                continue
                            provider = get_provider_namespace(
                                file_path, repo_path
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
                            skipped_counts["test plan"] = (
                                skipped_counts.get("test plan", 0) + 1
                            )
                            continue

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

                        # We previously filtered strictly for job/template.
                        # To catch "everything", we will rely on ID presence
                        # and the exclusion list above.

                        job_id = unit.get("id")
                        if not job_id:
                            # Log units without ID that are not excluded
                            key = f"{unit_type} (no id)"
                            skipped_counts[key] = (
                                skipped_counts.get(key, 0) + 1
                            )
                            continue

                        requires = unit.get("requires", "")
                        manifest_deps = extract_manifest_requirements(requires)

                        # Flatten fields
                        environ = unit.get("environ", "")
                        command = unit.get("command", "")
                        command_envs = extract_environ_from_command(command)

                        # Provider resolution
                        provider = get_provider_namespace(file_path, repo_path)

                        # Check if duplicate job_id exists (templates might
                        # define same ID? unlikely for distinct units)
                        # We used to dedup, but since we dropped unique
                        # constraint and user wants ALL jobs
                        # (even same ID across providers),
                        # we just add it.

                        declared_envs = environ.split() if environ else []
                        all_envs = sorted(
                            set(declared_envs) | set(command_envs)
                        )

                        job_entry = Job(
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
                        db.add(job_entry)
                        count += 1

                        # If the job has flags: also-after-suspend, Checkbox
                        # automatically generates a runtime variant prefixed
                        # with 'after-suspend-'. Store it explicitly so test
                        # plan include patterns resolve correctly.
                        flags = unit.get("flags", "")
                        if "also-after-suspend" in flags:
                            as_id = "after-suspend-" + job_id
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
                            count += 1
                except Exception as e:
                    print(f"Error parsing {file_path}: {e}")

    db.commit()
    db.close()
    print(f"Database updated. {count} jobs found.")
    print("Skipped units summary:")
    for k, v in skipped_counts.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    # Test run
    import sys

    if len(sys.argv) > 1:
        update_db(sys.argv[1])
    else:
        print("Usage: python parser.py <path_to_checkbox_repo>")
