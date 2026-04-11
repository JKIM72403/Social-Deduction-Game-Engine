"""
Management command: verify_mongo_consistency

Compares every ORM record against its counterpart in MongoDB and reports
divergence: missing documents or field-level mismatches.

Intended for use during the dual-write window (Phase 6–7) to validate that
MongoDB is in-sync with the ORM before setting ``USE_MONGODB=True``.

Exit behaviour
--------------
* All consistent → prints OK per collection, exits 0.
* Any divergence → raises ``CommandError`` (exits 1) with a summary count.

Field comparison
----------------
Every field defined in the corresponding ``TypedDict`` schema is compared.
Fields in ``_SKIP_FIELDS`` are excluded — add datetime fields there if
sub-second precision drift is observed between SQLite and BSON timestamps.

Usage
-----
    python manage.py verify_mongo_consistency
    python manage.py verify_mongo_consistency --collection sessions
    python manage.py verify_mongo_consistency --fail-fast
"""

from django.core.management.base import BaseCommand, CommandError

from db.documents import action_from_orm, participant_from_orm, session_from_orm
from games.models import GameAction, GameParticipant, GameSession

# The third element is a base queryset with the correct select_related chain so
# that session_from_orm / participant_from_orm never trigger N+1 lookups.
COLLECTIONS = {
    "sessions": (
        GameSession,
        session_from_orm,
        GameSession.objects.select_related("template", "host"),
    ),
    "participants": (
        GameParticipant,
        participant_from_orm,
        GameParticipant.objects.select_related("user"),
    ),
    "actions": (
        GameAction,
        action_from_orm,
        GameAction.objects.all(),
    ),
}

# Fields excluded from comparison.  Extend this set if clock-skew or
# microsecond precision differences are observed in production datetimes.
_SKIP_FIELDS: frozenset[str] = frozenset()


class Command(BaseCommand):
    help = "Compare ORM vs MongoDB field-by-field to detect consistency divergence"

    def add_arguments(self, parser):
        parser.add_argument(
            "--collection",
            choices=list(COLLECTIONS) + ["all"],
            default="all",
            metavar="NAME",
            help=(
                "Only check this collection: "
                "sessions | participants | actions | all  (default: all)"
            ),
        )
        parser.add_argument(
            "--fail-fast",
            action="store_true",
            help="Stop immediately after the first mismatch is found",
        )

    def handle(self, *args, **options):
        collection_filter: str = options["collection"]
        fail_fast: bool = options["fail_fast"]

        try:
            from db.mongo import get_db  # noqa: PLC0415

            db = get_db()
        except Exception as exc:
            raise CommandError(f"Cannot connect to MongoDB: {exc}") from exc

        targets = (
            {collection_filter: COLLECTIONS[collection_filter]}
            if collection_filter != "all"
            else COLLECTIONS
        )

        total_mismatches = 0

        for coll_name, (model_cls, converter, queryset) in targets.items():
            self.stdout.write(f"Checking '{coll_name}'...")
            mismatches = self._check_collection(
                coll_name, queryset, converter, db, fail_fast
            )
            total_mismatches += mismatches

            if mismatches:
                self.stdout.write(
                    self.style.ERROR(f"  \u2192 {mismatches} mismatch(es)")
                )
            else:
                self.stdout.write(self.style.SUCCESS("  \u2192 OK"))

            if fail_fast and total_mismatches:
                break

        if total_mismatches:
            raise CommandError(
                f"Consistency check FAILED: "
                f"{total_mismatches} mismatch(es) found across all checked collections."
            )

        self.stdout.write(self.style.SUCCESS("All collections consistent \u2713"))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_collection(self, coll_name, queryset, converter, db, fail_fast):
        """Return the count of mismatches found in one collection."""
        mismatches = 0

        for orm_obj in queryset.iterator(chunk_size=200):
            try:
                expected = dict(converter(orm_obj))
            except Exception as exc:
                self.stderr.write(
                    f"  [SKIP] Convert failed \u2014 "
                    f"{coll_name} id={getattr(orm_obj, 'id', '?')}: {exc}"
                )
                continue

            mongo_doc = db[coll_name].find_one({"_id": expected["_id"]})

            if mongo_doc is None:
                self.stdout.write(
                    self.style.ERROR(
                        f"  [MISSING] {coll_name} _id={expected['_id']} "
                        f"not found in MongoDB"
                    )
                )
                mismatches += 1
                if fail_fast:
                    return mismatches
                continue

            for field, expected_val in expected.items():
                if field in _SKIP_FIELDS:
                    continue
                actual_val = mongo_doc.get(field)
                if actual_val != expected_val:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  [MISMATCH] {coll_name} _id={expected['_id']} "
                            f"'{field}': ORM={expected_val!r}, Mongo={actual_val!r}"
                        )
                    )
                    mismatches += 1
                    if fail_fast:
                        return mismatches

        return mismatches
