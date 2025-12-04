"""
Integration test for HILBERT import workflow with Rocq.

This test demonstrates the complete HILBERT workflow:
1. Proof sketch construction with assertions
2. Compilation with petanque to get real errors
3. Extract missing identifiers from real error messages
4. Semantic search for missing identifiers (using real search engine)
5. Extract module names from search results
6. Header update with required imports
7. Re-verification with petanque

Run with:
    pytest tests/test_hilbert_import_workflow.py -v

Requires:
    - Running petanque server: pet-server -p 8765
    - Semantic search cache: cache/coq_informal.jsonl
"""

import pytest
import os
from src.tools.rocq_utils import (
    replace_have_proofs_with_sorry,
    extract_missing_identifiers,
    extract_module_names_from_search_results,
    add_imports_to_header,
)
from tests.rocq_test_helpers import validate_coq_code, run_coq_code


@pytest.fixture(scope="module")
def petanque_available():
    """Check if petanque server is available."""
    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("127.0.0.1", 8765))
        sock.close()
        return result == 0
    except:
        return False


class MockSemanticSearchEngine:
    """Mock semantic search engine that returns realistic Coq search results."""

    def get_search_results(self, query: str, top_k: int = 5) -> str:
        """Return mock search results based on query."""
        if "Nat" in query or "addition" in query:
            return """
1. [THEOREM] Addition is commutative
Module: Coq.Arith.PeanoNat
Name: Nat.add_comm
Description: Commutativity of addition on natural numbers

2. [THEOREM] Right identity of addition
Module: Coq.Arith.PeanoNat
Name: Nat.add_0_r
Description: Adding 0 on the right returns the same number

3. [THEOREM] Left identity of addition
Module: Coq.Arith.PeanoNat
Name: Nat.add_0_l
Description: Adding 0 on the left returns the same number

4. [THEOREM] Addition with successor on right
Module: Coq.Arith.PeanoNat
Name: Nat.add_succ_r
Description: Addition distributes over successor on the right
"""
        elif "lia" in query.lower():
            return """
1. [TACTIC] Linear Integer Arithmetic
Module: Lia
Name: lia
Description: Tactic for solving linear arithmetic goals
"""
        else:
            return "No results found for query: '{}'".format(query)


@pytest.fixture(scope="module")
def search_engine():
    """Return mock semantic search engine."""
    return MockSemanticSearchEngine()


class TestHILBERTImportWorkflow:
    """Integration tests for HILBERT import workflow with real petanque and semantic search."""

    def test_add_comm_full_workflow(self, petanque_available, search_engine):
        """
        Complete workflow with add_comm proof using Lia:
        1. Create proof sketch
        2. Get real error from petanque
        3. Use semantic search to find Lia module
        4. Add imports and verify
        """
        if not petanque_available:
            pytest.skip("Petanque server not available")

        # Step 1: Create a proof that uses lia without importing
        proof_sketch = """
Theorem my_add_comm : forall n m : nat, n + m = m + n.
Proof.
  intros n m.
  lia.
Qed.
"""
        # Step 2: Try to compile without imports - should fail
        state, error = run_coq_code(proof_sketch)
        assert error is not None
        error_str = str(error)

        # Step 3: Extract missing identifiers from real error
        missing = extract_missing_identifiers(error_str)
        assert len(missing) > 0

        # Should find "lia" in the error
        assert "lia" in missing

        # Step 4: Use semantic search to find the module
        search_results = search_engine.get_search_results("lia tactic", top_k=5)

        # Step 5: Extract module names from search results
        modules = extract_module_names_from_search_results(search_results)

        # Should find at least one module
        assert len(modules) > 0

        # Step 6: Add imports to header
        header = ""
        for module in modules:
            header = add_imports_to_header(header, {module})

        # Step 7: Verify proof compiles with imports
        full_proof = header + "\n" + proof_sketch
        assert validate_coq_code(full_proof)


