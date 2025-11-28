"""
Tests for RocqVerifier and AsyncRocqVerifier.

Before running tests:
1. Start the petanque server: pet-server -p 8765
2. Run tests: pytest tests/test_rocq_verifier.py -v

To skip tests if server is not running:
    pytest tests/test_rocq_verifier.py -v -m "not requires_server"
"""

import pytest
import asyncio
from src.inference.RocqVerifier import RocqVerifier
from src.inference.AsyncRocqVerifier import AsyncRocqVerifier

# Mark all tests as requiring petanque server
pytestmark = pytest.mark.requires_server

# Test proofs
VALID_PROOF = """
Lemma test_add_comm : forall n m : nat, n + m = m + n.
Proof.
  intros n m.
  induction n.
  - simpl. rewrite <- plus_n_O. reflexivity.
  - simpl. rewrite IHn. rewrite plus_n_Sm. reflexivity.
Qed.
"""

INVALID_PROOF = """
Lemma test_false : forall n : nat, n = n + 1.
Proof.
  intros n.
  reflexivity.
Qed.
"""

PROOF_WITH_ADMIT = """
Lemma test_with_admit : forall n : nat, n + 0 = n.
Proof.
  admit.
Admitted.
"""


@pytest.fixture
def sync_verifier():
    """Fixture for synchronous RocqVerifier."""
    verifier = RocqVerifier(host="127.0.0.1", port=8765)
    yield verifier
    # Cleanup is handled by __del__


@pytest.fixture
async def async_verifier():
    """Fixture for asynchronous AsyncRocqVerifier."""
    async with AsyncRocqVerifier(
        host="127.0.0.1", port=8765, max_concurrent_requests=5
    ) as verifier:
        yield verifier


class TestRocqVerifier:
    """Tests for synchronous RocqVerifier."""

    def test_valid_proof(self, sync_verifier):
        """Test verification of a valid proof."""
        result = sync_verifier.verify_proof(VALID_PROOF)
        assert result is True

    def test_valid_proof_with_error_message(self, sync_verifier):
        """Test valid proof with error message option."""
        result, error = sync_verifier.verify_proof(
            VALID_PROOF, return_error_message=True
        )
        assert result is True
        assert error is None

    def test_invalid_proof(self, sync_verifier):
        """Test verification of an invalid proof."""
        result = sync_verifier.verify_proof(INVALID_PROOF)
        assert result is False

    def test_invalid_proof_with_error_message(self, sync_verifier):
        """Test invalid proof with error message."""
        result, error = sync_verifier.verify_proof(
            INVALID_PROOF, return_error_message=True
        )
        assert result is False
        assert error is not None
        assert "Proof:" in error

    def test_proof_with_admit_rejected(self, sync_verifier):
        """Test that proof with admit is rejected when is_sorry_ok=False."""
        result = sync_verifier.verify_proof(PROOF_WITH_ADMIT, is_sorry_ok=False)
        assert result is False

    def test_proof_with_admit_accepted(self, sync_verifier):
        """Test that proof with admit is accepted when is_sorry_ok=True."""
        result = sync_verifier.verify_proof(PROOF_WITH_ADMIT, is_sorry_ok=True)
        assert result is True

    def test_batch_verify_proofs(self, sync_verifier):
        """Test batch verification."""
        proofs = [VALID_PROOF, INVALID_PROOF, PROOF_WITH_ADMIT]
        results = sync_verifier.batch_verify_proofs(proofs, is_sorry_ok=False)
        assert results == [True, False, False]

    def test_batch_verify_with_error_messages(self, sync_verifier):
        """Test batch verification with error messages."""
        proofs = [VALID_PROOF, INVALID_PROOF, PROOF_WITH_ADMIT]
        results, errors = sync_verifier.batch_verify_proofs(
            proofs, return_error_messages=True, is_sorry_ok=False
        )
        assert results == [True, False, False]
        assert errors[0] is None
        assert errors[1] is not None
        assert errors[2] is not None


