"""
DMAIC V3 Test Suite - Phase 6: Knowledge Management Tests
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path

from DMAIC_V3.phases.phase6_knowledge import Phase6Knowledge
from DMAIC_V3.config import DMAICConfig
from DMAIC_V3.core.state import StateManager


@pytest.fixture
def temp_workspace():
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def config(temp_workspace):
    cfg = DMAICConfig()
    cfg.paths.workspace_root = temp_workspace
    cfg.paths.output_root = temp_workspace / "output"
    return cfg


@pytest.fixture
def state_manager(config):
    state_dir = config.paths.output_root / "state"
    return StateManager(state_dir)


@pytest.fixture
def phase6(config, state_manager):
    return Phase6Knowledge(config=config, state=state_manager)


@pytest.mark.phase1
@pytest.mark.unit
class TestPhase6Knowledge:

    def test_initialization(self, phase6, config):
        assert phase6.config is not None
        assert phase6.state is not None

    def test_execute_returns_two_tuple(self, phase6):
        result = phase6.execute(iteration=1)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_execute_returns_bool_and_dict(self, phase6):
        success, result = phase6.execute(iteration=1)
        assert isinstance(success, bool)
        assert isinstance(result, dict)

    def test_execute_succeeds(self, phase6):
        success, result = phase6.execute(iteration=1)
        assert success is True

    def test_result_contains_iteration(self, phase6):
        success, result = phase6.execute(iteration=2)
        assert result.get('iteration') == 2

    def test_result_has_maturity_score(self, phase6):
        success, result = phase6.execute(iteration=1)
        assert 'maturity_score' in result
        score = result['maturity_score']
        assert isinstance(score, (int, float))
        assert 0 <= score <= 100

    def test_result_has_canonical_books_count(self, phase6):
        success, result = phase6.execute(iteration=1)
        assert 'canonical_books_count' in result
        assert isinstance(result['canonical_books_count'], int)
        assert result['canonical_books_count'] >= 0

    def test_result_has_timestamp(self, phase6):
        success, result = phase6.execute(iteration=1)
        assert 'start_time' in result
        assert 'end_time' in result

    def test_result_has_hooks_registered(self, phase6):
        success, result = phase6.execute(iteration=1)
        assert 'recursive_hooks_registered' in result
        assert isinstance(result['recursive_hooks_registered'], int)

    def test_multiple_iterations(self, phase6):
        for iteration in [1, 2, 3]:
            success, result = phase6.execute(iteration=iteration)
            assert isinstance(success, bool)
            assert result.get('iteration') == iteration

    def test_knowledge_with_canonical_dir(self, phase6, temp_workspace):
        # Create a mock canonical knowledge dir with a book
        canon_dir = temp_workspace / "CANONICAL_KNOWLEDGE"
        canon_dir.mkdir()
        book_file = canon_dir / "sample_book.json"
        book_file.write_text(json.dumps({"title": "Test Book", "size": 1024}))

        success, result = phase6.execute(iteration=1)
        assert isinstance(success, bool)
        assert isinstance(result, dict)
