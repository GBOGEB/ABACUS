"""Collection rules for the DMAIC_V3 suite.

The docker-image probes check the host's Docker install, not product code.
They are opt-in (DMAIC_DOCKER_TESTS=1). Without the opt-in they are left out
of collection, explicitly and in one place, instead of contributing governed
skips to the canonical coverage run. With the opt-in, every invocation of the
suite (canonical run, `pytest DMAIC_V3/tests/`, clean-clone proofs) runs them.
"""

import os

collect_ignore = []
if os.environ.get("DMAIC_DOCKER_TESTS", "0") != "1":
    collect_ignore.append("test_docker_images.py")
