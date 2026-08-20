from __future__ import annotations

import copy
import unittest

from scripts.visual_qc.repair_case_identity import (
    IDENTITY_FIELDS,
    IDENTITY_STATUSES,
    MAX_IDENTITY_MODELS,
    RESOLVED_IDENTITY_STATUSES,
    derive_model_identity_resolved,
    validate_device_identity,
    validate_identity_transition,
)


CATALOG_MODELS = ["BG6H", "BG6h"]


def evidence_reference(evidence_id="feishu-case005-source-record"):
    return {
        "kind": "supporting_evidence",
        "evidence_id": evidence_id,
    }


def unresolved_identity():
    return {
        "reported_models": ["TECNO/BG6"],
        "catalog_models": list(CATALOG_MODELS),
        "mapping_status": "unresolved_alias",
        "resolved_models": [],
        "resolution_note": None,
        "evidence_refs": [evidence_reference()],
    }


def conflict_identity():
    identity = unresolved_identity()
    identity["mapping_status"] = "conflict"
    return identity


def confirmed_alias_identity():
    identity = unresolved_identity()
    identity["mapping_status"] = "confirmed_alias"
    identity["resolved_models"] = ["BG6H"]
    identity["resolution_note"] = "Source evidence confirms BG6 maps to BG6H."
    return identity


def exact_match_identity():
    return {
        "reported_models": ["BG6H", "BG6h"],
        "catalog_models": list(CATALOG_MODELS),
        "mapping_status": "exact_catalog_match",
        "resolved_models": ["BG6H", "BG6h"],
        "resolution_note": None,
        "evidence_refs": [],
    }


def with_new_evidence(identity):
    identity["evidence_refs"].append(evidence_reference("later"))
    return identity