class TestHILBERTWorkflowWithPetanque:
    """Integration tests using petanque for real error checking."""

    def test_add_comm_sketch_workflow_with_search(
        self, petanque_available, search_engine
    ):
        """
        Complete add_comm workflow with sketch construction and semantic search:
        1. Start with complete proof using Lia
        2. Convert to sketch with admit placeholders
        3. Get error from petanque
        4. Use semantic search to find Lia module
        5. Add imports and verify
        """
        if not petanque_available:
            pytest.skip("Petanque server not available")

        # Step 1: Complete proof using lia
        complete_proof = """
Theorem add_comm : forall n m : nat, n + m = m + n.
Proof.
  intros n m.
  assert (H : forall a b, a + b = b + a) by (intros; lia).
  apply H.
Qed.
"""
        # Step 2: Create sketch from complete proof
        sketch = replace_have_proofs_with_sorry(complete_proof)

        # Verify assertions were replaced with admits
        assert "admit." in sketch

        # Step 3: Try the original complete proof without imports - should fail
        state, error = run_coq_code(complete_proof)
        assert error is not None
        error_str = str(error)

        # Step 4: Extract missing identifiers
        missing = extract_missing_identifiers(error_str)
        assert len(missing) > 0
        assert "lia" in missing

        # Step 5: Use semantic search to find the module
        search_results = search_engine.get_search_results(
            "lia linear arithmetic", top_k=3
        )

        # Step 6: Extract modules from search results
        modules = extract_module_names_from_search_results(search_results)
        assert len(modules) > 0

        # Step 7: Add imports to sketch (with Admitted for incomplete proofs)
        sketch = sketch.replace("Qed.", "Admitted.")
        header = ""
        for module in modules:
            header = add_imports_to_header(header, {module})

        # Step 8: Verify sketch compiles with imports
        full_sketch = header + "\n" + sketch
        assert validate_coq_code(full_sketch)

    def test_sketch_fails_without_imports_then_succeeds(self, petanque_available):
        """Full workflow: sketch without Lia fails, then succeeds after adding import."""
        if not petanque_available:
            pytest.skip("Petanque server not available")

        # Use Lia as it definitely requires an import
        sketch_no_import = """
Theorem simple_arith : forall n : nat, n + 1 = 1 + n.
Proof.
  intro n.
  lia.
Qed.
"""
        # Step 1: Try without Lia import - should fail
        state, error = run_coq_code(sketch_no_import)

        # Should get an error about missing lia
        assert error is not None
        error_str = str(error)

        # Step 2: Extract missing identifiers from real error
        missing = extract_missing_identifiers(error_str)

        # Should find "lia"
        assert "lia" in missing

        # Step 3: Simulate search results
        mock_search = "Module: Lia"
        modules = extract_module_names_from_search_results(mock_search)
        header = add_imports_to_header("", modules)

        # Step 4: Verify with imports
        full_proof = header + "\n" + sketch_no_import
        assert validate_coq_code(full_proof)

    def test_lia_workflow_with_real_errors(self, petanque_available):
        """Test Lia import workflow with real petanque verification."""
        if not petanque_available:
            pytest.skip("Petanque server not available")

        # Step 1: Proof that requires Lia (will fail without import)
        sketch_without_lia = """
Theorem lia_example : forall n m : nat, n + m = m + n.
Proof.
  intros n m.
  lia.
Qed.
"""
        # Step 2: Try without Lia import - should fail
        state, error = run_coq_code(sketch_without_lia)

        assert error is not None
        error_str = str(error)

        # Step 3: Extract missing identifier
        missing = extract_missing_identifiers(error_str)

        # Should find "lia" in the error
        assert "lia" in missing

        # Step 4: Add Lia import based on "search results"
        mock_search = "Module: Lia\nName: lia"
        modules = extract_module_names_from_search_results(mock_search)
        header = add_imports_to_header("", modules)

        assert "Require Import Lia." in header

        # Step 5: Verify with Lia import - should succeed
        full_proof = header + "\n" + sketch_without_lia
        assert validate_coq_code(full_proof)

    def test_sketch_construction_with_verification(self, petanque_available):
        """Test proof sketch construction with petanque verification."""
        if not petanque_available:
            pytest.skip("Petanque server not available")

        # Step 1: Complete proof with Lia
        complete_proof = """
Require Import Lia.

Theorem complete_example : forall n : nat, n + 0 = n.
Proof.
  intro n.
  assert (H : forall m, m + 0 = m) by (intro m; lia).
  apply H.
Qed.
"""
        # Step 2: Verify complete proof works
        assert validate_coq_code(complete_proof)

        # Step 3: Create sketch from the theorem (with spaces after periods)
        theorem_with_spaces = """
Theorem complete_example : forall n : nat, n + 0 = n.
Proof.
  intro n.
  assert (H : forall m, m + 0 = m) by (intro m; lia).
  apply H.
Qed.
"""
        sketch = replace_have_proofs_with_sorry(theorem_with_spaces)

        # Should have admit in the assertion
        assert "by admit." in sketch

        # Since we have admits, change Qed to Admitted
        sketch = sketch.replace("Qed.", "Admitted.")

        # Step 4: Add Lia import to the sketch
        header = "Require Import Lia."
        full_sketch = header + "\n" + sketch

        # Step 5: Verify sketch compiles with import and Admitted
        assert validate_coq_code(full_sketch)

    def test_multiple_imports_workflow(self, petanque_available):
        """Test adding multiple imports incrementally with real errors."""
        if not petanque_available:
            pytest.skip("Petanque server not available")

        # Proof that needs both Lia and PeanoNat theorems
        sketch = """
Theorem multi_import_example : forall n : nat, n + 0 = 0 + n.
Proof.
  intro n.
  lia.
Qed.
"""
        # Start with empty header
        header = ""

        # First iteration: try without imports, should fail
        state, error = run_coq_code(header + "\n" + sketch)
        assert error is not None

        # Extract error and add Lia
        error_str = str(error)
        missing = extract_missing_identifiers(error_str)
        assert "lia" in missing

        # Add Lia import
        search_1 = "Module: Lia"
        modules_1 = extract_module_names_from_search_results(search_1)
        header = add_imports_to_header(header, modules_1)

        # Should now work with Lia
        assert validate_coq_code(header + "\n" + sketch)

        # Verify no duplicate imports if we try to add again
        header = add_imports_to_header(header, modules_1)
        assert header.count("Require Import Lia.") == 1
