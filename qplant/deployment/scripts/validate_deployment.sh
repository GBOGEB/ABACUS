#!/bin/bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────
# QPLANT v4.4.0 — Post-Deployment Validation
# ─────────────────────────────────────────────────────────────────────

NS="qplant-production"
ERRORS=0

echo "🔍 Post-Deployment Validation — QPLANT v4.4.0"
echo "───────────────────────────────────────────────"

# 1. Check all pods running
echo ""
echo "1. Pod Status"
READY=$(kubectl get pods -n "$NS" --no-headers 2>/dev/null | grep -c "Running" || true)
TOTAL=$(kubectl get pods -n "$NS" --no-headers 2>/dev/null | wc -l || true)
if [ "$READY" -ge 3 ]; then
    echo "   ✅ $READY/$TOTAL pods running"
else
    echo "   ❌ Only $READY/$TOTAL pods running (expected ≥3)"
    ERRORS=$((ERRORS + 1))
fi

# 2. Verify ConfigMap
echo ""
echo "2. SSOT ConfigMap"
CM_VERSION=$(kubectl get configmap qplant-ssot-v4-4-0 -n "$NS" -o jsonpath='{.metadata.annotations.version}' 2>/dev/null || echo "NOT_FOUND")
if [ "$CM_VERSION" = "v4.4.0" ]; then
    echo "   ✅ ConfigMap version: $CM_VERSION"
else
    echo "   ❌ ConfigMap version mismatch: $CM_VERSION"
    ERRORS=$((ERRORS + 1))
fi

# 3. Health check endpoints
echo ""
echo "3. Health Checks"
SVC_IP=$(kubectl get svc qplant-api-service -n "$NS" -o jsonpath='{.spec.clusterIP}' 2>/dev/null || echo "")
if [ -n "$SVC_IP" ]; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://$SVC_IP/api/v1/health" --connect-timeout 5 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        echo "   ✅ Health endpoint responding (HTTP $HTTP_CODE)"
    else
        echo "   ⚠️  Health endpoint returned HTTP $HTTP_CODE"
    fi
else
    echo "   ⚠️  Service IP not available (expected in CI)"
fi

# 4. Check logs for errors
echo ""
echo "4. Error Log Check"
ERROR_COUNT=$(kubectl logs -l app=qplant-api -n "$NS" --tail=100 2>/dev/null | grep -ci "error\|exception\|traceback" || true)
if [ "$ERROR_COUNT" -eq 0 ]; then
    echo "   ✅ No errors in recent logs"
else
    echo "   ⚠️  $ERROR_COUNT error lines in recent logs"
fi

# 5. HPA status
echo ""
echo "5. Autoscaler Status"
HPA_STATUS=$(kubectl get hpa -n "$NS" --no-headers 2>/dev/null | head -1 || echo "NOT_FOUND")
if [ "$HPA_STATUS" != "NOT_FOUND" ]; then
    echo "   ✅ HPA configured: $HPA_STATUS"
else
    echo "   ⚠️  HPA not found"
fi

# 6. Network Policy
echo ""
echo "6. Network Policy"
NP_COUNT=$(kubectl get networkpolicy -n "$NS" --no-headers 2>/dev/null | wc -l || true)
if [ "$NP_COUNT" -ge 1 ]; then
    echo "   ✅ $NP_COUNT network policies active"
else
    echo "   ⚠️  No network policies found"
fi

# Summary
echo ""
echo "═══════════════════════════════════════════════"
if [ "$ERRORS" -eq 0 ]; then
    echo "✅ All validation checks passed"
    exit 0
else
    echo "❌ $ERRORS validation errors detected"
    exit 1
fi
