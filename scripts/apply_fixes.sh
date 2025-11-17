#!/bin/bash
# Quick fix script for Issues #14 and #13

echo "🔧 Fixing GitHub Actions Issues #14 and #13..."
echo ""

# Step 1: Add src/ directory
echo "📁 Step 1: Adding src/ directory to git..."
git add src/
if [ $? -eq 0 ]; then
    echo "✅ src/ added successfully"
else
    echo "❌ Failed to add src/"
    exit 1
fi

# Step 2: Fix flake8 compatibility
echo ""
echo "🐛 Step 2: Fixing flake8 compatibility..."
if ! grep -q "importlib-metadata<5.0" DMAIC_V3/requirements.txt 2>/dev/null; then
    echo "importlib-metadata<5.0" >> DMAIC_V3/requirements.txt
    git add DMAIC_V3/requirements.txt
    echo "✅ Added importlib-metadata<5.0 to requirements.txt"
else
    echo "ℹ️  importlib-metadata already in requirements.txt"
fi

# Step 3: Show what will be committed
echo ""
echo "📊 Files to be committed:"
git status --short

# Step 4: Commit
echo ""
echo "💾 Step 3: Committing changes..."
git commit -m "fix: Add src/dmaic module and pin importlib-metadata

- Add src/ directory to repository (fixes #14)
- Pin importlib-metadata<5.0 for flake8 compatibility (fixes #13)
- This should fix Bridge Smoke Tests and Static Analysis workflows"

if [ $? -eq 0 ]; then
    echo "✅ Changes committed successfully"
else
    echo "❌ Failed to commit changes"
    exit 1
fi

# Step 5: Push
echo ""
echo "🚀 Step 4: Pushing to GitHub..."
echo "Branch: feature/dow-integration"
read -p "Press Enter to push, or Ctrl+C to cancel..."

git push origin feature/dow-integration

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Successfully pushed to GitHub!"
    echo ""
    echo "🎉 Done! Check GitHub Actions:"
    echo "   https://github.com/GBOGEB/ABACUS/actions"
    echo ""
    echo "📋 Expected results:"
    echo "   ✅ Bridge Smoke Tests should PASS"
    echo "   ✅ Bridge Unit Tests should PASS"
    echo "   ✅ Bridge Integration Tests should PASS"
    echo "   ✅ Static Analysis should PASS"
else
    echo "❌ Failed to push to GitHub"
    exit 1
fi
