"""Fail-closed action policy; agents never hold merge or admin authority."""

ALLOWED = frozenset({"inspect", "test", "collect_receipt"})


def authorize(action, scope, *, authenticated_actor=None, trusted_actors=()):
    """Require independently supplied authenticated identity, not scope claims."""
    return (
        action in ALLOWED
        and isinstance(scope, dict)
        and bool(scope.get("repository"))
        and bool(scope.get("source_sha"))
        and scope.get("write") is False
        and isinstance(authenticated_actor, str)
        and bool(authenticated_actor)
        and authenticated_actor in frozenset(trusted_actors)
    )
