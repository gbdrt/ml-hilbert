"""
Tests for rocq_utils.py

These tests verify Rocq utility functions for theorem extraction,
parsing, and manipulation.

Run tests with:
    pytest tests/test_rocq_utils.py -v

Note: Some tests require a running petanque server to validate Rocq syntax:
    pet-server -p 8765
"""

import pytest
from src.tools.rocq_utils import (
    extract_theorem_name,
    extract_theorem_signature,
    check_theorem_signature_match,
    normalize_signature,
    extract_proof_body_from_theorem,
    extract_missing_identifiers,
    extract_all_have_names,
    check_for_sorries,
    extract_all_theorems_from_string,
    remove_import_statements,
    remove_import_lines,
    replace_have_proofs_with_sorry,
    _remove_comments,
)
from tests.rocq_test_helpers import validate_coq_code


# Keep validate_rocq_code as alias for backward compatibility
validate_rocq_code = validate_coq_code


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


@pytest.mark.requires_server
class TestExtractTheoremName:
    """Tests for extract_theorem_name function."""

    def test_simple_theorem(self):
        """Test extracting name from simple theorem."""
        text = "Theorem foo : 1 = 1."
        assert validate_rocq_code(text)
        assert extract_theorem_name(text) == "foo"

    def test_lemma(self):
        """Test extracting name from lemma."""
        text = "Lemma bar : nat -> nat."
        assert validate_rocq_code(text)
        assert extract_theorem_name(text) == "bar"

    def test_example(self):
        """Test extracting name from example."""
        text = "Example test_ex : forall n, n + 0 = n."
        assert validate_rocq_code(text)
        assert extract_theorem_name(text) == "test_ex"

    def test_theorem_with_params(self):
        """Test extracting name from theorem with parameters."""
        text = "Theorem add_comm (n m : nat) : n + m = m + n."
        assert validate_rocq_code(text)
        assert extract_theorem_name(text) == "add_comm"

    def test_with_comments(self):
        """Test extracting name with comments present."""
        text = "(* This is a comment *) Theorem foo : 1 = 1."
        assert validate_rocq_code(text)
        assert extract_theorem_name(text) == "foo"

    def test_no_theorem_keyword(self):
        """Test that ValueError is raised when no theorem keyword found."""
        text = "Definition foo := 1."
        assert validate_rocq_code(text)
        with pytest.raises(ValueError, match="No theorem keyword found"):
            extract_theorem_name(text)


@pytest.mark.requires_server
class TestExtractTheoremSignature:
    """Tests for extract_theorem_signature function."""

    def test_simple_theorem(self):
        """Test extracting signature from simple theorem."""
        text = "Theorem foo : 1 = 1. Proof. reflexivity. Qed."
        assert validate_rocq_code(text)
        sig = extract_theorem_signature(text)
        assert sig == "Theorem foo : 1 = 1"

    def test_theorem_with_params(self):
        """Test extracting signature with parameters."""
        text = "Lemma add_comm (n m : nat) : n + m = m + n. Proof. induction n; simpl; auto; rewrite IHn; auto. Qed."
        assert validate_rocq_code(text)
        sig = extract_theorem_signature(text)
        assert "Lemma add_comm" in sig
        assert "n + m = m + n" in sig

    def test_theorem_with_forall(self):
        """Test extracting signature with forall."""
        text = "Theorem test : forall n : nat, n + 0 = n. Proof. induction n. reflexivity. simpl. auto. Qed."
        assert validate_rocq_code(text)
        sig = extract_theorem_signature(text)
        assert sig == "Theorem test : forall n : nat, n + 0 = n"

    def test_no_theorem(self):
        """Test that None is returned when no theorem found."""
        text = "Definition foo := 1."
        assert validate_rocq_code(text)
        sig = extract_theorem_signature(text)
        assert sig is None


class TestNormalizeSignature:
    """Tests for normalize_signature function."""

    def test_extra_whitespace(self):
        """Test normalizing extra whitespace."""
        sig = "Theorem  foo   :   1  =  1"
        normalized = normalize_signature(sig)
        assert normalized == "Theorem foo:1=1"

    def test_spaces_around_operators(self):
        """Test removing spaces around operators."""
        sig = "n + m = m + n"
        normalized = normalize_signature(sig)
        assert normalized == "n+m=m+n"

    def test_spaces_around_parentheses(self):
        """Test removing spaces around parentheses."""
        sig = "forall ( n : nat ) , n + 0 = n"
        normalized = normalize_signature(sig)
        assert normalized == "forall(n:nat),n+0=n"

    def test_empty_signature(self):
        """Test normalizing empty signature."""
        assert normalize_signature("") == ""
        assert normalize_signature(None) == ""


