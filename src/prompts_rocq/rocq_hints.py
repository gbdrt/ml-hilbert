#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#
TACTIC_HINTS = """
`reflexivity`: Use when the goal is trivially equal (e.g., `x = x`)
`exact H`: Use when hypothesis `H` matches the goal exactly
`assumption`: Searches context for exact match to goal
`intro x` or `intros`: Introduce variables/hypotheses for `forall` or `->` in goal
`destruct H`: Breaks down inductive hypothesis `H` into constructors
`destruct H as [x [y H']]`: Destructures existentials and conjunctions
`inversion H`: Analyze constructors of an inductive type, generating equalities
`apply H`: Use when `H : P -> Q` and goal is `Q`
`eapply H`: Like apply but creates existential variables for unknowns
`rewrite H` or `rewrite <- H`: Rewrites using equality `H : a = b` (left-to-right or right-to-left)
`simpl`: Simplifies expressions by unfolding definitions
`simpl in H`: Simplifies hypothesis H
`unfold f`: Unfolds definition of `f`
`fold f`: Folds definition back
`split`: Splits conjunctive goals or applies inductive constructors
`left`/`right`: Choose side of disjunction
`constructor`: Applies the appropriate constructor for the goal
`exfalso`: Proof by contradiction (changes goal to `False`)
`contradiction`: Solves goal when there's a contradictory hypothesis
`discriminate`: Solves goal when there's an impossible constructor equality
`congruence`: Solves goal using congruence closure (equality reasoning)
`f_equal`: Proves `f a = f b` by proving `a = b`
`ring`: Solves polynomial ring equations (requires `Require Import Ring`)
`field`: Solves field equations (requires `Require Import Field`)
`lia` or `nia`: Linear/non-linear integer arithmetic solver (requires `Require Import Lia`)
`lra`: Linear real arithmetic solver (requires `Require Import Lra`)
`assert (H : P) by tac`: Introduces intermediate result `H : P` proved by `tac`
`assert (H : P). { proof }. rest`: Alternative assert syntax
`pose proof H as H'`: Creates a copy of hypothesis H named H'
`generalize dependent x`: Generalizes over x in the goal
`clear H`: Removes hypothesis H from context
`remember e as x`: Replaces expression e with variable x and adds `x = e`
`induction x`: Structural induction on `x`
`induction x as [|n IH]`: Induction with pattern matching for constructors
`induction x using ind_principle`: Custom induction principle
`case_eq e`: Case analysis on expression e
`elim H`: Elimination/induction on H
`exists x`: Provide witness for existential goal
`specialize (H args)`: Specializes a hypothesis with arguments
`symmetry`: Changes `a = b` to `b = a` or vice versa
`transitivity y`: Proves `x = z` via `x = y` and `y = z`
`auto`: Automatic solver using simple tactics
`eauto`: Extended auto with eapply
`tauto`: Propositional tautology checker
`intuition`: Combines auto and intuition for propositional logic
`firstorder`: First-order logic solver
`omega`: Deprecated, use `lia` for integer arithmetic
`erewrite H`: Rewrite with existential variables
`;`: Tactical for applying tactics in sequence (e.g., `tac1; tac2`)
`try tac`: Tries tac, succeeds even if tac fails
`repeat tac`: Applies tac repeatedly until it fails
`now tac`: Applies tac and checks no goals remain
"""

GENERAL_HINTS = """
1. When dealing with inequalities, equalities and arithmetic operations like subtraction or division in `nat`, beware of truncation. Use `Z` (integers), `Q` (rationals), or `R` (reals) when possible for arithmetic operations. Avoid using `nat` unless required by the theorem statement.
2. Be ESPECIALLY careful about implicit types while defining numeric literals. AVOID patterns like `0 - 1` or `1 / 2` without specifying the types or ensuring they're in the right domain.
3. ALWAYS specify types when dealing with numeric values to avoid ambiguities and unexpected behavior.
4. Use `simpl` or `simpl in H` to unfold definitions. Use `unfold` for specific definitions when `simpl` is too aggressive.
5. Use `rewrite <- lemma` for reverse direction. When `rewrite` fails, try `rewrite lemma in H` to rewrite in a hypothesis, or use `pattern` to target specific subterms.
6. When `ring` fails on ring expressions, ensure you have `Require Import Ring` and that all variables are in a ring type. For fields, use `field` with `Require Import Field`.
7. Apply `lia` or `lra` for linear arithmetic problems (integer or real). These are powerful solvers for arithmetic goals.
8. Use `exfalso` or `contradiction` for proof by contradiction.
9. If you get a "no more subgoals" error, it means the previous tactics already solved the goal, and you should remove the subsequent tactics.
10. When proving theorems in Rocq/Coq, use the `Proof.` ... `Qed.` or `Proof.` ... `Defined.` structure.
11. Do NOT mix Ltac (tactic language) with Gallina (term language) inappropriately. Use tactics after `Proof.` and terms in definitions.
12. Remember that Coq requires `admit.` as a placeholder for incomplete proofs (equivalent to Lean's `sorry`).
"""
