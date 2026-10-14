"""Fail-closed action policy; agents never hold merge or admin authority."""
ALLOWED = frozenset({"inspect", "test", "collect_receipt"})
def authorize(action, scope):
    return (action in ALLOWED and isinstance(scope, dict)
            and bool(scope.get("repository")) and bool(scope.get("source_sha"))
            and scope.get("write") is False)