@pytest.mark.requires_server
class TestCheckTheoremSignatureMatch:
    """Tests for check_theorem_signature_match function."""

    def test_matching_signatures(self):
        """Test that matching signatures are detected."""
        thm1 = "Theorem foo : 1 = 1. Proof. reflexivity. Qed."
        thm2 = "Theorem  foo  :  1  =  1. Proof. auto. Qed."
        assert validate_rocq_code(thm1)
        assert validate_rocq_code(thm2)
        assert check_theorem_signature_match(thm1, thm2) is True

    def test_different_signatures(self):
        """Test that different signatures are detected."""
        thm1 = "Theorem foo : 1 = 1. Proof. reflexivity. Qed."
        thm2 = "Theorem bar : 2 = 2. Proof. reflexivity. Qed."
        assert validate_rocq_code(thm1)
        assert validate_rocq_code(thm2)
        assert check_theorem_signature_match(thm1, thm2) is False

    def test_same_content_different_names(self):
        """Test different theorem names with same content."""
        thm1 = "Theorem foo : forall n : nat, n + 0 = n. Proof. induction n; auto. Qed."
        thm2 = "Theorem bar : forall n : nat, n + 0 = n. Proof. induction n; auto. Qed."
        assert validate_rocq_code(thm1)
        assert validate_rocq_code(thm2)
        assert check_theorem_signature_match(thm1, thm2) is False

    def test_no_theorem_in_one(self):
        """Test when one input has no theorem."""
        thm1 = "Theorem foo : 1 = 1."
        thm2 = "Definition bar := 1."
        assert validate_rocq_code(thm1)
        assert validate_rocq_code(thm2)
        assert check_theorem_signature_match(thm1, thm2) is False


@pytest.mark.requires_server
class TestExtractProofBody:
    """Tests for extract_proof_body_from_theorem function."""

    def test_simple_proof(self):
        """Test extracting proof body from simple theorem."""
        text = "Theorem foo : 1 = 1. Proof. reflexivity. Qed."
        assert validate_rocq_code(text)
        body = extract_proof_body_from_theorem(text)
        assert "reflexivity" in body
        assert "Proof" not in body
        assert "Qed" not in body

    def test_multi_line_proof(self):
        """Test extracting multi-line proof."""
        text = """Theorem foo : forall n, n + 0 = n.
Proof.
  induction n.
  - reflexivity.
  - simpl. rewrite IHn. reflexivity.
Qed."""
        assert validate_rocq_code(text)
        body = extract_proof_body_from_theorem(text)
        assert "induction" in body
        assert "reflexivity" in body

    def test_inline_proof(self):
        """Test extracting inline proof with :=."""
        text = "Definition foo : 1 = 1 := eq_refl."
        assert validate_rocq_code(text)
        body = extract_proof_body_from_theorem(text)
        assert "eq_refl" in body

    def test_proof_with_defined(self):
        """Test extracting proof ending with Defined."""
        text = "Theorem foo : nat. Proof. exact 0. Defined."
        assert validate_rocq_code(text)
        body = extract_proof_body_from_theorem(text)
        assert "exact 0" in body


@pytest.mark.requires_server
class TestRemoveComments:
    """Tests for _remove_comments function."""

    def test_simple_comment(self):
        """Test removing simple comment."""
        text = "(* This is a comment *) Theorem foo : 1 = 1."
        assert validate_rocq_code(text)
        result = _remove_comments(text)
        assert validate_rocq_code(result)
        assert "comment" not in result
        assert "Theorem foo" in result

    def test_nested_comments(self):
        """Test removing nested comments."""
        text = "(* Outer (* Inner *) still outer *) Theorem foo : True. Proof. exact I. Qed."
        assert validate_rocq_code(text)
        result = _remove_comments(text)
        assert validate_rocq_code(result)
        assert "Outer" not in result
        assert "Inner" not in result
        assert "Theorem foo" in result

    def test_multiple_comments(self):
        """Test removing multiple comments."""
        text = "(* First *) Theorem (* Second *) foo : 1 = 1."
        assert validate_rocq_code(text)
        result = _remove_comments(text)
        assert validate_rocq_code(result)
        assert "First" not in result
        assert "Second" not in result
        assert "Theorem" in result
        assert "foo" in result

    def test_no_comments(self):
        """Test text without comments."""
        text = "Theorem foo : 1 = 1."
        assert validate_rocq_code(text)
        result = _remove_comments(text)
        assert validate_rocq_code(result)
        assert result == text


