#!/bin/bash
# === Cosmic Ray Mutation Testing — Full Scan ===
# Run: bash run_mutation_scan.sh
# Time: ~40-50 minutes
# Output: results printed + saved to /tmp/mutation_report.txt

BACKEND="$(cd "$(dirname "$0")" && pwd)"
VENV="${BACKEND}/venv/bin"
cd "${BACKEND}"

REPORT="/tmp/mutation_report.txt"
echo "=== Cosmic Ray Mutation Scan ===" | tee "${REPORT}"
echo "Date: $(date)" | tee -a "${REPORT}"
echo "Tests: boundary + hypothesis" | tee -a "${REPORT}"
echo "" | tee -a "${REPORT}"

run_module() {
    local MODULE=$1
    local NAME=$2
    local TESTS=$3
    local CFG="/tmp/cr_${NAME}.toml"
    local DB="/tmp/cr_${NAME}.sqlite"

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "${REPORT}"
    echo "🧬 ${NAME}" | tee -a "${REPORT}"

    cat > "${CFG}" << EOF
[cosmic-ray]
module-path = "${MODULE}"
timeout = 300.0
excluded-modules = []
test-command = "${VENV}/python -m pytest ${TESTS} -x -q --tb=no --no-header"

[cosmic-ray.distributor]
name = "local"
EOF

    rm -f "${DB}"

    echo "  Init..." | tee -a "${REPORT}"
    "${VENV}/cosmic-ray" init "${CFG}" "${DB}" 2>&1 | tail -1
    if [ $? -ne 0 ]; then
        echo "  ❌ Init failed" | tee -a "${REPORT}"
        return
    fi

    echo "  Baseline..." | tee -a "${REPORT}"
    "${VENV}/cosmic-ray" baseline "${CFG}" 2>&1 | tail -1
    if [ $? -ne 0 ]; then
        echo "  ❌ Baseline failed" | tee -a "${REPORT}"
        return
    fi

    echo "  ✅ Baseline OK — running mutations..." | tee -a "${REPORT}"
    "${VENV}/cosmic-ray" exec "${CFG}" "${DB}" 2>&1

    RESULT=$("${VENV}/cr-report" "${DB}" 2>&1 | tail -3)
    echo "${RESULT}" | tee -a "${REPORT}"
    echo "" | tee -a "${REPORT}"
}

# Module 1: prompt_sanitizer
run_module \
    "ai_engine/modules/prompt_sanitizer.py" \
    "prompt_sanitizer" \
    "tests/test_boundary_mutations.py tests/test_hypothesis_properties.py tests/test_ai_modules.py"

# Module 2: title_utils
run_module \
    "ai_engine/modules/title_utils.py" \
    "title_utils" \
    "tests/test_boundary_mutations.py tests/test_hypothesis_properties.py tests/test_ai_modules.py tests/test_ai_engine_core.py tests/test_ai_main.py tests/test_main_critical.py"

# Module 3: duplicate_checker
run_module \
    "ai_engine/modules/duplicate_checker.py" \
    "duplicate_checker" \
    "tests/test_boundary_mutations.py tests/test_hypothesis_properties.py tests/test_specs_enricher.py tests/test_zone_bd.py"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "${REPORT}"
echo "📊 DONE! Full report: ${REPORT}" | tee -a "${REPORT}"
echo "scoring.py skipped (Cosmic Ray lambda crash)" | tee -a "${REPORT}"

# Cleanup temp configs
rm -f /tmp/cr_*.toml /tmp/cr_*.sqlite