class VisualQcRepairCaseIdentityTests(unittest.TestCase):
    def validate(self, identity, *, callback=lambda refs: None):
        return validate_device_identity(
            identity,
            catalog_models=CATALOG_MODELS,
            validate_evidence_refs=callback,
        )

    def test_public_constants_define_exact_contract(self):
        self.assertEqual(MAX_IDENTITY_MODELS, 20)
        self.assertEqual(
            IDENTITY_FIELDS,
            {
                "reported_models",
                "catalog_models",
                "mapping_status",
                "resolved_models",
                "resolution_note",
                "evidence_refs",
            },
        )
        self.assertEqual(
            IDENTITY_STATUSES,
            {
                "exact_catalog_match",
                "confirmed_alias",
                "unresolved_alias",
                "conflict",
            },
        )
        self.assertEqual(
            RESOLVED_IDENTITY_STATUSES,
            {"exact_catalog_match", "confirmed_alias"},
        )

    def test_identity_model_lists_accept_twenty_records(self):
        twenty_reported = confirmed_alias_identity()
        twenty_reported["reported_models"] = [
            f"TECNO/ALIAS-{index}" for index in range(MAX_IDENTITY_MODELS)
        ]
        self.assertEqual(
            self.validate(twenty_reported)["reported_models"],
            twenty_reported["reported_models"],
        )

        twenty_catalog = [
            f"CATALOG-{index}" for index in range(MAX_IDENTITY_MODELS)
        ]
        catalog_identity = confirmed_alias_identity()
        catalog_identity["catalog_models"] = list(twenty_catalog)
        catalog_identity["resolved_models"] = [twenty_catalog[0]]
        self.assertEqual(
            validate_device_identity(
                catalog_identity,
                catalog_models=twenty_catalog,
                validate_evidence_refs=lambda refs: None,
            )["catalog_models"],
            twenty_catalog,
        )

        twenty_resolved = confirmed_alias_identity()
        twenty_resolved["catalog_models"] = list(twenty_catalog)
        twenty_resolved["resolved_models"] = list(twenty_catalog)
        self.assertEqual(
            validate_device_identity(
                twenty_resolved,
                catalog_models=twenty_catalog,
                validate_evidence_refs=lambda refs: None,
            )["resolved_models"],
            twenty_catalog,
        )

    def test_identity_model_lists_reject_twenty_one_records(self):
        twenty_one = MAX_IDENTITY_MODELS + 1

        reported = confirmed_alias_identity()
        reported["reported_models"] = [
            f"TECNO/ALIAS-{index}" for index in range(twenty_one)
        ]
        with self.assertRaisesRegex(
            ValueError,
            "reported_models must contain at most 20 records",
        ):
            self.validate(reported)

        catalog = [f"CATALOG-{index}" for index in range(twenty_one)]
        catalog_identity = confirmed_alias_identity()
        catalog_identity["catalog_models"] = list(catalog)
        catalog_identity["resolved_models"] = [catalog[0]]
        with self.assertRaisesRegex(
            ValueError,
            "catalog_models must contain at most 20 records",
        ):
            validate_device_identity(
                catalog_identity,
                catalog_models=catalog,
                validate_evidence_refs=lambda refs: None,
            )

        resolved = confirmed_alias_identity()
        resolved["resolved_models"] = [
            f"RESOLVED-{index}" for index in range(twenty_one)
        ]
        with self.assertRaisesRegex(
            ValueError,
            "resolved_models must contain at most 20 records",
        ):
            self.validate(resolved)

    def test_all_four_identity_states_are_valid(self):
        for identity in (
            exact_match_identity(),
            confirmed_alias_identity(),
            unresolved_identity(),
            conflict_identity(),
        ):
            with self.subTest(status=identity["mapping_status"]):
                self.assertEqual(self.validate(identity), identity)

    def test_exact_match_requires_identical_nonempty_catalog_models(self):
        for field, value in (
            ("reported_models", ["BG6h", "BG6H"]),
            ("resolved_models", ["BG6H"]),
            ("reported_models", ["TECNO/BG6"]),
            ("resolved_models", ["TECNO/BG6"]),
            ("reported_models", []),
            ("resolved_models", []),
        ):
            identity = exact_match_identity()
            identity[field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaisesRegex(ValueError, field):
                    self.validate(identity)

    def test_exact_match_preserves_exact_source_strings(self):
        identity = exact_match_identity()
        identity["reported_models"] = [" BG6H ", "BG6h"]
        identity["resolved_models"] = [" BG6H ", "BG6h"]
        identity["catalog_models"] = [" BG6H ", "BG6h"]

        validated = validate_device_identity(
            identity,
            catalog_models=[" BG6H ", "BG6h"],
            validate_evidence_refs=lambda refs: None,
        )

        self.assertEqual(validated["reported_models"][0], " BG6H ")
        self.assertEqual(validated["catalog_models"][0], " BG6H ")

    def test_exact_match_rejects_resolution_note(self):
        identity = exact_match_identity()
        identity["resolution_note"] = "No alias needed."
        with self.assertRaisesRegex(ValueError, "resolution note"):
            self.validate(identity)

    def test_confirmed_alias_requires_note_evidence_and_resolved_models(self):
        for field, value, message in (
            ("resolved_models", [], "resolved_models"),
            ("resolution_note", None, "resolution note"),
            ("resolution_note", "", "resolution_note"),
            ("resolution_note", "  ", "resolution_note"),
            ("evidence_refs", [], "evidence"),
        ):
            identity = confirmed_alias_identity()
            identity[field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaisesRegex(ValueError, message):
                    self.validate(identity)

    def test_confirmed_alias_rejects_resolved_model_outside_catalog(self):
        identity = confirmed_alias_identity()
        identity["resolved_models"] = ["BG6"]
        with self.assertRaisesRegex(ValueError, "catalog"):
            self.validate(identity)

    def test_unresolved_and_conflict_require_empty_resolution_and_evidence(self):
        for status in ("unresolved_alias", "conflict"):
            for field, value, message in (
                ("resolved_models", ["BG6H"], "resolved_models"),
                ("resolution_note", "Tentative mapping.", "resolution note"),
                ("evidence_refs", [], "evidence"),
            ):
                identity = unresolved_identity()
                identity["mapping_status"] = status
                identity[field] = value
                with self.subTest(status=status, field=field):
                    with self.assertRaisesRegex(ValueError, message):
                        self.validate(identity)

    def test_string_lists_reject_blanks_duplicates_and_invalid_shapes(self):
        for field, value in (
            ("reported_models", [""]),
            ("reported_models", ["  "]),
            ("reported_models", ["TECNO/BG6", "TECNO/BG6"]),
            ("catalog_models", ["BG6H", "BG6H"]),
            ("resolved_models", ["BG6H", "BG6H"]),
            ("reported_models", "TECNO/BG6"),
            ("catalog_models", None),
            ("resolved_models", None),
        ):
            identity = unresolved_identity()
            if field == "resolved_models":
                identity = confirmed_alias_identity()
            identity[field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaisesRegex(ValueError, field):
                    self.validate(identity)

    def test_canonical_catalog_requires_exact_values_and_order(self):
        for value in (["BG6h", "BG6H"], ["BG6H"], ["BG6H", "BG6"]):
            identity = unresolved_identity()
            identity["catalog_models"] = value
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "catalog_models"):
                    self.validate(identity)

    def test_supplied_canonical_catalog_must_be_valid(self):
        with self.assertRaisesRegex(ValueError, "catalog_models"):
            validate_device_identity(
                unresolved_identity(),
                catalog_models=["BG6H", "BG6H"],
                validate_evidence_refs=lambda refs: None,
            )

    def test_unknown_missing_and_invalid_fields_are_rejected(self):
        unknown = unresolved_identity()
        unknown["unexpected"] = True
        missing = unresolved_identity()
        del missing["resolution_note"]
        for identity in (unknown, missing, [], None):
            with self.subTest(identity=identity):
                with self.assertRaisesRegex(ValueError, "fields"):
                    self.validate(identity)

    def test_mapping_status_must_be_known(self):
        identity = unresolved_identity()
        identity["mapping_status"] = "inferred_alias"
        with self.assertRaisesRegex(ValueError, "mapping_status"):
            self.validate(identity)

    def test_mapping_status_rejects_list_with_clear_validation_error(self):
        identity = unresolved_identity()
        identity["mapping_status"] = ["unresolved_alias"]
        with self.assertRaisesRegex(ValueError, "mapping_status"):
            self.validate(identity)

    def test_mapping_status_rejects_dict_with_clear_validation_error(self):
        identity = unresolved_identity()
        identity["mapping_status"] = {"status": "unresolved_alias"}
        with self.assertRaisesRegex(ValueError, "mapping_status"):
            self.validate(identity)

    def test_evidence_validator_is_invoked_and_result_is_deep_copied(self):
        identity = unresolved_identity()
        original = copy.deepcopy(identity)
        seen = []

        validated = self.validate(identity, callback=lambda refs: seen.append(refs))

        self.assertEqual(seen, [identity["evidence_refs"]])
        self.assertIsNot(seen[0], identity["evidence_refs"])
        self.assertIsNot(validated, identity)
        self.assertIsNot(validated["reported_models"], identity["reported_models"])
        self.assertIsNot(validated["evidence_refs"], identity["evidence_refs"])
        self.assertIsNot(
            validated["evidence_refs"][0],
            identity["evidence_refs"][0],
        )
        validated["reported_models"].append("NEW")
        validated["evidence_refs"][0]["evidence_id"] = "changed"
        self.assertEqual(identity, original)

    def test_evidence_validator_failure_is_propagated_without_mutating_input(self):
        identity = unresolved_identity()
        original = copy.deepcopy(identity)

        def reject(refs):
            refs.append(evidence_reference("callback-mutation"))
            raise ValueError("invalid evidence reference")

        with self.assertRaisesRegex(ValueError, "invalid evidence reference"):
            self.validate(identity, callback=reject)
        self.assertEqual(identity, original)

    def test_derived_resolution_boundary_matches_only_resolved_states(self):
        for status in IDENTITY_STATUSES:
            with self.subTest(status=status):
                self.assertEqual(
                    derive_model_identity_resolved({"mapping_status": status}),
                    status in {"exact_catalog_match", "confirmed_alias"},
                )

    def test_unresolved_alias_allows_forward_and_same_state_transitions(self):
        previous = unresolved_identity()
        for status in ("unresolved_alias", "confirmed_alias", "conflict"):
            current = {
                "unresolved_alias": unresolved_identity,
                "confirmed_alias": confirmed_alias_identity,
                "conflict": conflict_identity,
            }[status]()
            if status != "unresolved_alias":
                with_new_evidence(current)
            with self.subTest(status=status):
                self.assertIsNone(
                    validate_identity_transition(
                        previous,
                        current,
                        has_new_correction=False,
                    )
                )

    def test_conflict_allows_same_state_and_corrected_confirmation(self):
        previous = conflict_identity()
        self.assertIsNone(
            validate_identity_transition(
                previous,
                conflict_identity(),
                has_new_correction=False,
            )
        )
        self.assertIsNone(
            validate_identity_transition(
                previous,
                with_new_evidence(confirmed_alias_identity()),
                has_new_correction=True,
            )
        )

    def test_conflict_confirmation_requires_new_correction(self):
        with self.assertRaisesRegex(ValueError, "correction"):
            validate_identity_transition(
                conflict_identity(),
                with_new_evidence(confirmed_alias_identity()),
                has_new_correction=False,
            )

    def test_unresolved_confirmation_requires_new_evidence(self):
        with self.assertRaisesRegex(ValueError, "new evidence"):
            validate_identity_transition(
                unresolved_identity(),
                confirmed_alias_identity(),
                has_new_correction=False,
            )

    def test_unresolved_conflict_requires_new_evidence(self):
        with self.assertRaisesRegex(ValueError, "new evidence"):
            validate_identity_transition(
                unresolved_identity(),
                conflict_identity(),
                has_new_correction=False,
            )

    def test_conflict_confirmation_requires_new_evidence(self):
        with self.assertRaisesRegex(ValueError, "new evidence"):
            validate_identity_transition(
                conflict_identity(),
                confirmed_alias_identity(),
                has_new_correction=True,
            )

    def test_resolved_identity_is_immutable_after_publication(self):
        for previous in (exact_match_identity(), confirmed_alias_identity()):
            self.assertIsNone(
                validate_identity_transition(
                    previous,
                    copy.deepcopy(previous),
                    has_new_correction=False,
                )
            )
            current = copy.deepcopy(previous)
            current["evidence_refs"].append(evidence_reference("later"))
            with self.subTest(status=previous["mapping_status"]):
                with self.assertRaisesRegex(ValueError, "immutable"):
                    validate_identity_transition(
                        previous,
                        current,
                        has_new_correction=True,
                    )

    def test_reported_models_and_evidence_are_append_only_prefixes(self):
        previous = unresolved_identity()
        appended = unresolved_identity()
        appended["reported_models"].append("TECNO BG6")
        appended["evidence_refs"].append(evidence_reference("later"))
        self.assertIsNone(
            validate_identity_transition(
                previous,
                appended,
                has_new_correction=False,
            )
        )

        for field, value, message in (
            ("reported_models", [], "reported models"),
            ("reported_models", ["TECNO BG6"], "reported models"),
            ("evidence_refs", [], "evidence"),
            ("evidence_refs", [evidence_reference("replacement")], "evidence"),
        ):
            current = unresolved_identity()
            current[field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaisesRegex(ValueError, message):
                    validate_identity_transition(
                        previous,
                        current,
                        has_new_correction=False,
                    )

    def test_name_or_catalog_changes_require_new_evidence(self):
        previous = unresolved_identity()
        for field, value in (
            ("reported_models", ["TECNO/BG6", "TECNO BG6"]),
            ("catalog_models", ["BG6H", "BG6h", "BG6"]),
        ):
            current = unresolved_identity()
            current[field] = value
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "new evidence"):
                    validate_identity_transition(
                        previous,
                        current,
                        has_new_correction=False,
                    )

            current["evidence_refs"].append(evidence_reference("later"))
            self.assertIsNone(
                validate_identity_transition(
                    previous,
                    current,
                    has_new_correction=False,
                )
            )

    def test_backward_and_unsupported_transitions_are_rejected(self):
        for previous, current in (
            (conflict_identity(), unresolved_identity()),
            (unresolved_identity(), exact_match_identity()),
        ):
            with self.subTest(
                previous=previous["mapping_status"],
                current=current["mapping_status"],
            ):
                with self.assertRaises(ValueError):
                    validate_identity_transition(
                        previous,
                        current,
                        has_new_correction=True,
                    )


if __name__ == "__main__":
    unittest.main()