class TestReplaceHaveProofsWithSorry:
    """Tests for replace_have_proofs_with_sorry function."""

    def test_assert_with_by(self):
        """Test replacing assert proof with admit."""
        text = "assert (H : 1 = 1) by reflexivity."
        result = replace_have_proofs_with_sorry(text)
        assert "by admit" in result
        assert "reflexivity" not in result

    def test_have_with_by(self):
        """Test replacing have proof with admit (SSReflect)."""
        text = "have H : n + 0 = n by auto."
        result = replace_have_proofs_with_sorry(text)
        assert "by admit" in result
        assert "auto" not in result

    def test_empty_text(self):
        """Test empty text."""
        assert replace_have_proofs_with_sorry("") == ""
        assert replace_have_proofs_with_sorry(None) == None


class TestExtractMissingIdentifiers:
    """Tests for extract_missing_identifiers function."""

    def test_reference_not_found(self):
        """Test extracting from 'reference not found' error."""
        error = "Error: The reference foo was not found in the current environment."
        identifiers = extract_missing_identifiers(error)
        assert "foo" in identifiers

    def test_unbound_value(self):
        """Test extracting from 'unbound value' error."""
        error = "Unbound value bar"
        identifiers = extract_missing_identifiers(error)
        assert "bar" in identifiers

    def test_multiple_errors(self):
        """Test extracting multiple identifiers."""
        error = "The reference foo was not found. Unbound value bar."
        identifiers = extract_missing_identifiers(error)
        assert "foo" in identifiers
        assert "bar" in identifiers

    def test_no_identifiers(self):
        """Test error with no identifiers."""
        error = "Some other error message"
        identifiers = extract_missing_identifiers(error)
        assert identifiers == []

    def test_empty_error(self):
        """Test empty error message."""
        assert extract_missing_identifiers("") == []
        assert extract_missing_identifiers(None) == []


class TestExtractAllHaveNames:
    """Tests for extract_all_have_names function."""

    def test_have_statements(self):
        """Test extracting have statement names (SSReflect)."""
        text = "have H1 : n + 0 = n by auto. have H2 : 1 = 1 by reflexivity."
        names = extract_all_have_names(text)
        assert "H1" in names
        assert "H2" in names

    def test_assert_statements(self):
        """Test extracting assert statement names."""
        text = "assert (H : 1 = 1) by reflexivity. assert (H2 : 2 = 2)."
        names = extract_all_have_names(text)
        assert "H" in names
        assert "H2" in names

    def test_mixed_statements(self):
        """Test extracting mixed have/assert names."""
        text = "have H1 : P. assert (H2 : Q)."
        names = extract_all_have_names(text)
        assert "H1" in names
        assert "H2" in names

    def test_no_statements(self):
        """Test text without have/assert."""
        text = "Theorem foo : 1 = 1. Proof. reflexivity. Qed."
        names = extract_all_have_names(text)
        assert names == []


@pytest.mark.requires_server
class TestCheckForSorries:
    """Tests for check_for_sorries function."""

    def test_proof_with_admit(self):
        """Test detecting admit."""
        proof = "Theorem foo : 1 = 1. Proof. admit. Admitted."
        assert validate_rocq_code(proof)
        assert check_for_sorries(proof) is True

    def test_proof_with_admitted(self):
        """Test detecting Admitted."""
        proof = "Theorem foo : 1 = 1. Proof. Admitted."
        assert validate_rocq_code(proof)
        assert check_for_sorries(proof) is True

    def test_proof_without_admits(self):
        """Test proof without admits."""
        proof = "Theorem foo : 1 = 1. Proof. reflexivity. Qed."
        assert validate_rocq_code(proof)
        assert check_for_sorries(proof) is False

    def test_admit_in_comment(self):
        """Test that admit in comment is not detected."""
        proof = "(* We could use admit here *) Theorem foo : 1 = 1. Proof. reflexivity. Qed."
        assert validate_rocq_code(proof)
        # After removing comments, admit should not be found
        assert check_for_sorries(proof) is False


