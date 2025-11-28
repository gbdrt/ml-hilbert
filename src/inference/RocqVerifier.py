#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#
import traceback
import re
import logging
import tempfile
import os
from typing import Tuple, Optional
from pytanque import Pytanque, PetanqueError

logger = logging.getLogger(__name__)


class RocqVerifier:
    """
    Synchronous Rocq/Coq proof verifier using pytanque client.

    This class provides proof verification functionality for Coq proofs,
    similar to LeanVerifier but using the pytanque/petanque protocol.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        """
        Initialize RocqVerifier with connection parameters.

        Args:
            host: The hostname of the petanque server (default: "127.0.0.1")
            port: The port number of the petanque server (default: 8765)
        """
        self.client = Pytanque(host, port)
        self.client.connect()
        self._dummy_file = None
        self._create_dummy_file()

    def _create_dummy_file(self):
        """Create a dummy .v file for get_root_state."""
        if not self._dummy_file:
            fd, self._dummy_file = tempfile.mkstemp(suffix=".v", text=True)
            os.close(fd)

    def __del__(self):
        """Clean up resources on deletion."""
        # Close the client
        if hasattr(self, "client"):
            try:
                self.client.close()
            except:
                pass
        # Clean up dummy file
        if (
            hasattr(self, "_dummy_file")
            and self._dummy_file
            and os.path.exists(self._dummy_file)
        ):
            try:
                os.unlink(self._dummy_file)
            except:
                pass

    def verify_proof(
        self,
        proof: str,
        timeout: int = 30,
        return_error_message: bool = False,
        is_sorry_ok: bool = False,
    ) -> bool | Tuple[bool, Optional[str]]:
        """
        Verify a single Coq proof.

        Args:
            proof: The proof to verify (complete Coq code with theorem statement and proof)
            timeout: The timeout for the verification request (default: 30s)
            return_error_message: Whether to return the error message if the proof is invalid (default: False)
            is_sorry_ok: Whether to allow the proof to be valid even if it contains "admit" or "Admitted" (default: False)

        Returns:
            bool: True if the proof is valid, False otherwise
            Tuple[bool, Optional[str]]: If return_error_message=True, returns (is_valid, error_message)
        """
        proof = proof.strip()

        try:
            # Start from empty file
            state = self.client.get_root_state(self._dummy_file)

            # Run the entire proof (theorem declaration + proof)
            final_state = self.client.run(state, proof, verbose=False, timeout=timeout)

            # Check if there are remaining goals
            goals = self.client.goals(final_state, pretty=False)

            is_proof_valid = len(goals) == 0

            # Check for admits/admitted if is_sorry_ok is False
            if not is_sorry_ok and is_proof_valid:
                has_admit = bool(re.search(r"\b(?:admit|Admitted)\b", proof))
                is_proof_valid = not has_admit

            if return_error_message:
                if not is_proof_valid:
                    if goals:
                        goal_strs = [f"Goal: {g.ty}" for g in goals]
                        error_message = (
                            f"Proof:\n{proof}\n\nRemaining goals:\n"
                            + "\n".join(goal_strs)
                        )
                    elif has_admit:
                        error_message = f"Proof:\n{proof}\n\nError: Proof contains admit or Admitted"
                    else:
                        error_message = (
                            f"Proof:\n{proof}\n\nError: Unknown verification failure"
                        )
                    return is_proof_valid, error_message
                return is_proof_valid, None
            return is_proof_valid

        except PetanqueError as e:
            logger.info("Petanque error during verification: %s", e.message)
            if return_error_message:
                return False, f"Proof:\n{proof}\n\nError: {e.message}"
            return False

        except Exception as e:
            logger.info("Proof verification failed with exception")
            traceback.print_exc()
            if return_error_message:
                return False, f"Proof:\n{proof}\n\nError: {str(e)}"
            return False

    def batch_verify_proofs(
        self,
        proofs: list,
        return_error_messages: bool = False,
        timeout: int = 30,
        is_sorry_ok: bool = False,
    ) -> list | Tuple[list, list]:
        """
        Verify a batch of proofs.

        Args:
            proofs: A list of proofs to verify
            return_error_messages: Whether to return the error messages if the proofs are invalid (default: False)
            timeout: The timeout for the verification request (default: 30s)
            is_sorry_ok: Whether to allow proofs that contain "admit" or "Admitted" (default: False)

        Returns:
            list: A list of booleans indicating the validity of each proof
            Tuple[list, list]: If return_error_messages=True, returns (validity_list, error_messages_list)
        """
        verification_results = []
        error_messages = []

        for proof in proofs:
            if return_error_messages:
                is_valid, error_msg = self.verify_proof(
                    proof,
                    timeout=timeout,
                    return_error_message=True,
                    is_sorry_ok=is_sorry_ok,
                )
                verification_results.append(is_valid)
                error_messages.append(error_msg)
            else:
                is_valid = self.verify_proof(
                    proof,
                    timeout=timeout,
                    return_error_message=False,
                    is_sorry_ok=is_sorry_ok,
                )
                verification_results.append(is_valid)

        if return_error_messages:
            return verification_results, error_messages
        else:
            return verification_results
