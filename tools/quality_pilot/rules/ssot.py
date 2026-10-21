# Rule self-test fixture: `opengrep scan --test tools/quality_pilot/rules`
# Annotations: "ruleid:" must match on the next line, "ok:" must not.
import math
import pathlib

from CoolProp.CoolProp import PropsSI

# ruleid: ssot-hardcoded-helium-constant
T_LAMBDA = 2.1768

# ok: ssot-hardcoded-helium-constant
T_OPERATING = 1.9

# ruleid: eos-call-outside-adapter
rho = PropsSI("D", "T", 4.5, "P", 1.3e5, "Helium")


def bump_counter(n):
    # ruleid: protected-ssot-file-write
    with open("patches/PATCH_COUNTER", "w") as f:
        f.write(str(n))
    # ok: protected-ssot-file-write
    with open("patches/PATCH_COUNTER", "r") as f:
        return f.read()


def save_manifest(text):
    # ruleid: protected-ssot-file-write
    pathlib.Path("manifest.yaml").write_text(text)


def converged(residual):
    # ruleid: float-exact-equality
    if residual == 0.0:
        return True
    # ok: float-exact-equality
    return math.isclose(residual, 0.0, abs_tol=1e-9)
