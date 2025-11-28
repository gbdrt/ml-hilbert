#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#
"""Proof utilities for Rocq (Coq) proofs using pytanque."""

from pytanque.client import PetanqueError
from pytanque.protocol import State


def read_client_response(states, exceptions):
    """
    Parse pytanque responses for multiple proof attempts.

    Unlike Lean's kimina which returns structured response objects,
    pytanque raises exceptions for errors and returns State objects for success.

    Args:
        states: List of State objects or None (for successful/failed proofs)
        exceptions: List of Exception objects or None (errors that occurred)

    Returns:
        List of dicts with keys 'is_correct_with_sorry' and 'is_correct_no_sorry'
    """
    parsed_answers = []

    for state, exception in zip(states, exceptions):
        # If there was an exception, the proof failed
        if exception is not None:
            parsed_answers.append({
                "is_correct_with_sorry": False,
                "is_correct_no_sorry": False
            })
            continue

        # If state is None (timeout or other issue), proof failed
        if state is None:
            parsed_answers.append({
                "is_correct_with_sorry": False,
                "is_correct_no_sorry": False
            })
            continue

        # Check if proof is finished (no remaining goals)
        if not state.proof_finished:
            parsed_answers.append({
                "is_correct_with_sorry": False,
                "is_correct_no_sorry": False
            })
            continue

        # Check feedback for admits (equivalent to sorry in Lean)
        # In Coq, admits show up in feedback or need to be detected in the proof text
        has_admit = False
        if state.feedback:
            for _, message in state.feedback:
                # Check if feedback mentions 'admitted' (case-insensitive)
                if 'admitted' in message.lower() or 'admit' in message.lower():
                    has_admit = True
                    break

        parsed_answers.append({
            "is_correct_with_sorry": True,
            "is_correct_no_sorry": not has_admit
        })

    return parsed_answers


def extract_all_error_messages(states, exceptions, proofs):
    """
    Extract error messages from pytanque responses.

    Args:
        states: List of State objects or None
        exceptions: List of Exception objects or None
        proofs: List of proof strings

    Returns:
        List of formatted error messages
    """
    all_error_messages = []

    for state, exception, proof in zip(states, exceptions, proofs):
        if exception is not None:
            # Extract error message from PetanqueError
            if isinstance(exception, PetanqueError):
                # PetanqueError args are (error_code, error_message)
                error_code, error_message = exception.args
                error_text = f"Proof:\n{proof}\n\nError (code {error_code}):\n{error_message}"
            elif isinstance(exception, TimeoutError):
                error_text = f"Proof:\n{proof}\n\nError: Timed out"
            else:
                error_text = f"Proof:\n{proof}\n\nError: {str(exception)}"
            all_error_messages.append(error_text)
        elif state is None:
            # Timeout or other failure
            all_error_messages.append(f"Proof:\n{proof}\n\nError: Timed out or failed to execute")
        elif not state.proof_finished:
            # Proof incomplete (has remaining goals)
            error_text = f"Proof:\n{proof}\n\nError: Proof incomplete - goals remaining"
            all_error_messages.append(error_text)
        else:
            # No error
            all_error_messages.append("")

    return all_error_messages


def split_header_body(proof: str) -> tuple[str, str]:
    """
    Splits `proof` into header and body for Coq proofs.

    - header: consecutive `Require Import ...` lines at the beginning
    - body: rest of the proof

    For Coq standard library imports, we consolidate multiple specific imports
    into broader imports where appropriate (e.g., multiple Arith imports -> Require Import Arith).

    Args:
        proof (str): The proof code to split

    Returns:
        tuple[str, str]: The header and body of the proof
    """
    proof = proof.strip()
    lines = proof.splitlines()
    header_lines = []
    proof_idx = 0

    # Track if we've seen specific library imports
    stdlib_imports = set()  # e.g., 'Arith', 'List', 'Bool'

    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if line_stripped.startswith("Require Import") or line_stripped.startswith("Require Export"):
            # Extract what's being imported
            parts = line_stripped.split()
            if len(parts) >= 3:
                # parts[0] = "Require", parts[1] = "Import"/"Export", parts[2:] = library names
                for lib in parts[2:]:
                    # Remove trailing dots
                    lib = lib.rstrip('.')
                    # Track top-level standard library imports (Arith.Plus -> Arith)
                    if '.' in lib:
                        stdlib_imports.add(lib.split('.')[0])
                    else:
                        stdlib_imports.add(lib)
            header_lines.append(line_stripped)
            proof_idx = i + 1
        elif line_stripped.startswith("From") and "Require Import" in line_stripped:
            # Handle "From Foo Require Import Bar" style
            header_lines.append(line_stripped)
            proof_idx = i + 1
        else:
            break

    # Consolidate stdlib imports if needed
    if stdlib_imports:
        # Keep the original header lines for now (more conservative approach)
        header = "\n".join(header_lines).strip()
    else:
        header = "\n".join(header_lines).strip()

    body = "\n".join(lines[proof_idx:]).strip()

    return header, body
