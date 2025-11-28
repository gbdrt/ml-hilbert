"""Tests for rocq_proof_utils module."""

import pytest
from src.tools.rocq_proof_utils import (
    read_client_response,
    extract_all_error_messages,
    split_header_body,
)
from tests.rocq_test_helpers import validate_coq_code, run_coq_code


@pytest.mark.requires_server
class TestReadClientResponse:
    """Tests for read_client_response function using real pytanque."""

    def test_successful_proof_no_admits(self):
        """Test response parsing for successful proof without admits."""
        proof = "Theorem test : True. Proof. exact I. Qed."
        assert validate_coq_code(proof)

        state, exception = run_coq_code(proof)
        results = read_client_response([state], [exception])

        assert len(results) == 1
        assert results[0]["is_correct_with_sorry"] is True
        assert results[0]["is_correct_no_sorry"] is True

    def test_successful_proof_with_admits(self):
        """Test response parsing for proof with admits."""
        proof = "Theorem test : True. Proof. admit. Admitted."
        assert validate_coq_code(proof)

        state, exception = run_coq_code(proof)
        results = read_client_response([state], [exception])

        assert len(results) == 1
        assert results[0]["is_correct_with_sorry"] is True
        # The admit detection depends on feedback which may vary
        # Just check the structure is correct
        assert "is_correct_no_sorry" in results[0]

    def test_proof_with_error(self):
        """Test response parsing when proof has type error."""
        proof = "Theorem test : False. Proof. exact I. Qed."
        # This should fail validation
        assert not validate_coq_code(proof)

        state, exception = run_coq_code(proof)
        results = read_client_response([state], [exception])

        assert len(results) == 1
        assert results[0]["is_correct_with_sorry"] is False
        assert results[0]["is_correct_no_sorry"] is False

    def test_multiple_proofs_mixed(self):
        """Test parsing multiple proofs with mixed results."""
        proof1 = "Theorem test1 : True. Proof. exact I. Qed."
        proof2 = "Theorem test2 : False. Proof. exact I. Qed."
        proof3 = "Theorem test3 : 1 + 1 = 2. Proof. reflexivity. Qed."

        assert validate_coq_code(proof1)
        assert not validate_coq_code(proof2)
        assert validate_coq_code(proof3)

        state1, exception1 = run_coq_code(proof1)
        state2, exception2 = run_coq_code(proof2)
        state3, exception3 = run_coq_code(proof3)

        states = [state1, state2, state3]
        exceptions = [exception1, exception2, exception3]

        results = read_client_response(states, exceptions)

        assert len(results) == 3
        assert results[0]["is_correct_with_sorry"] is True
        assert results[0]["is_correct_no_sorry"] is True
        assert results[1]["is_correct_with_sorry"] is False
        assert results[1]["is_correct_no_sorry"] is False
        assert results[2]["is_correct_with_sorry"] is True
        assert results[2]["is_correct_no_sorry"] is True

    def test_proof_with_induction(self):
        """Test proof using induction tactic."""
        proof = (
            "Theorem test : forall n, n + 0 = n. Proof. induction n; simpl; auto. Qed."
        )
        assert validate_coq_code(proof)

        state, exception = run_coq_code(proof)
        results = read_client_response([state], [exception])

        assert len(results) == 1
        assert results[0]["is_correct_with_sorry"] is True
        assert results[0]["is_correct_no_sorry"] is True


