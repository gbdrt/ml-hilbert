"""Tests for Coq-specific string extraction functions in string.py"""

import pytest
from src.tools.string import extract_coq_block, extract_all_coq_blocks
from tests.rocq_test_helpers import validate_coq_code


class TestExtractCoqBlock:
    """Tests for extract_coq_block function."""

    def test_single_coq_block_lowercase(self):
        """Test extracting single Coq block with lowercase tag."""
        response = """
Here's a proof:

```coq
Theorem test : True.
Proof. exact I. Qed.
```

That's the proof.
"""
        result = extract_coq_block(response)
        assert result is not None
        assert "Theorem test : True" in result
        assert "exact I" in result
        assert validate_coq_code(result)

    def test_single_coq_block_uppercase(self):
        """Test extracting single Coq block with uppercase tag."""
        response = """
```COQ
Theorem test : 1 = 1.
Proof. reflexivity. Qed.
```
"""
        result = extract_coq_block(response)
        assert result is not None
        assert "Theorem test" in result
        assert validate_coq_code(result)

    def test_single_rocq_block(self):
        """Test extracting Rocq block."""
        response = """
```rocq
Theorem test : True.
Proof. exact I. Qed.
```
"""
        result = extract_coq_block(response)
        assert result is not None
        assert "Theorem test" in result
        assert validate_coq_code(result)

    def test_mixed_case_coq(self):
        """Test extracting with mixed case Coq tag."""
        response = """
```Coq
Theorem test : True.
Proof. exact I. Qed.
```
"""
        result = extract_coq_block(response)
        assert result is not None
        assert validate_coq_code(result)

    def test_multiple_blocks_returns_last(self):
        """Test that multiple blocks returns the last one."""
        response = """
First block:
```coq
Theorem first : True.
Proof. exact I. Qed.
```

Second block:
```coq
Theorem second : 1 = 1.
Proof. reflexivity. Qed.
```
"""
        result = extract_coq_block(response)
        assert result is not None
        assert "second" in result
        assert "first" not in result
        assert validate_coq_code(result)

    def test_no_coq_block(self):
        """Test response with no Coq block."""
        response = """
This is just text without any code blocks.
"""
        result = extract_coq_block(response)
        assert result is None

    def test_other_code_block_ignored(self):
        """Test that non-Coq code blocks are ignored."""
        response = """
```python
def hello():
    print("hello")
```
"""
        result = extract_coq_block(response)
        assert result is None

    def test_coq_block_with_requires(self):
        """Test extracting Coq block with imports."""
        response = """
```coq
Require Import Arith.

Theorem test : forall n, n + 0 = n.
Proof. induction n; simpl; auto. Qed.
```
"""
        result = extract_coq_block(response)
        assert result is not None
        assert "Require Import Arith" in result
        assert validate_coq_code(result)

    def test_coq_block_with_comments(self):
        """Test extracting Coq block with comments."""
        response = """
```coq
(* This is a test theorem *)
Theorem test : True.
Proof.
  (* Use exact tactic *)
  exact I.
Qed.
```
"""
        result = extract_coq_block(response)
        assert result is not None
        assert "(* This is a test theorem *)" in result
        assert validate_coq_code(result)

    def test_coq_block_multiline(self):
        """Test extracting multi-line Coq proof."""
        response = """
```coq
Theorem add_comm : forall n m, n + m = m + n.
Proof.
  intros n m.
  induction n.
  - simpl. rewrite <- plus_n_O. reflexivity.
  - simpl. rewrite IHn. rewrite plus_n_Sm. reflexivity.
Qed.
```
"""
        result = extract_coq_block(response)
        assert result is not None
        assert "add_comm" in result
        assert "intros n m" in result
        assert "induction n" in result
        # Note: This proof might not validate without proper setup
        # but we can check structure

    def test_empty_coq_block(self):
        """Test extracting empty Coq block."""
        response = """
```coq
```
"""
        result = extract_coq_block(response)
        assert result is not None
        assert result == ""

    def test_coq_block_with_inline_backticks(self):
        """Test Coq block containing inline backticks in comments."""
        response = """
```coq
(* Use the `exact` tactic *)
Theorem test : True.
Proof. exact I. Qed.
```
"""
        result = extract_coq_block(response)
        assert result is not None
        assert "exact" in result
        assert validate_coq_code(result)


