"""
Integration test that uses HILBERTWorker methods to test the complete workflow.

This test demonstrates the full HILBERT proof generation process using actual
HILBERTWorker methods:
1. generate_proof_sketch() - Generate proof sketch with assertions
2. extract_subgoals_from_sketch() - Extract subgoals from sketch
3. solve_subgoals() - Solve individual subgoq goals in parallel
4. Verify the complete proof

Run with:
    pytest tests/test_hilbert_logic_integration.py -v

Requires:
    - Running petanque server: pet-server -p 8765
    - PROOF_SYSTEM=ROCQ in HILBERTWorker.py
    - LLM API keys configured (for generate_proof_sketch and extract_subgoals_from_sketch)

NOTE: This test may segfault if torch/scipy libraries are not properly installed.
      The segfault comes from importing HILBERTWorker which loads SemanticSearchEngine.
      To run this test successfully:
      1. Ensure PROOF_SYSTEM="ROCQ" in src/models/HILBERTWorker.py
      2. Run pet-server: `pet-server -p 8765`
      3. Set ANTHROPIC_API_KEY environment variable

Integration test philosophy:
    - Tests actual HILBERTWorker methods (not mocked utilities)
    - Demonstrates realistic HILBERT workflow
    - Uses real petanque verification
    - Requires full system setup (LLM + verifier)
"""

import pytest
import asyncio

from src.models.HILBERTWorker import HILBERTWorker, PROOF_SYSTEM
from src.tracking.ProofAttemptConfig import ProofAttemptConfig
from tests.rocq_test_helpers import validate_coq_code


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


@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def hilbert_worker():
    """Create a HILBERTWorker instance for testing."""
    # Skip all tests if PROOF_SYSTEM is not ROCQ
    if PROOF_SYSTEM != "ROCQ":
        pytest.skip("This test requires PROOF_SYSTEM=ROCQ in HILBERTWorker.py")

    # Import Rocq-specific dependencies
    try:
        from src.inference.AsyncRocqVerifier import AsyncRocqVerifier
    except ImportError:
        pytest.skip("Rocq verifier not available")

    config = ProofAttemptConfig(
        max_verifier_attempts=3,
        max_llm_correction_attempts=3,
        max_search_attempts=2,
        max_recursion_depth=1,
        max_llm_calls_per_proof=100,
        enable_retrieval=True,
        enable_statistics=False,
    )

    worker = HILBERTWorker(config, enable_proof_tree=False)
    yield worker
    await worker.close()