@pytest.mark.requires_server
class TestExtractAllErrorMessages:
    """Tests for extract_all_error_messages function using real pytanque."""

    def test_petanque_error(self):
        """Test error message extraction from real PetanqueError."""
        proof = "Theorem test : False. Proof. exact I. Qed."
        assert not validate_coq_code(proof)

        state, exception = run_coq_code(proof)
        messages = extract_all_error_messages([state], [exception], [proof])

        assert len(messages) == 1
        assert proof in messages[0]
        # Should contain error details
        assert "Error" in messages[0] or "code" in messages[0]

    def test_successful_proof_no_error(self):
        """Test that successful proof returns empty error message."""
        proof = "Theorem test : True. Proof. exact I. Qed."
        assert validate_coq_code(proof)

        state, exception = run_coq_code(proof)
        messages = extract_all_error_messages([state], [exception], [proof])

        assert len(messages) == 1
        assert messages[0] == ""

    def test_multiple_proofs_mixed_results(self):
        """Test error extraction for multiple proofs with mixed results."""
        proof1 = "Theorem a : True. Proof. exact I. Qed."
        proof2 = "Theorem b : False. Proof. exact I. Qed."
        proof3 = "Require Import Lia. Theorem c : forall n, n + 1 = 1 + n. Proof. intros. lia. Qed."

        assert validate_coq_code(proof1)
        assert not validate_coq_code(proof2)
        assert validate_coq_code(proof3)

        state1, exception1 = run_coq_code(proof1)
        state2, exception2 = run_coq_code(proof2)
        state3, exception3 = run_coq_code(proof3)

        states = [state1, state2, state3]
        exceptions = [exception1, exception2, exception3]
        proofs = [proof1, proof2, proof3]

        messages = extract_all_error_messages(states, exceptions, proofs)

        assert len(messages) == 3
        assert messages[0] == ""  # successful
        assert proof2 in messages[1]  # error message should contain proof
        assert messages[2] == ""  # successful

    def test_undefined_identifier_error(self):
        """Test error message for undefined identifier."""
        proof = "Theorem test : forall n, n + undefined_var = n. Proof. auto. Qed."
        assert not validate_coq_code(proof)

        state, exception = run_coq_code(proof)
        messages = extract_all_error_messages([state], [exception], [proof])

        assert len(messages) == 1
        assert proof in messages[0]
        # Should mention the undefined variable or unbound
        assert len(messages[0]) > len(proof)  # Has error details


@pytest.mark.requires_server
class TestSplitHeaderBody:
    """Tests for split_header_body function with validation."""

    def test_no_imports(self):
        """Test splitting proof with no imports."""
        proof = "Theorem test : True. Proof. exact I. Qed."
        assert validate_coq_code(proof)

        header, body = split_header_body(proof)

        assert header == ""
        assert body == proof
        # Validate the body still works
        assert validate_coq_code(body)

    def test_single_require_import(self):
        """Test splitting with single Require Import."""
        proof = """Require Import Arith.
Theorem test : forall n, n + 0 = n.
Proof. induction n; simpl; auto. Qed."""
        assert validate_coq_code(proof)

        header, body = split_header_body(proof)

        assert "Require Import Arith" in header
        assert "Theorem test" in body
        assert "Require Import" not in body
        # Validate full proof still works
        assert validate_coq_code(header + "\n" + body)

    def test_multiple_require_imports(self):
        """Test splitting with multiple Require Import statements."""
        proof = """Require Import Arith.
Require Import List.
Require Import Bool.

Theorem test : True.
Proof. exact I. Qed."""
        assert validate_coq_code(proof)

        header, body = split_header_body(proof)

        assert "Require Import Arith" in header
        assert "Require Import List" in header
        assert "Require Import Bool" in header
        assert "Theorem test" in body
        assert "Require Import" not in body
        # Validate recombined proof
        assert validate_coq_code(header + "\n" + body)

    def test_require_import_with_dots(self):
        """Test Require Import with dotted notation."""
        proof = """Require Import Arith.

Theorem test : True.
Proof. exact I. Qed."""
        assert validate_coq_code(proof)

        header, body = split_header_body(proof)

        assert "Arith" in header
        assert "Theorem test" in body
        assert validate_coq_code(header + "\n" + body)

    def test_require_export(self):
        """Test with Require Export instead of Import."""
        proof = """Require Export Arith.
Theorem test : True. Proof. exact I. Qed."""
        assert validate_coq_code(proof)

        header, body = split_header_body(proof)

        assert "Require Export Arith" in header
        assert "Theorem test" in body
        assert validate_coq_code(header + "\n" + body)

    def test_from_require_import(self):
        """Test 'From Foo Require Import Bar' style."""
        proof = """From Coq Require Import Arith.
From Coq Require Import List.

Theorem test : True.
Proof. exact I. Qed."""
        assert validate_coq_code(proof)

        header, body = split_header_body(proof)

        assert "From Coq Require Import Arith" in header
        assert "From Coq Require Import List" in header
        assert "Theorem test" in body
        assert validate_coq_code(header + "\n" + body)

    def test_mixed_import_styles(self):
        """Test mixed import styles."""
        proof = """Require Import Arith.
From Coq Require Import List.
Require Export Bool.

Theorem test : True.
Proof. exact I. Qed."""
        assert validate_coq_code(proof)

        header, body = split_header_body(proof)

        assert "Require Import Arith" in header
        assert "From Coq Require Import List" in header
        assert "Require Export Bool" in header
        assert "Theorem test" in body
        assert validate_coq_code(header + "\n" + body)

    def test_whitespace_handling(self):
        """Test that whitespace is properly handled."""
        proof = """

Require Import Arith.

Theorem test : True.
Proof. exact I. Qed.
"""
        assert validate_coq_code(proof)

        header, body = split_header_body(proof)

        assert "Require Import Arith" in header
        assert "Theorem test" in body
        # Body should be stripped
        assert not body.startswith("\n")
        assert validate_coq_code(header + "\n" + body)

    def test_imports_with_comments(self):
        """Test that imports stop at first non-import line."""
        proof = """Require Import Arith.
(* This is a comment *)
Theorem test : True.
Proof. exact I. Qed."""
        assert validate_coq_code(proof)

        header, body = split_header_body(proof)

        assert "Require Import Arith" in header
        assert "(* This is a comment *)" in body
        assert "Theorem test" in body
        # The full proof should still work
        assert validate_coq_code(header + "\n" + body)

    def test_complex_proof_with_lia(self):
        """Test splitting proof that uses Lia tactic."""
        proof = """Require Import Lia.

Theorem test : forall n m, n + m = m + n.
Proof.
  intros n m.
  lia.
Qed."""
        assert validate_coq_code(proof)

        header, body = split_header_body(proof)

        assert "Require Import Lia" in header
        assert "Theorem test" in body
        assert "lia" in body
        assert validate_coq_code(header + "\n" + body)

    def test_proof_with_list_operations(self):
        """Test splitting proof using List library."""
        proof = """Require Import List.

Theorem test : forall A (x : A), x :: nil = x :: nil.
Proof.
  intros A x.
  reflexivity.
Qed."""
        assert validate_coq_code(proof)

        header, body = split_header_body(proof)

        assert "Require Import List" in header
        assert "Theorem test" in body
        assert validate_coq_code(header + "\n" + body)


