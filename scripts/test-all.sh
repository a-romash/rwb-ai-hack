#!/bin/sh
# All Python suites of the platform. Needs PostgreSQL (POSTGRES_HOST etc.) for backend tests.
# Used locally and by the platform CI: sh scripts/test-all.sh
set -eu
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/backend:$PWD"

echo "== root tests"
python -m unittest discover -s tests

echo "== backend tests"
(cd backend && alembic upgrade head && python -m unittest discover -s tests)

echo "== stages, gates, contracts"
python -m unittest \
  stages.analysis.tests.test_analysis_stage stages.analysis.tests.test_inputs \
  stages.spec.tests.test_contracts stages.spec.tests.test_eval stages.spec.tests.test_spec_stage \
  gates.tests.test_gates stages.scaffold.tests.test_generate stages.develop.tests.test_ladder \
  contracts.tests.test_hooks_pack

echo "== product smoke"
(cd templates/product/infra && python -m unittest test_smoke)
