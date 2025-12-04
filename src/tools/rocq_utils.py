#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#
"""
Rocq/Rocq utility functions for theorem extraction, parsing, and manipulation.

This module provides Rocq equivalents of the Lean utility functions.
"""
import re
import logging
from typing import List, Tuple, Optional, Set

logger = logging.getLogger(__name__)


def extract_theorem_name(theorem_text: str) -> str:
    """
    Extract the name of a theorem/lemma from its declaration in Rocq.

    Args:
        theorem_text: String containing a Rocq theorem/lemma declaration

    Returns:
        The name of the theorem/lemma

    Raises:
        ValueError: If no theorem keyword found

    Example:
        >>> extract_theorem_name("Theorem foo : 1 = 1.")
        'foo'
        >>> extract_theorem_name("Lemma bar (n : nat) : n + 0 = n.")
        'bar'
    """
    # Remove comments if any
    text = _remove_comments(theorem_text)

    # Find theorem keywords (Theorem, Lemma, Example, etc.)
    keywords = [
        "Theorem",
        "Lemma",
        "Example",
        "Fact",
        "Remark",
        "Corollary",
        "Proposition",
    ]
    keyword_pattern = r"\b(" + "|".join(keywords) + r")\s+(\w+)"

    match = re.search(keyword_pattern, text)
    if not match:
        raise ValueError(
            f"No theorem keyword found in theorem declaration. Text: {theorem_text[:100]}"
        )

    return match.group(2)


def extract_theorem_signature(text: str) -> Optional[str]:
    """
    Extract the theorem statement from Rocq code (everything before the proof).
    Captures everything from theorem keyword up to 'Proof.' or first tactic.

    Args:
        text: Rocq code containing a theorem

    Returns:
        The theorem signature or None if extraction fails

    Example:
        >>> extract_theorem_signature("Theorem foo : 1 = 1. Proof. reflexivity. Qed.")
        'Theorem foo : 1 = 1'
    """
    # Remove imports and non-theorem lines
    new_text = _remove_all_nontheorem_lines(text)
    if not new_text:
        return None

    # Remove comments
    new_text = _remove_comments(new_text)

    # Extract up to 'Proof.' or before first tactic
    # Match theorem declaration up to the period that ends the type
    match = re.match(
        r"((?:Theorem|Lemma|Example|Fact|Remark|Corollary|Proposition)\s+\w+[^.]+)",
        new_text,
    )
    if match:
        return match.group(1).strip()

    return None


def check_theorem_signature_match(theorem1: str, theorem2: str) -> bool:
    """
    Check if two theorems have matching signatures, accounting for formatting discrepancies.

    Args:
        theorem1: First theorem statement
        theorem2: Second theorem statement

    Returns:
        True if signatures match, False otherwise
    """
    # Extract signatures from both theorems
    sig1 = extract_theorem_signature(theorem1)
    sig2 = extract_theorem_signature(theorem2)

    # If either signature couldn't be extracted, they don't match
    if sig1 is None or sig2 is None:
        return False

    # Normalize both signatures
    norm_sig1 = normalize_signature(sig1)
    norm_sig2 = normalize_signature(sig2)

    logger.info("SIGNATURE ONE: %s", norm_sig1)
    logger.info("SIGNATURE TWO: %s", norm_sig2)

    # Compare normalized signatures
    return norm_sig1 == norm_sig2


def normalize_signature(signature: str) -> str:
    """
    Normalize a Rocq signature by removing extra whitespace and standardizing formatting.

    Args:
        signature: The signature to normalize

    Returns:
        The normalized signature
    """
    if not signature:
        return ""

    # Replace multiple whitespaces with single space
    normalized = re.sub(r"\s+", " ", signature.strip())

    # Remove spaces around common operators
    operators = [
        (r"\s*=\s*", "="),
        (r"\s*<>\s*", "<>"),
        (r"\s*->\s*", "->"),
        (r"\s*<-\s*", "<-"),
        (r"\s*<->\s*", "<->"),
        (r"\s*\+\s*", "+"),
        (r"\s*-\s*", "-"),
        (r"\s*\*\s*", "*"),
        (r"\s*/\s*", "/"),
    ]

    for pattern, replacement in operators:
        normalized = re.sub(pattern, replacement, normalized)

    # Remove spaces around parentheses, brackets, and braces
    brackets = [
        (r"\s*\(\s*", "("),
        (r"\s*\)\s*", ")"),
        (r"\s*\[\s*", "["),
        (r"\s*\]\s*", "]"),
        (r"\s*\{\s*", "{"),
        (r"\s*\}\s*", "}"),
    ]

    for pattern, replacement in brackets:
        normalized = re.sub(pattern, replacement, normalized)

    # Remove spaces around punctuation
    punctuation = [
        (r"\s*,\s*", ","),
        (r"\s*:\s*", ":"),
        (r"\s*;\s*", ";"),
        (r"\s*\.\s*", "."),
    ]

    for pattern, replacement in punctuation:
        normalized = re.sub(pattern, replacement, normalized)

    # Clean up any remaining multiple spaces
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized.strip()