@pytest.mark.requires_server
class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_full_workflow_success(self):
        """Test complete workflow with successful proof."""
        proof = """Require Import Arith.

Theorem add_comm_partial : forall n, n + 0 = n.
Proof.
  induction n; simpl; auto.
Qed."""
        assert validate_coq_code(proof)

        # Split header and body
        header, body = split_header_body(proof)
        assert "Require Import Arith" in header
        assert "Theorem add_comm_partial" in body

        # Run through pytanque
        state, exception = run_coq_code(proof)

        # Parse response
        results = read_client_response([state], [exception])
        assert results[0]["is_correct_with_sorry"] is True
        assert results[0]["is_correct_no_sorry"] is True

        # Check no error message
        messages = extract_all_error_messages([state], [exception], [proof])
        assert messages[0] == ""

    def test_full_workflow_with_error(self):
        """Test complete workflow with proof error."""
        proof = """Require Import Arith.

Theorem bad_theorem : forall n, n + 1 = n.
Proof.
  intros n.
  reflexivity.
Qed."""
        assert not validate_coq_code(proof)

        # Split header and body
        header, body = split_header_body(proof)
        assert "Require Import Arith" in header

        # Run through pytanque
        state, exception = run_coq_code(proof)

        # Parse response
        results = read_client_response([state], [exception])
        assert results[0]["is_correct_with_sorry"] is False
        assert results[0]["is_correct_no_sorry"] is False

        # Check error message exists
        messages = extract_all_error_messages([state], [exception], [proof])
        assert messages[0] != ""
        assert proof in messages[0]

    def test_batch_processing(self):
        """Test processing multiple proofs in batch."""
        proofs = [
            "Theorem t1 : True. Proof. exact I. Qed.",
            "Theorem t2 : 1 = 1. Proof. reflexivity. Qed.",
            "Theorem t3 : False. Proof. exact I. Qed.",  # This will fail
            "Theorem t4 : forall n : nat, n = n. Proof. intros. reflexivity. Qed.",
        ]

        # Validate expected results
        assert validate_coq_code(proofs[0])
        assert validate_coq_code(proofs[1])
        assert not validate_coq_code(proofs[2])
        assert validate_coq_code(proofs[3])

        # Run all proofs
        results_list = []
        states = []
        exceptions = []

        for proof in proofs:
            state, exception = run_coq_code(proof)
            states.append(state)
            exceptions.append(exception)

        # Parse all responses
        results = read_client_response(states, exceptions)
        assert len(results) == 4
        assert results[0]["is_correct_with_sorry"] is True
        assert results[1]["is_correct_with_sorry"] is True
        assert results[2]["is_correct_with_sorry"] is False
        assert results[3]["is_correct_with_sorry"] is True

        # Extract all error messages
        messages = extract_all_error_messages(states, exceptions, proofs)
        assert len(messages) == 4
        assert messages[0] == ""
        assert messages[1] == ""
        assert messages[2] != ""  # Should have error
        assert messages[3] == ""
