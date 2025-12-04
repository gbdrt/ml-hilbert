"""Shared test helpers for Rocq/Coq testing."""

import tempfile
import os
from pytanque import Pytanque
from pytanque.protocol import State


def validate_coq_code(code: str) -> bool:
    """
    Validate Coq code by running it through pytanque.

    Args:
        code: Coq code to validate

    Returns:
        True if code is valid, False otherwise
    """
    try:
        fd, temp_file = tempfile.mkstemp(suffix='.v', text=True)
        os.close(fd)
        try:
            with Pytanque("127.0.0.1", 8765) as client:
                state = client.get_root_state(temp_file)
                final_state = client.run(state, code, verbose=False, timeout=5)
                return True
        finally:
            os.unlink(temp_file)
    except Exception as e:
        print(f"Validation failed: {e}")
        return False


def run_coq_code(code: str):
    """
    Run Coq code through pytanque and return (state, exception).

    Args:
        code: Coq code to run

    Returns:
        Tuple of (State or None, Exception or None)
    """
    fd, temp_file = tempfile.mkstemp(suffix='.v', text=True)
    os.close(fd)
    try:
        with Pytanque("127.0.0.1", 8765) as client:
            try:
                state = client.get_root_state(temp_file)
                final_state = client.run(state, code, verbose=False, timeout=5)
                return (final_state, None)
            except Exception as e:
                return (None, e)
    finally:
        os.unlink(temp_file)


def validate_proof_sketch(sketch: str) -> tuple[bool, str]:
    """
    Validate a proof sketch by checking:
    1. It compiles without errors
    2. No goals remain before Admitted.

    This removes Admitted./Qed. from the end and checks that all goals
    are resolved by the proof tactics before the terminator.

    Args:
        sketch: Coq proof sketch code

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        fd, temp_file = tempfile.mkstemp(suffix='.v', text=True)
        os.close(fd)
        try:
            with Pytanque("127.0.0.1", 8765) as client:
                state = client.get_root_state(temp_file)

                # Remove Admitted. or Qed. from the end to check goals before closure
                sketch_without_end = sketch.strip()
                if sketch_without_end.endswith("Admitted."):
                    sketch_without_end = sketch_without_end[:-len("Admitted.")].rstrip()
                elif sketch_without_end.endswith("Qed."):
                    sketch_without_end = sketch_without_end[:-len("Qed.")].rstrip()

                # Run the proof without the terminator
                final_state = client.run(state, sketch_without_end, verbose=False, timeout=5)

                # Check if there are remaining goals
                goals = client.goals(final_state, pretty=False)

                if len(goals) > 0:
                    return (False, f"Sketch has {len(goals)} remaining goals before Admitted")

                return (True, "")
        finally:
            os.unlink(temp_file)
    except Exception as e:
        return (False, f"Compilation error: {e}")


def validate_complete_proof(proof: str) -> tuple[bool, str]:
    """
    Validate a complete proof (should end with Qed and have no remaining goals).

    Args:
        proof: Coq proof code

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        fd, temp_file = tempfile.mkstemp(suffix='.v', text=True)
        os.close(fd)
        try:
            with Pytanque("127.0.0.1", 8765) as client:
                state = client.get_root_state(temp_file)
                final_state = client.run(state, proof, verbose=False, timeout=5)

                # Check if there are remaining goals
                goals = client.goals(final_state, pretty=False)

                if len(goals) > 0:
                    return (False, f"Complete proof has {len(goals)} remaining goals")

                return (True, "")
        finally:
            os.unlink(temp_file)
    except Exception as e:
        return (False, f"Compilation error: {e}")