def extract_proof_body_from_theorem(theorem_text: str) -> str:
    """
    Extract the proof body from a theorem, removing the theorem declaration.

    Args:
        theorem_text: String containing a complete Rocq theorem with proof

    Returns:
        String containing just the proof body (tactics between Proof. and Qed.)

    Example:
        >>> extract_proof_body_from_theorem("Theorem foo : 1 = 1. Proof. reflexivity. Qed.")
        'reflexivity.'
    """
    # Remove comments
    text = _remove_comments(theorem_text)

    # Match proof body between 'Proof.' and 'Qed.'/'Defined'/'Admitted'
    match = re.search(r"Proof\.(.*?)(?:Qed|Defined|Admitted)", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Alternative: inline proof with ':='
    if ":=" in text:
        parts = text.split(":=", 1)
        if len(parts) == 2:
            proof = parts[1].strip()
            # Remove trailing period
            if proof.endswith("."):
                proof = proof[:-1].strip()
            return proof

    return ""


def _remove_comments(text: str) -> str:
    """
    Remove comments from Rocq code while preserving structure.

    Args:
        text: Rocq code with comments

    Returns:
        Rocq code with comments removed
    """
    if not text:
        return text if text is not None else ""

    # Rocq uses (* ... *) for comments
    result = ""
    i = 0
    while i < len(text):
        # Check for start of block comment
        if i < len(text) - 1 and text[i : i + 2] == "(*":
            # Find the end of block comment (handle nested comments)
            depth = 1
            i += 2
            while i < len(text) - 1 and depth > 0:
                if text[i : i + 2] == "(*":
                    depth += 1
                    i += 2
                elif text[i : i + 2] == "*)":
                    depth -= 1
                    i += 2
                else:
                    i += 1
            continue
        else:
            result += text[i]
            i += 1

    return result


def replace_have_proofs_with_sorry(theorem_text: str) -> str:
    """
    Replace the proofs of intermediate assertions (assert/have) with admit.

    In Rocq, intermediate assertions can be introduced with:
    - assert (H : P) by tactic.
    - assert (H : P). { proof }
    - have H : P by tactic. (SSReflect)

    This function replaces the proofs with 'admit'.

    Args:
        theorem_text: String containing Rocq code with assertions

    Returns:
        String with assertion proofs replaced by admit
    """
    if not theorem_text or not theorem_text.strip():
        return theorem_text

    # For now, implement a simple version that replaces assert proofs
    # This is a simplified version - full implementation would need proper parsing

    # Pattern: assert (H : P) by tactic. -> assert (H : P) by admit.
    # Matches period followed by space OR period at end of string
    result = re.sub(r"(assert\s*\([^)]+\)\s*by\s+).+?\.(\s|$)", r"\1admit.\2", theorem_text)

    # Pattern: have H : P by tactic. -> have H : P by admit.
    # Matches period followed by space OR period at end of string
    result = re.sub(r"(have\s+\w+\s*:\s*[^.]+\s+by\s+).+?\.(\s|$)", r"\1admit.\2", result)

    return result


def extract_missing_identifiers(error_message: str) -> List[str]:
    """
    Extract all missing identifiers from a Rocq error message.

    Looks for patterns like:
    - "The reference <id> was not found"
    - "Unbound value <id>"
    - "Error: <id> not found"

    Args:
        error_message: The error message from Rocq

    Returns:
        List of missing identifier names found in the error message
    """
    if not error_message:
        return []

    identifiers = []

    # Pattern for "The reference <id> was not found"
    ref_pattern = r"The reference\s+(\w+)\s+was not found"
    matches = re.findall(ref_pattern, error_message, re.IGNORECASE)
    identifiers.extend(matches)

    # Pattern for "Unbound value <id>"
    unbound_pattern = r"Unbound value\s+(\w+)"
    matches = re.findall(unbound_pattern, error_message, re.IGNORECASE)
    identifiers.extend(matches)

    # Pattern for "Error: <id> not found"
    not_found_pattern = r"Error:\s+(\w+)\s+not found"
    matches = re.findall(not_found_pattern, error_message, re.IGNORECASE)
    identifiers.extend(matches)

    return identifiers


def extract_module_names_from_search_results(search_results: str) -> Set[str]:
    """
    Extract unique module names from formatted search results.

    Args:
        search_results: Formatted search results string from SemanticSearchEngine

    Returns:
        Set of unique module names (e.g., {"Coq.Arith.PeanoNat", "Coq.Lists.List"})

    Example:
        >>> results = "Module: Coq.Arith.PeanoNat\\nName: Nat.add_0_r"
        >>> extract_module_names_from_search_results(results)
        {'Coq.Arith.PeanoNat'}
    """
    if not search_results:
        return set()

    module_names = set()

    # Pattern to match "Module: <module_name>" lines
    module_pattern = r"Module:\s*(.+)"
    matches = re.findall(module_pattern, search_results)

    for match in matches:
        module_name = match.strip()
        if module_name:
            module_names.add(module_name)

    return module_names


def generate_require_imports(module_names: Set[str]) -> str:
    """
    Generate Require Import statements from a set of module names.

    Args:
        module_names: Set of module names (e.g., {"Coq.Arith.PeanoNat", "Coq.Lists.List"})

    Returns:
        String containing Require Import statements, one per line

    Example:
        >>> modules = {"Coq.Arith.PeanoNat", "Coq.Lists.List"}
        >>> print(generate_require_imports(modules))
        Require Import Coq.Arith.PeanoNat.
        Require Import Coq.Lists.List.
    """
    if not module_names:
        return ""

    # Sort for deterministic output
    sorted_modules = sorted(module_names)

    import_statements = []
    for module in sorted_modules:
        import_statements.append(f"Require Import {module}.")

    return "\n".join(import_statements)


def extract_existing_imports(header: str) -> Set[str]:
    """
    Extract existing Require Import statements from a header.

    Args:
        header: The header section of a Coq file

    Returns:
        Set of module names that are already imported

    Example:
        >>> header = "Require Import Coq.Arith.PeanoNat.\\nRequire Import Coq.Lists.List."
        >>> extract_existing_imports(header)
        {'Coq.Arith.PeanoNat', 'Coq.Lists.List'}
    """
    if not header:
        return set()

    existing_imports = set()

    # Pattern to match "Require Import <module>." statements
    # Captures module names that can contain dots (e.g., Coq.Arith.PeanoNat)
    import_pattern = r"Require\s+Import\s+([A-Za-z0-9_.]+)\."
    matches = re.findall(import_pattern, header)

    for match in matches:
        existing_imports.add(match.strip())

    return existing_imports


def add_imports_to_header(header: str, new_modules: Set[str]) -> str:
    """
    Add new Require Import statements to a header, avoiding duplicates.

    Args:
        header: Existing header section
        new_modules: Set of new module names to import

    Returns:
        Updated header with new import statements added

    Example:
        >>> header = "Require Import Coq.Arith.PeanoNat."
        >>> new_modules = {"Coq.Lists.List", "Coq.Arith.PeanoNat"}
        >>> print(add_imports_to_header(header, new_modules))
        Require Import Coq.Arith.PeanoNat.
        Require Import Coq.Lists.List.
    """
    if not new_modules:
        return header

    # Extract existing imports
    existing_imports = extract_existing_imports(header)

    # Filter out modules that are already imported
    modules_to_add = new_modules - existing_imports

    if not modules_to_add:
        return header

    # Generate new import statements
    new_import_statements = generate_require_imports(modules_to_add)

    # Add to header
    if header.strip():
        return header.rstrip() + "\n" + new_import_statements
    else:
        return new_import_statements


def extract_all_have_names(text_string: str) -> List[str]:
    """
    Extract the names of all have/assert statements in the given Rocq proof.

    Args:
        text_string: The Rocq code to search within

    Returns:
        List of have/assert statement names
    """
    # Remove comments
    text_string = _remove_comments(text_string)

    have_names = []

    # Pattern for SSReflect 'have' statements: have H : ...
    have_pattern = r"\bhave\s+(\w+)\s*:"
    matches = re.findall(have_pattern, text_string)
    have_names.extend(matches)

    # Pattern for 'assert' statements: assert (H : ...)
    assert_pattern = r"\bassert\s*\(\s*(\w+)\s*:"
    matches = re.findall(assert_pattern, text_string)
    have_names.extend(matches)

    return have_names


def _check_for_sorries(proof: str) -> bool:
    """
    Check if a Rocq proof contains 'admit' or 'Admitted'.

    Args:
        proof: The Rocq proof to check

    Returns:
        True if proof contains admit/Admitted, False otherwise
    """
    # Clean up imports and comments
    no_imports_proof = remove_import_statements(proof)
    no_comments_proof = _remove_comments(no_imports_proof)

    # Check if the proof contains admit or Admitted
    if re.search(r"\b(admit|Admitted)\b", no_comments_proof, re.IGNORECASE):
        return True
    else:
        return False


def _extract_all_theorems_from_string(text: str) -> List[str]:
    """
    Extract all theorem blocks from a string containing one or more Rocq theorems.

    Args:
        text: String containing one or more theorem blocks

    Returns:
        List of strings, each containing a complete theorem block

    Example:
        >>> text = '''Theorem foo : 1 = 1. Proof. reflexivity. Qed.
        ... Lemma bar : 2 = 2. Proof. reflexivity. Qed.'''
        >>> extract_all_theorems_from_string(text)
        ['Theorem foo : 1 = 1. Proof. reflexivity. Qed.', 'Lemma bar : 2 = 2. Proof. reflexivity. Qed.']
    """
    if not text or not text.strip():
        return []

    text_no_imports = remove_import_statements(text)
    text_no_comments = _remove_comments(text_no_imports)

    # Find all theorem-like keywords
    keywords = r"\b(?:Theorem|Lemma|Example|Fact|Remark|Corollary|Proposition)\b"
    match_iterator = re.finditer(keywords, text_no_comments)

    positions = [match.start() for match in match_iterator] + [len(text_no_comments)]

    theorems = []

    for idx, position in enumerate(positions[:-1]):
        extracted_theorem = text_no_comments[position : positions[idx + 1]]
        extracted_theorem = extracted_theorem.strip()
        theorems.append(extracted_theorem)

    return theorems


def remove_import_statements(text: str) -> str:
    """
    Remove all import/require statements and return only theorem content.

    Args:
        text: Rocq code with import statements

    Returns:
        Rocq code without import statements
    """
    return _remove_all_nontheorem_lines(text)


def remove_import_lines(text: str) -> str:
    """
    Remove import/require lines from Rocq code.

    Args:
        text: Rocq code

    Returns:
        Rocq code without import lines
    """
    lines = text.split("\n")
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("Require"):
            continue
        if stripped.startswith("Import"):
            continue
        if stripped.startswith("From"):
            continue
        if stripped.startswith("Set "):
            continue
        if stripped.startswith("Unset "):
            continue
        new_lines.append(line)

    return "\n".join(new_lines)


def _remove_all_nontheorem_lines(text: str) -> Optional[str]:
    """
    Remove all lines before the first theorem declaration.

    Args:
        text: Rocq code

    Returns:
        Rocq code starting from first theorem, or None if no theorem found
    """
    all_lines = text.split("\n")

    keywords = [
        "Theorem",
        "Lemma",
        "Example",
        "Fact",
        "Remark",
        "Corollary",
        "Proposition",
    ]

    for idx, line in enumerate(all_lines):
        stripped = line.strip()
        for keyword in keywords:
            if stripped.startswith(keyword + " "):
                to_include = all_lines[idx:]
                new_text = "\n".join(to_include).strip()
                return new_text

    logger.info(100 * "?")
    logger.info("Text does not contain theorem lines\n%s", text)
    logger.info(100 * "?")
    return None