class TestAsyncRocqVerifier:
    """Tests for asynchronous AsyncRocqVerifier."""

    @pytest.mark.asyncio
    async def test_valid_proof(self, async_verifier):
        """Test verification of a valid proof."""
        result = await async_verifier.verify_proof(VALID_PROOF)
        assert result is True

    @pytest.mark.asyncio
    async def test_valid_proof_with_error_message(self, async_verifier):
        """Test valid proof with error message option."""
        result, error = await async_verifier.verify_proof(
            VALID_PROOF, return_error_message=True
        )
        assert result is True
        assert error is None

    @pytest.mark.asyncio
    async def test_invalid_proof(self, async_verifier):
        """Test verification of an invalid proof."""
        result = await async_verifier.verify_proof(INVALID_PROOF)
        assert result is False

    @pytest.mark.asyncio
    async def test_invalid_proof_with_error_message(self, async_verifier):
        """Test invalid proof with error message."""
        result, error = await async_verifier.verify_proof(
            INVALID_PROOF, return_error_message=True
        )
        assert result is False
        assert error is not None
        assert "Proof:" in error

    @pytest.mark.asyncio
    async def test_proof_with_admit_rejected(self, async_verifier):
        """Test that proof with admit is rejected when is_sorry_ok=False."""
        result = await async_verifier.verify_proof(PROOF_WITH_ADMIT, is_sorry_ok=False)
        assert result is False

    @pytest.mark.asyncio
    async def test_proof_with_admit_accepted(self, async_verifier):
        """Test that proof with admit is accepted when is_sorry_ok=True."""
        result = await async_verifier.verify_proof(PROOF_WITH_ADMIT, is_sorry_ok=True)
        assert result is True

    @pytest.mark.asyncio
    async def test_batch_verify_proofs(self, async_verifier):
        """Test batch verification."""
        proofs = [VALID_PROOF, INVALID_PROOF, PROOF_WITH_ADMIT]
        results = await async_verifier.batch_verify_proofs(proofs, is_sorry_ok=False)
        assert results == [True, False, False]

    @pytest.mark.asyncio
    async def test_batch_verify_with_error_messages(self, async_verifier):
        """Test batch verification with error messages."""
        proofs = [VALID_PROOF, INVALID_PROOF, PROOF_WITH_ADMIT]
        results, errors = await async_verifier.batch_verify_proofs(
            proofs, return_error_messages=True, is_sorry_ok=False
        )
        assert results == [True, False, False]
        assert errors[0] is None
        assert errors[1] is not None
        assert errors[2] is not None

    @pytest.mark.asyncio
    async def test_concurrent_verification(self, async_verifier):
        """Test concurrent verification of multiple proofs."""
        proofs = [VALID_PROOF] * 5
        results = await async_verifier.batch_verify_proofs(proofs)
        assert all(r is True for r in results)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager behavior."""
        async with AsyncRocqVerifier(host="127.0.0.1", port=8765) as verifier:
            result = await verifier.verify_proof(VALID_PROOF)
            assert result is True
        # Verifier should be closed after exiting context
        assert verifier._closed is True


class TestAPICompatibility:
    """Test that both verifiers have compatible APIs."""

    def test_sync_api_signature(self):
        """Test that sync verifier has expected method signatures."""
        verifier = RocqVerifier(host="127.0.0.1", port=8765)
        assert hasattr(verifier, "verify_proof")
        assert hasattr(verifier, "batch_verify_proofs")

    def test_async_api_signature(self):
        """Test that async verifier has expected method signatures."""
        verifier = AsyncRocqVerifier(host="127.0.0.1", port=8765)
        assert hasattr(verifier, "verify_proof")
        assert hasattr(verifier, "batch_verify_proofs")
        assert hasattr(verifier, "close")
        assert hasattr(verifier, "__aenter__")
        assert hasattr(verifier, "__aexit__")