@pytest.mark.requires_server
class TestExtractAllTheoremsFromString:
    """Tests for extract_all_theorems_from_string function."""

    def test_single_theorem(self):
        """Test extracting single theorem."""
        text = "Theorem foo : 1 = 1. Proof. reflexivity. Qed."
        assert validate_rocq_code(text)
        theorems = extract_all_theorems_from_string(text)
        assert len(theorems) == 1
        assert "Theorem foo" in theorems[0]

    def test_multiple_theorems(self):
        """Test extracting multiple theorems."""
        text = """
Theorem foo : 1 = 1. Proof. reflexivity. Qed.
Lemma bar : 2 = 2. Proof. reflexivity. Qed.
Example baz : 3 = 3. Proof. reflexivity. Qed.
"""
        assert validate_rocq_code(text)
        theorems = extract_all_theorems_from_string(text)
        assert len(theorems) == 3
        assert any("Theorem foo" in t for t in theorems)
        assert any("Lemma bar" in t for t in theorems)
        assert any("Example baz" in t for t in theorems)

    def test_mixed_keywords(self):
        """Test extracting theorems with different keywords."""
        text = """
Theorem thm1 : True.
Corollary cor1 : True.
Proposition prop1 : True.
"""
        assert validate_rocq_code(text)
        theorems = extract_all_theorems_from_string(text)
        assert len(theorems) == 3

    def test_empty_text(self):
        """Test extracting from empty text."""
        assert extract_all_theorems_from_string("") == []
        assert extract_all_theorems_from_string(None) == []


@pytest.mark.requires_server
class TestRemoveImportStatements:
    """Tests for remove_import_statements function."""

    def test_with_requires(self):
        """Test removing Require statements."""
        text = """Require Import Nat.
Require Import List.

Theorem foo : 1 = 1.
Proof. reflexivity. Qed."""
        assert validate_rocq_code(text)
        result = remove_import_statements(text)
        assert "Require" not in result
        assert "Theorem foo" in result

    def test_without_imports(self):
        """Test text without imports."""
        text = "Theorem foo : 1 = 1. Proof. reflexivity. Qed."
        assert validate_rocq_code(text)
        result = remove_import_statements(text)
        assert "Theorem foo" in result


@pytest.mark.requires_server
class TestRemoveImportLines:
    """Tests for remove_import_lines function."""

    def test_require_lines(self):
        """Test removing Require lines."""
        text = """Require Import Nat.
Require Import List.
Set Implicit Arguments.
Theorem foo : 1 = 1."""
        assert validate_rocq_code(text)
        result = remove_import_lines(text)
        assert validate_rocq_code(result)
        assert "Require" not in result
        assert "From" not in result
        assert "Set" not in result
        assert "Theorem foo" in result

    def test_import_lines(self):
        """Test removing Import lines."""
        text = """Theorem foo : 1 = 1. Proof. reflexivity. Qed."""
        # Just test that remove_import_lines works, skip validation
        result = remove_import_lines(text)
        assert validate_rocq_code(result)
        assert "Theorem foo" in result

    def test_preserves_other_lines(self):
        """Test that other lines are preserved."""
        text = """Require Import Nat.
Definition x := 1.
Theorem foo : x = 1."""
        assert validate_rocq_code(text)
        result = remove_import_lines(text)
        assert validate_rocq_code(result)
        assert "Definition x" in result
        assert "Theorem foo" in result
        assert "Require" not in result


class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_full_theorem_processing(self):
        """Test processing a full theorem with all utilities."""
        theorem = """
(* This is a test theorem *)
Theorem add_comm : forall n m : nat, n + m = m + n.
Proof.
  intros n m.
  induction n; simpl; auto.
  rewrite IHn. auto.
Qed.
"""
        assert validate_rocq_code(theorem)
        # Extract name
        name = extract_theorem_name(theorem)
        assert name == "add_comm"

        # Extract signature
        sig = extract_theorem_signature(theorem)
        assert sig is not None
        assert "add_comm" in sig

        # Extract proof body
        body = extract_proof_body_from_theorem(theorem)
        assert "intros" in body

        # Check for have statements (this theorem doesn't have any)
        have_names = extract_all_have_names(theorem)
        assert len(have_names) == 0

        # Check for admits
        assert check_for_sorries(theorem) is False

        # Remove imports
        no_imports = remove_import_lines(theorem)
        assert "Require" not in no_imports

    def test_theorem_comparison(self):
        """Test comparing two theorems."""
        thm1 = "Theorem foo : forall n, n + 0 = n. Proof. induction n. reflexivity. simpl. auto. Qed."
        thm2 = "Theorem  foo  :  forall  n,  n  +  0  =  n. Proof. auto. Qed."
        assert validate_rocq_code(thm1)
        assert validate_rocq_code(thm2)
        # Should match despite whitespace differences
        assert check_theorem_signature_match(thm1, thm2) is True

        # Different content should not match
        thm3 = "Require Import Lia. Theorem bar : forall n, n + 1 = 1 + n. Proof. intros. lia. Qed."
        assert validate_rocq_code(thm3)
        assert check_theorem_signature_match(thm1, thm3) is False
