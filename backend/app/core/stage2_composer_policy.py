"""Central Stage 2 composer caps and diversity-selection policy."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class Stage2ComposerPolicy:
    """Small, explicit knobs controlling candidate-pool breadth."""

    max_candidates_per_type: int = 16
    max_group_candidates_per_family: int = 2
    max_rejected_combinations: int = 12
    max_ranked_puzzles: int = 60
    near_duplicate_board_overlap_threshold: int = 14
    semantic_majority_bonus: float = 0.16
    balanced_mixed_penalty: float = 0.18
    microtheme_plus_wordplay_penalty: float = 0.22
    repeated_surface_family_penalty: float = 0.18
    repeated_theme_family_penalty: float = 0.24
    repeated_editorial_family_penalty: float = 0.2
    repeated_template_penalty: float = 0.16
    run_small_theme_family_cap: int = 1
    run_surface_wordplay_family_cap: int = 1
    run_editorial_family_cap: int = 1
    run_balanced_mixed_template_cap: int = 3


STAGE2_COMPOSER_POLICY = Stage2ComposerPolicy()


def stage2_composer_policy_snapshot() -> dict[str, int]:
    """Return a serializable snapshot of the current composer policy."""

    return asdict(STAGE2_COMPOSER_POLICY)