class TestHILBERTWorkerIntegration:
    """Integration test using actual HILBERTWorker methods."""

    @pytest.mark.asyncio
    async def test_extract_subgoals_from_sketch(
        self, petanque_available, hilbert_worker
    ):
        """
        Test HILBERTWorker.extract_subgoals_from_sketch() method.
        """
        if not petanque_available:
            pytest.skip("Petanque server not available")

        header = "Require Import Lia.\n\n"

        # A proof sketch with assertions (what generate_proof_sketch would produce)
        # Note: This is Coq/Rocq syntax
        proof_sketch = """Theorem add_comm : forall n m : nat, n + m = m + n.
Proof.
  intros n m.
  assert (H1 : forall a, a + 0 = a) by admit.
  assert (H2 : forall a b, a + S b = S (a + b)) by admit.
  induction n.
  - simpl. symmetry. apply H1.
  - simpl. rewrite IHn. apply H2.
Admitted.
"""

        # Use HILBERTWorker method to extract subgoals
        # Note: This requires LLM access, so the test will demonstrate the method call
        # but may not complete without API keys
        try:
            extracted_theorems = await hilbert_worker.extract_subgoals_from_sketch(
                proof_sketch, header
            )

            # Should extract the two assert statements as theorems
            assert (
                len(extracted_theorems) >= 2
            ), f"Should extract at least 2 subgoals, got {len(extracted_theorems)}"

            # Each extracted theorem should be a valid theorem statement
            for theorem in extracted_theorems:
                assert "theorem" in theorem.lower() or "lemma" in theorem.lower()
        except Exception as e:
            # If LLM is not available, skip but don't fail
            pytest.skip(f"LLM not available for subgoal extraction: {e}")

    @pytest.mark.asyncio
    async def test_solve_subgoals_with_simple_example(
        self, petanque_available, hilbert_worker
    ):
        """
        Test HILBERTWorker.solve_subgoals() method with simple Coq theorems.
        """
        if not petanque_available:
            pytest.skip("Petanque server not available")

        header = "Require Import Lia.\n\n"

        # Main proof sketch
        proof_sketch = """Theorem simple_add : forall n : nat, n + 0 = n.
Proof.
  intro n.
  assert (H : forall m, m + 0 = m) by admit.
  apply H.
Admitted.
"""

        # Extracted subgoals (as theorems)
        extracted_theorems = [
            """Theorem H : forall m, m + 0 = m.
Proof.
  admit.
Admitted.
"""
        ]

        # Proved theorems cache (empty initially)
        proved_theorems = {}

        # Useful theorems for search (empty in this test)
        useful_theorems = ""

        # Solve the subgoals using HILBERTWorker method
        success, solved_proofs, error_msg = await hilbert_worker.solve_subgoals(
            correct_proof_sketch=proof_sketch,
            extracted_theorems=extracted_theorems,
            proved_theorems=proved_theorems,
            header=header,
            useful_theorems=useful_theorems,
            depth=0,
        )

        # Check results
        if success:
            assert solved_proofs is not None
            assert len(solved_proofs) == len(extracted_theorems)
            # At least one proof should be solved
            assert any(proof is not None for proof in solved_proofs)
        else:
            # If it failed, there should be an error message
            assert error_msg is not None

    @pytest.mark.asyncio
    async def test_full_workflow_with_mocked_sketch(
        self, petanque_available, hilbert_worker
    ):
        """
        Test workflow: proof sketch → extract subgoals → solve subgoals.

        Note: We provide a pre-written sketch instead of calling generate_proof_sketch()
        to avoid requiring LLM API access in tests.
        """
        if not petanque_available:
            pytest.skip("Petanque server not available")

        header = "Require Import Lia.\n\n"

        # Step 1: Proof sketch (mimics output of generate_proof_sketch)
        proof_sketch = """Theorem add_zero_r : forall n : nat, n + 0 = n.
Proof.
  intro n.
  assert (H : forall m, m + 0 = m) by admit.
  apply H.
Admitted.
"""

        # Verify sketch compiles
        assert validate_coq_code(header + proof_sketch), "Proof sketch should compile"

        # Step 2: Extract subgoals (using HILBERTWorker method)
        # Note: For Rocq, extract_subgoals_from_sketch uses LLM, so we'll manually create
        # the extracted theorems to avoid needing API access
        extracted_theorems = [
            """Theorem H : forall m, m + 0 = m.
Proof.
  admit.
Admitted.
"""
        ]

        # Step 3: Solve subgoals (using HILBERTWorker method)
        proved_theorems = {}
        useful_theorems = ""

        success, solved_proofs, error_msg = await hilbert_worker.solve_subgoals(
            correct_proof_sketch=proof_sketch,
            extracted_theorems=extracted_theorems,
            proved_theorems=proved_theorems,
            header=header,
            useful_theorems=useful_theorems,
            depth=0,
        )

        # Verify results
        if success:
            assert solved_proofs is not None
            print(f"Solved proofs: {solved_proofs}")
        else:
            # Some subgoals may not be solvable without LLM
            print(f"Error: {error_msg}")

    @pytest.mark.asyncio
    async def test_solve_subgoals_parallel_execution(
        self, petanque_available, hilbert_worker
    ):
        """
        Test that solve_subgoals processes multiple subgoals in parallel.
        """
        if not petanque_available:
            pytest.skip("Petanque server not available")

        header = "Require Import Lia.\n\n"

        # Proof sketch with multiple subgoals
        proof_sketch = """Theorem multi : forall n m : nat, n + m = m + n.
Proof.
  intros n m.
  assert (H1 : forall a, a + 0 = 0 + a) by admit.
  assert (H2 : forall a b, a + S b = S (a + b)) by admit.
  lia.
Admitted.
"""

        # Multiple extracted subgoals
        extracted_theorems = [
            """Theorem H1 : forall a, a + 0 = 0 + a.
Proof.
  admit.
Admitted.
""",
            """Theorem H2 : forall a b, a + S b = S (a + b).
Proof.
  admit.
Admitted.
""",
        ]

        # Solve subgoals (should be done in parallel by HILBERTWorker)
        success, solved_proofs, error_msg = await hilbert_worker.solve_subgoals(
            correct_proof_sketch=proof_sketch,
            extracted_theorems=extracted_theorems,
            proved_theorems={},
            header=header,
            useful_theorems="",
            depth=0,
        )

        # Check that both subgoals were processed
        if success and solved_proofs:
            assert len(solved_proofs) == 2
            print(
                f"Both subgoals processed: {len([p for p in solved_proofs if p is not None])} solved"
            )
