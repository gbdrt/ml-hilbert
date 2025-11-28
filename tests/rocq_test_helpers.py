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
