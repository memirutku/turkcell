#!/usr/bin/env bash
# Phase 1 Infrastructure Verification Script
# Usage: ./scripts/verify_phase1.sh
# Returns: exit 0 if all checks pass, exit 1 on any failure

set -euo pipefail

PASS=0
FAIL=0
TOTAL=0

check() {
    local name="$1"
    local cmd="$2"
    TOTAL=$((TOTAL + 1))
    echo -n "  [$TOTAL] $name... "
    if eval "$cmd" > /dev/null 2>&1; then
        echo "PASSED"
        PASS=$((PASS + 1))
    else
        echo "FAILED"
        FAIL=$((FAIL + 1))
    fi
}

echo "========================================"
echo "  Turkcell AI-Gen - Phase 1 Verification"
echo "========================================"
echo ""

echo "[1/5] Container Health"
check "All containers running" "docker compose ps --format json | grep -q 'running'"
check "API container healthy" "docker compose ps api --format '{{.Health}}' | grep -q 'healthy'"
check "Web container healthy" "docker compose ps web --format '{{.Health}}' | grep -q 'healthy'"
check "Redis container healthy" "docker compose ps redis --format '{{.Health}}' | grep -q 'healthy'"
check "Milvus container healthy" "docker compose ps milvus-standalone --format '{{.Health}}' | grep -q 'healthy'"

echo ""
echo "[2/5] Service Endpoints"
check "FastAPI health returns 200" "curl -sf http://localhost:8000/api/health | grep -q 'healthy'"
check "Next.js loads" "curl -sf http://localhost:3000 | grep -q 'html'"

echo ""
echo "[3/5] Mock BSS/OSS API"
check "Tariffs endpoint returns data" "curl -sf http://localhost:8000/api/mock/tariffs | python3 -c 'import sys,json; d=json.load(sys.stdin); assert len(d)>=5'"
check "Customers endpoint returns data" "curl -sf http://localhost:8000/api/mock/customers/1 | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d[\"name\"]'"
check "Bills endpoint returns data" "curl -sf http://localhost:8000/api/mock/customers/1/bills | python3 -c 'import sys,json; d=json.load(sys.stdin); assert len(d)>=1'"

echo ""
echo "[4/5] Data Services"
check "Redis PING responds" "docker compose exec -T redis redis-cli ping | grep -q PONG"
check "Milvus port accepting connections" "curl -sf http://localhost:9091/healthz"

echo ""
echo "[5/5] Security"
check "No hardcoded API keys in source" "! grep -rn 'sk-\|AKIA[A-Z0-9]\{16\}\|api_key\s*=\s*\"[a-zA-Z0-9]' backend/ frontend/ docker-compose.yml 2>/dev/null"
check ".env not tracked by git" "! git ls-files --error-unmatch .env 2>/dev/null"

echo ""
echo "========================================"
echo "  Results: $PASS/$TOTAL passed, $FAIL failed"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
echo "All Phase 1 checks passed!"
exit 0