class TestExtractAllCoqBlocks:
    """Tests for extract_all_coq_blocks function."""

    def test_single_block(self):
        """Test extracting single Coq block."""
        response = """
```coq
Theorem test : True.
Proof. exact I. Qed.
```
"""
        results = extract_all_coq_blocks(response)
        assert results is not None
        assert len(results) == 1
        assert validate_coq_code(results[0])

    def test_multiple_blocks(self):
        """Test extracting multiple Coq blocks."""
        response = """
First theorem:
```coq
Theorem first : True.
Proof. exact I. Qed.
```

Second theorem:
```coq
Theorem second : 1 = 1.
Proof. reflexivity. Qed.
```

Third theorem:
```coq
Theorem third : 2 = 2.
Proof. reflexivity. Qed.
```
"""
        results = extract_all_coq_blocks(response)
        assert results is not None
        assert len(results) == 3
        assert "first" in results[0]
        assert "second" in results[1]
        assert "third" in results[2]
        # Validate all blocks
        assert all(validate_coq_code(block) for block in results)

    def test_no_blocks(self):
        """Test response with no Coq blocks."""
        response = """
This is just text.
No code here.
"""
        results = extract_all_coq_blocks(response)
        assert results is None

    def test_mixed_case_tags(self):
        """Test extracting blocks with different case tags."""
        response = """
```coq
Theorem a : True. Proof. exact I. Qed.
```

```Coq
Theorem b : True. Proof. exact I. Qed.
```

```COQ
Theorem c : True. Proof. exact I. Qed.
```

```rocq
Theorem d : True. Proof. exact I. Qed.
```
"""
        results = extract_all_coq_blocks(response)
        assert results is not None
        assert len(results) == 4
        assert all(validate_coq_code(block) for block in results)

    def test_blocks_with_text_between(self):
        """Test blocks separated by text."""
        response = """
Here's the first theorem:

```coq
Theorem first : True.
Proof. exact I. Qed.
```

Some explanation here.

And here's the second:

```coq
Theorem second : 1 = 1.
Proof. reflexivity. Qed.
```

Done!
"""
        results = extract_all_coq_blocks(response)
        assert results is not None
        assert len(results) == 2
        assert all(validate_coq_code(block) for block in results)

    def test_blocks_with_other_languages(self):
        """Test that only Coq blocks are extracted."""
        response = """
```python
print("hello")
```

```coq
Theorem test : True.
Proof. exact I. Qed.
```

```javascript
console.log("world")
```

```rocq
Theorem test2 : 1 = 1.
Proof. reflexivity. Qed.
```
"""
        results = extract_all_coq_blocks(response)
        assert results is not None
        assert len(results) == 2
        assert all(validate_coq_code(block) for block in results)

    def test_blocks_with_requires(self):
        """Test extracting blocks with Require statements."""
        response = """
```coq
Require Import Arith.
Theorem test1 : forall n, n + 0 = n.
Proof. induction n; simpl; auto. Qed.
```

```coq
Require Import Lia.
Theorem test2 : forall n m, n + m = m + n.
Proof. intros. lia. Qed.
```
"""
        results = extract_all_coq_blocks(response)
        assert results is not None
        assert len(results) == 2
        assert "Require Import Arith" in results[0]
        assert "Require Import Lia" in results[1]
        assert all(validate_coq_code(block) for block in results)


@pytest.mark.requires_server
class TestCoqBlockIntegration:
    """Integration tests for Coq block extraction with validation."""

    def test_extract_and_validate_complex_proof(self):
        """Test extracting and validating a complex proof."""
        response = """
Here's a proof of addition commutativity for natural numbers:

```coq
Require Import Arith.

Theorem add_comm_partial : forall n, n + 0 = n.
Proof.
  induction n.
  - reflexivity.
  - simpl. rewrite IHn. reflexivity.
Qed.
```

This proof uses induction on natural numbers.
"""
        # Test single block extraction
        block = extract_coq_block(response)
        assert block is not None
        assert validate_coq_code(block)

        # Test all blocks extraction
        blocks = extract_all_coq_blocks(response)
        assert blocks is not None
        assert len(blocks) == 1
        assert validate_coq_code(blocks[0])

    def test_extract_multiple_valid_proofs(self):
        """Test extracting multiple valid proofs."""
        response = """
```coq
Theorem t1 : True.
Proof. exact I. Qed.
```

```coq
Theorem t2 : 1 = 1.
Proof. reflexivity. Qed.
```

```coq
Require Import Lia.
Theorem t3 : forall n, n + 1 = 1 + n.
Proof. intros. lia. Qed.
```
"""
        blocks = extract_all_coq_blocks(response)
        assert blocks is not None
        assert len(blocks) == 3
        # All blocks should be valid
        for i, block in enumerate(blocks):
            assert validate_coq_code(block), f"Block {i} failed validation: {block}"

    def test_extract_with_mixed_valid_invalid(self):
        """Test extracting blocks where some would fail validation."""
        response = """
```coq
Theorem valid : True.
Proof. exact I. Qed.
```

```coq
Theorem invalid : False.
Proof. exact I. Qed.
```
"""
        blocks = extract_all_coq_blocks(response)
        assert blocks is not None
        assert len(blocks) == 2

        # First should be valid
        assert validate_coq_code(blocks[0])

        # Second should be invalid (can't prove False with I)
        assert not validate_coq_code(blocks[1])
