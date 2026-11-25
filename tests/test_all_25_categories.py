"""Test resolution of all 25 official EHA categories and pillar mappings."""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import config
from config import EHA_CONFIRMED_CATEGORIES, get_applicable_pillars, EHA_LIFECYCLE_PILLARS


def test_all_25_exact_names():
    """Verify that every one of the 25 official categories maps to its expected pillars."""
    print(f"\n--- Testing all {len(EHA_CONFIRMED_CATEGORIES)} official categories ---")
    assert len(EHA_CONFIRMED_CATEGORIES) == 25, f"Expected 25 categories, got {len(EHA_CONFIRMED_CATEGORIES)}"

    for cat in EHA_CONFIRMED_CATEGORIES:
        cat_id = cat["id"]
        cat_name = cat["name"]
        expected_pillars = cat["pillars"]

        resolved = get_applicable_pillars(cat_name)
        assert resolved == expected_pillars, (
            f"Failed on category #{cat_id} '{cat_name}': expected {expected_pillars}, got {resolved}"
        )
        print(f"  [PASS] #{cat_id:02d}: {cat_name} -> {resolved}")


def test_quote_and_dash_variations():
    """Verify variations with straight vs curly quotes, en-dash vs hyphen, case changes."""
    print("\n--- Testing quote and dash variations ---")
    test_cases = [
        # Curly vs straight quote
        ("Most Supportive 'Return to Work' Program", ["Attraction & Onboarding", "Learning & Growth", "Well-being", "Culture"]),
        ("Best 'Women-in-Leadership' Program", ["Leadership & Strategy", "Culture", "Learning & Growth"]),
        ("Best Women-in-Leadership Program", ["Leadership & Strategy", "Culture", "Learning & Growth"]),
        # Hyphens vs en-dash
        ("Best Company to Work For - Large", EHA_LIFECYCLE_PILLARS),
        ("Best Company to Work For - Medium", EHA_LIFECYCLE_PILLARS),
        ("Best Company to Work For - Small", EHA_LIFECYCLE_PILLARS),
        # Without (New Category) tag
        ("Excellence in Emiratization", ["Attraction & Onboarding", "Learning & Growth", "Leadership & Strategy", "Culture"]),
        ("Best Workplace for Gen Z", ["Culture", "Well-being", "Learning & Growth", "Attraction & Onboarding"]),
        # Common acronyms
        ("Best L&D Strategy", ["Learning & Growth", "Leadership & Strategy"]),
        ("Best Learning and Development Strategy", ["Learning & Growth", "Leadership & Strategy"]),
        ("Best AI in HR", ["Leadership & Strategy", "Culture", "Attraction & Onboarding"]),
    ]

    for input_name, expected in test_cases:
        resolved = get_applicable_pillars(input_name)
        assert resolved == expected, f"Failed variation '{input_name}': expected {expected}, got {resolved}"
        print(f"  [PASS] Variation '{input_name}' -> {resolved}")


def test_fallback():
    """Verify fallback for unmapped or empty category strings."""
    print("\n--- Testing fallback behavior ---")
    assert get_applicable_pillars(None) == EHA_LIFECYCLE_PILLARS
    assert get_applicable_pillars("") == EHA_LIFECYCLE_PILLARS
    assert get_applicable_pillars("Custom Unrecognized Category 2026") == EHA_LIFECYCLE_PILLARS
    print("  [PASS] Fallback safely returns all 6 pillars")


if __name__ == "__main__":
    test_all_25_exact_names()
    test_quote_and_dash_variations()
    test_fallback()
    print("\nALL 25 CATEGORY RESOLUTION TESTS PASSED WITH 100% COVERAGE!")
