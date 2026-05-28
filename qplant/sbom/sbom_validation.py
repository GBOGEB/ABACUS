#!/usr/bin/env python3
"""
SBOM Validation and Compliance Checker for QPLANT v4.4.0.

Validates SBOM completeness, license compliance, and structure.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Known copyleft licenses that require review
COPYLEFT_LICENSES = {"GPL-2.0", "GPL-3.0", "LGPL-2.1", "LGPL-3.0", "AGPL-3.0"}
APPROVED_LICENSES = {
    "MIT", "MIT License", "Apache-2.0", "Apache Software License",
    "BSD", "BSD-2-Clause", "BSD-3-Clause", "BSD License",
    "ISC", "PSF", "Python Software Foundation License", "Unlicense",
    "MPL-2.0", "WTFPL", "Public Domain",
}


def validate_sbom(sbom_path: str = "cyclonedx_sbom.json") -> Dict[str, Any]:
    """
    Validate SBOM against quality and compliance standards.

    Checks:
    - Structure conforms to CycloneDX spec
    - All components have name and version
    - License information present
    - No copyleft conflicts
    - PURL identifiers present
    """
    path = Path(sbom_path)
    if not path.exists():
        return {"valid": False, "error": f"SBOM not found: {sbom_path}"}

    with open(path) as f:
        sbom = json.load(f)

    issues: List[str] = []
    warnings: List[str] = []

    # 1. Structure checks
    if sbom.get("bomFormat") != "CycloneDX":
        issues.append("Missing or incorrect bomFormat (expected CycloneDX)")
    if "specVersion" not in sbom:
        issues.append("Missing specVersion")
    if "metadata" not in sbom:
        issues.append("Missing metadata section")
    if "components" not in sbom:
        issues.append("Missing components section")

    # 2. Component checks
    components = sbom.get("components", [])
    missing_version = 0
    missing_license = 0
    missing_purl = 0
    copyleft_found = []

    for comp in components:
        if not comp.get("version"):
            missing_version += 1
        if not comp.get("purl"):
            missing_purl += 1

        # License check
        licenses = comp.get("licenses", [])
        if not licenses:
            missing_license += 1
        else:
            for lic in licenses:
                lic_name = lic.get("license", {}).get("name", "")
                if lic_name in COPYLEFT_LICENSES:
                    copyleft_found.append(f"{comp['name']}: {lic_name}")

    if missing_version > 0:
        warnings.append(f"{missing_version} components missing version")
    if missing_license > 0:
        warnings.append(f"{missing_license} components missing license info")
    if missing_purl > 0:
        warnings.append(f"{missing_purl} components missing PURL identifier")
    if copyleft_found:
        warnings.append(f"Copyleft licenses found: {', '.join(copyleft_found)}")

    # 3. Metadata checks
    meta = sbom.get("metadata", {})
    if not meta.get("timestamp"):
        warnings.append("Missing generation timestamp")
    if not meta.get("component", {}).get("version"):
        warnings.append("Missing project version in metadata")

    # Calculate score
    total_checks = 10
    passed = total_checks - len(issues) - min(len(warnings), 3)
    score = max(0, (passed / total_checks) * 100)

    result = {
        "valid": len(issues) == 0,
        "score": round(score, 1),
        "total_components": len(components),
        "issues": issues,
        "warnings": warnings,
        "copyleft_licenses": copyleft_found,
        "compliance": {
            "all_versions_present": missing_version == 0,
            "all_licenses_present": missing_license == 0,
            "no_copyleft_conflicts": len(copyleft_found) == 0,
            "valid_structure": len(issues) == 0,
        },
    }

    return result


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Validate QPLANT SBOM")
    parser.add_argument("--sbom", default="cyclonedx_sbom.json")
    args = parser.parse_args()

    print("🔍 Validating SBOM...")
    result = validate_sbom(args.sbom)

    print(f"\n{'═' * 50}")
    status = "✅ VALID" if result["valid"] else "❌ INVALID"
    print(f"SBOM Status: {status}")
    print(f"Score: {result['score']}/100")
    print(f"Components: {result['total_components']}")
    print(f"{'═' * 50}")

    if result["issues"]:
        print("\n❌ Issues:")
        for issue in result["issues"]:
            print(f"  - {issue}")

    if result["warnings"]:
        print("\n⚠️  Warnings:")
        for warn in result["warnings"]:
            print(f"  - {warn}")

    compliance = result["compliance"]
    print("\n📋 Compliance:")
    for check, passed in compliance.items():
        icon = "✅" if passed else "❌"
        print(f"  {icon} {check.replace('_', ' ').title()}")

    # Save validation result
    output = "sbom_validation_result.json"
    with open(output, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n📄 Result saved: {output}")

    if not result["valid"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
