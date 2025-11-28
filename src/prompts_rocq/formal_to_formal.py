#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#
##############################################################
#               Formal to Formal (Rocq/Coq)
##############################################################
COT_PROMPT = """
Complete the following Rocq/Coq code:
```coq
{formal_statement}
```
Before producing the Rocq/Coq code to formally prove the given theorem, provide a detailed proof plan outlining the main proof steps and strategies. The plan should highlight key ideas, intermediate lemmas, and proof structures that will guide the construction of the final formal proof.
"""

NON_COT_PROMPT = """
Complete the following Rocq/Coq code:
```coq
{formal_statement}
```
"""
