# W81 repair-outcome block

W81 is the bounded continuation after W80 closed as a controlled negative diagnostic.

It first rechecks the four missing low-PC1 W79 states and requires them to remain
`NO_ACTIONS_EVIDENCE` if no authoritative GitHub Actions runs exist.

It then measures two objective repair episodes using the same deterministic work
vector used by W78/W79, projects those exact source states onto the frozen W79
semantic PC1 basis, and binds the episode outcomes to authoritative GitHub Actions
run/job evidence.

The pair semantics are deliberately non-causal: a failing historical PR head and
a later repair PR head that closes the same named red are an observed repair
episode, not a single-commit treatment effect.

W81 does not refit PCA, does not reopen timing PCA, and does not admit Bradley-Terry.
The initial two repair episodes form two disconnected pair components and W80 PC1
predictive validation remains false.
