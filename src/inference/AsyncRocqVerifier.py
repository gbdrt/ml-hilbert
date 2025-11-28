#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#
import asyncio
import traceback
import re
import logging
import tempfile
import os
import threading
from typing import List, Tuple, Optional
from pytanque import Pytanque, PetanqueError

logger = logging.getLogger(__name__)


class AsyncRocqVerifier:
    """
    Async version of RocqVerifier optimized for concurrent verification.

    This class provides async/await patterns for Rocq/Coq proof verification,
    similar to AsyncLeanVerifier but using the pytanque/petanque protocol.

    Since pytanque doesn't have native async support and connections are not thread-safe,
    this implementation uses thread-local storage to create separate client connections
    per thread, with asyncio.to_thread() for async execution.
    """

    def __init__(self,
                 host: str = "127.0.0.1",
                 port: int = 8765,
                 max_concurrent_requests: int = 10):
        """
        Initialize AsyncRocqVerifier with connection parameters.

        Args:
            host: The hostname of the petanque server (default: "127.0.0.1")
            port: The port number of the petanque server (default: 8765)
            max_concurrent_requests: Maximum number of concurrent verification operations (default: 10)
        """
        self.host = host
        self.port = port
        self.max_concurrent = max_concurrent_requests
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)
        self._closed = False
        self._dummy_file = None
        self._thread_local = threading.local()
        self._create_dummy_file()

    def _create_dummy_file(self):
        """Create a dummy .v file for get_root_state."""
        if not self._dummy_file:
            fd, self._dummy_file = tempfile.mkstemp(suffix='.v', text=True)
            os.close(fd)

    def _get_thread_client(self) -> Pytanque:
        """
        Get or create a Pytanque client for the current thread.

        This ensures each thread has its own connection to avoid thread-safety issues.
        """
        if not hasattr(self._thread_local, 'client'):
            self._thread_local.client = Pytanque(self.host, self.port)
            self._thread_local.client.connect()
        return self._thread_local.client

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with proper cleanup."""
        await self.close()

    def _verify_proof_sync(self, proof: str, timeout: int = 30,
                          return_error_message: bool = False,
                          is_sorry_ok: bool = False) -> bool | Tuple[bool, Optional[str]]:
        """
        Synchronous implementation of proof verification.

        This is the actual implementation that will be called in a thread pool.
        Uses thread-local client to ensure thread safety.
        """
        proof = proof.strip()

        try:
            # Get thread-local client
            client = self._get_thread_client()

            # Start from empty file
            state = client.get_root_state(self._dummy_file)

            # Run the entire proof (theorem declaration + proof)
            final_state = client.run(state, proof, verbose=False, timeout=timeout)

            # Check if there are remaining goals
            goals = client.goals(final_state, pretty=False)

            is_proof_valid = len(goals) == 0

            # Check for admits/admitted if is_sorry_ok is False
            if not is_sorry_ok and is_proof_valid:
                has_admit = bool(re.search(r'\b(?:admit|Admitted)\b', proof))
                is_proof_valid = not has_admit

            if return_error_message:
                if not is_proof_valid:
                    if goals:
                        goal_strs = [f"Goal: {g.ty}" for g in goals]
                        error_message = f"Proof:\n{proof}\n\nRemaining goals:\n" + "\n".join(goal_strs)
                    elif has_admit:
                        error_message = f"Proof:\n{proof}\n\nError: Proof contains admit or Admitted"
                    else:
                        error_message = f"Proof:\n{proof}\n\nError: Unknown verification failure"
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

    async def verify_proof(self, proof: str, timeout: int = 30,
                          return_error_message: bool = False,
                          is_sorry_ok: bool = False) -> bool | Tuple[bool, Optional[str]]:
        """
        Verify a single proof asynchronously.

        Args:
            proof: The proof to verify
            timeout: The timeout for the verification request (default: 30s)
            return_error_message: Whether to return the error message if the proof is invalid (default: False)
            is_sorry_ok: Whether to allow the proof to be valid even if it contains "admit" or "Admitted" (default: False)

        Returns:
            bool: True if the proof is valid, False otherwise
            Tuple[bool, Optional[str]]: If return_error_message=True, returns (is_valid, error_message)
        """
        if self._closed:
            raise RuntimeError("AsyncRocqVerifier is closed")

        # Use semaphore to limit concurrent operations
        async with self._semaphore:
            # Run the synchronous verification in a thread pool
            # Each thread will get its own client connection via thread-local storage
            result = await asyncio.to_thread(
                self._verify_proof_sync,
                proof,
                timeout,
                return_error_message,
                is_sorry_ok
            )
            return result

    async def batch_verify_proofs(self, proofs: List[str],
                                 return_error_messages: bool = False,
                                 timeout: int = 30,
                                 is_sorry_ok: bool = False,
                                 show_progress: bool = False) -> List[bool] | Tuple[List[bool], List[str]]:
        """
        Verify a batch of proofs asynchronously with optimized concurrency.

        Args:
            proofs: A list of proofs to verify
            return_error_messages: Whether to return the error messages if the proofs are invalid (default: False)
            timeout: The timeout for the verification request (default: 30s)
            is_sorry_ok: Whether to allow proofs that contain "admit" or "Admitted" (default: False)
            show_progress: Whether to show progress (default: False) - currently not implemented

        Returns:
            List[bool]: A list of booleans indicating the validity of each proof
            Tuple[List[bool], List[str]]: If return_error_messages=True, returns (validity_list, error_messages_list)
        """
        if self._closed:
            raise RuntimeError("AsyncRocqVerifier is closed")

        if not proofs:
            return ([], []) if return_error_messages else []

        # Create tasks for all proofs
        tasks = [
            self.verify_proof(
                proof,
                timeout=timeout,
                return_error_message=return_error_messages,
                is_sorry_ok=is_sorry_ok
            )
            for proof in proofs
        ]

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)

        if return_error_messages:
            verification_results = [r[0] for r in results]
            error_messages = [r[1] for r in results]
            return verification_results, error_messages
        else:
            return results

    async def close(self):
        """
        Explicitly close the AsyncRocqVerifier and clean up resources.

        This should be called when you're done using the verifier, or use it as an async context manager.
        """
        if not self._closed:
            self._closed = True
            # Note: We can't easily close thread-local clients here since they're in different threads
            # They will be cleaned up when threads terminate

            # Clean up dummy file
            if self._dummy_file and os.path.exists(self._dummy_file):
                try:
                    os.unlink(self._dummy_file)
                except:
                    pass

    def __del__(self):
        """
        Destructor to ensure resources are cleaned up if close() wasn't called explicitly.

        Note: This will log a warning if close() wasn't called properly.
        """
        if hasattr(self, '_closed') and not self._closed:
            import warnings
            warnings.warn(
                "AsyncRocqVerifier was not properly closed. Use 'async with AsyncRocqVerifier(...)' "
                "or call 'await verifier.close()' explicitly.",
                ResourceWarning,
                stacklevel=2
            )
        # Clean up dummy file
        if hasattr(self, '_dummy_file') and self._dummy_file and os.path.exists(self._dummy_file):
            try:
                os.unlink(self._dummy_file)
            except:
                pass
