#!/bin/bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────
# QPLANT v4.4.0 — Production Deployment Script
# ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
K8S_DIR="$SCRIPT_DIR/../k8s"
AUTH_DIR="$SCRIPT_DIR/../../authentication"
VERSION="v4.4.0"

echo "🚀 Deploying QPLANT $VERSION to Production"
echo "   Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "─────────────────────────────────────────────"

# Step 1: Validate environment
echo ""
echo "Step 1/8: Validating cluster access..."
if ! kubectl cluster-info > /dev/null 2>&1; then
    echo "❌ Cannot connect to Kubernetes cluster"
    echo "   Ensure kubectl is configured and cluster is reachable"
    exit 1
fi
kubectl get nodes
echo "✅ Cluster accessible"

# Step 2: Validate manifests
echo ""
echo "Step 2/8: Validating K8s manifests..."
for f in "$K8S_DIR"/*.yaml; do
    if ! kubectl apply --dry-run=client -f "$f" > /dev/null 2>&1; then
        echo "❌ Invalid manifest: $f"
        exit 1
    fi
done
echo "✅ All manifests valid"

# Step 3: Create namespace
echo ""
echo "Step 3/8: Creating namespace..."
kubectl apply -f "$K8S_DIR/namespace.yaml"
echo "✅ Namespace ready"

# Step 4: Generate API keys
echo ""
echo "Step 4/8: Generating API keys..."
if [ -f "$AUTH_DIR/key_cli.py" ]; then
    python3 "$AUTH_DIR/key_cli.py" generate --name "Production Admin" --days 365 --rate-limit 5000
    python3 "$AUTH_DIR/key_cli.py" generate --name "Monitoring" --days 365 --rate-limit 10000
    echo "✅ API keys generated (update secrets.yaml with actual keys)"
else
    echo "⚠️  key_cli.py not found — using placeholder keys"
fi

# Step 5: Deploy SSOT ConfigMap (immutable)
echo ""
echo "Step 5/8: Deploying SSOT ConfigMap..."
kubectl apply -f "$K8S_DIR/configmap-ssot-production.yaml"
echo "✅ Immutable SSOT ConfigMap deployed"

# Step 6: Deploy secrets
echo ""
echo "Step 6/8: Deploying secrets..."
kubectl apply -f "$K8S_DIR/secrets.yaml"
echo "✅ Secrets deployed"

# Step 7: Deploy application stack
echo ""
echo "Step 7/8: Deploying application..."
kubectl apply -f "$K8S_DIR/deployment-api-server.yaml"
kubectl apply -f "$K8S_DIR/service.yaml"
kubectl apply -f "$K8S_DIR/ingress.yaml"
kubectl apply -f "$K8S_DIR/hpa.yaml"
kubectl apply -f "$K8S_DIR/network-policy.yaml"
echo "⏳ Waiting for rollout..."
kubectl rollout status deployment/qplant-api-server -n qplant-production --timeout=300s
echo "✅ Application deployed"

# Step 8: Verify
echo ""
echo "Step 8/8: Verifying deployment..."
kubectl get all -n qplant-production
echo ""
kubectl get configmap qplant-ssot-v4-4-0 -n qplant-production -o jsonpath='{.metadata.annotations.version}'
echo ""

echo ""
echo "═══════════════════════════════════════════════"
echo "✅ QPLANT $VERSION deployment complete!"
echo "═══════════════════════════════════════════════"
