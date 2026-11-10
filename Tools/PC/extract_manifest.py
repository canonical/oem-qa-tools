#!/usr/bin/env python3
"""
Print the machine manifest of Checkbox submissions as JSON.

Manifests of multiple submissions are merged. Keys whose values differ between
submissions are reported on stderr (the first value is kept in the output).
"""

import argparse
import json
import sys
import tarfile


def extract_manifest(submission: dict):
    """
    Return the machine manifest payload of a submission.

    Raises KeyError if the submission has no machine manifest.
    """
    payload = submission["system_information"]["machine_manifest"]["outputs"][
        "payload"
    ]
    if isinstance(payload, str):
        return json.loads(payload)
    return payload


def load_submission(path: str) -> dict:
    """Load a submission json file, or the one inside a tar archive."""
    if not tarfile.is_tarfile(path):
        with open(path) as fp:
            return json.load(fp)
    with tarfile.open(path) as tar:
        for member in tar:
            if member.isfile() and member.name.split("/")[-1] == (
                "submission.json"
            ):
                return json.load(tar.extractfile(member))
    raise KeyError("submission.json not found in archive")


def merge_manifests(manifests: list[dict]):
    """
    Merge manifests into one.

    Return the merged manifest (the first seen value wins) and a dict mapping
    each key whose value differs between manifests to the list of values.
    """
    merged = {}
    values = {}
    for manifest in manifests:
        for key, value in manifest.items():
            merged.setdefault(key, value)
            seen = values.setdefault(key, [])
            if value not in seen:
                seen.append(value)
    differences = {k: v for k, v in values.items() if len(v) > 1}
    return merged, differences


def main(args):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "submissions",
        nargs="+",
        help="Paths to submission json files or to tar archives (e.g. "
        ".tar.xz) containing a submission.json.",
    )
    args = parser.parse_args(args)
    manifests = []
    for path in args.submissions:
        try:
            submission = load_submission(path)
            manifests.append(extract_manifest(submission))
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            print(
                f"{path}: unable to extract manifest: {exc!r}",
                file=sys.stderr,
            )
            return 1
    try:
        merged, differences = merge_manifests(manifests)
    except AttributeError:
        print("Manifests must be json objects to be merged", file=sys.stderr)
        return 1
    for key, values in differences.items():
        print(f"Different values for {key}: {values}", file=sys.stderr)
    print(json.dumps(merged, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
