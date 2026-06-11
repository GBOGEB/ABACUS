#!/bin/bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────
# QPLANT — Emergency Rollback
# ─────────────────────────────────────────────────────────────────────

NS="qplant-production"
DEPLOYMENT="qplant-api-server"

echo "⚠️  QPLANT Emergency Rollback"
echo "   Namespace:  $NS"
echo "   Deployment: $DEPLOYMENT"
echo "───────────────────────────────────────────────"

# Show current revision
echo ""
echo "Current rollout history:"
kubectl rollout history deployment/"$DEPLOYMENT" -n "$NS" 2>/dev/null || echo "(no history available)"

# Perform rollback
echo ""
echo "Rolling back to previous revision..."
kubectl rollout undo deployment/"$DEPLOYMENT" -n "$NS"

# Wait for rollout
echo ""
echo "Waiting for rollback to complete..."
kubectl rollout status deployment/"$DEPLOYMENT" -n "$NS" --timeout=120s

# Verify
echo ""
echo "Post-rollback pod status:"
kubectl get pods -n "$NS" -l app=qplant-api

echo ""
echo "✅ Rollback complete. Verify application health manually."
echo "   Run: bash deployment/scripts/validate_deployment.sh"
