"""
Management command: migrate_to_mongo

One-time (and idempotent) migration of all existing ORM data to MongoDB.

Reads ``GameSession``, ``GameParticipant``, and ``GameAction`` records in
configurable batches and upserts them into the corresponding Mongo
collections via ``replace_one(upsert=True)``.

Safe to re-run: every write is keyed on ``_id`` (the Django ORM integer PK),
so re-running overwrites Mongo documents with the current ORM state — it
fixes drift without creating duplicates.

Collection order
----------------
Sessions are migrated before participants, and participants before actions,
to mirror referential-integrity ordering even though Mongo doesn't enforce it.

Usage
-----
    python manage.py migrate_to_mongo                          # migrate all
    python manage.py migrate_to_mongo --dry-run               # count only
    python manage.py migrate_to_mongo --collection sessions   # one collection
    python manage.py migrate_to_mongo --batch-size 100        # smaller chunks
"""

import time

from django.core.management.base import BaseCommand, CommandError

from db.documents import action_from_orm, participant_from_orm, session_from_orm
from games.models import GameAction, GameParticipant, GameSession

# Ordered so that referential dependencies are satisfied: sessions first.
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


class Command(BaseCommand):
    help = "Migrate all ORM data to MongoDB (idempotent upsert by _id)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Count records and print plan without writing to MongoDB",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            metavar="N",
            help="Number of ORM rows to load per database query (default: 500)",
        )
        parser.add_argument(
            "--collection",
            choices=list(COLLECTIONS) + ["all"],
            default="all",
            metavar="NAME",
            help=(
                "Restrict migration to one collection: "
                "sessions | participants | actions | all  (default: all)"
            ),
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        batch_size: int = options["batch_size"]
        collection_filter: str = options["collection"]

        if batch_size < 1:
            raise CommandError("--batch-size must be at least 1")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN — no data will be written to MongoDB.")
            )

        targets = (
            {collection_filter: COLLECTIONS[collection_filter]}
            if collection_filter != "all"
            else COLLECTIONS
        )

        if not dry_run:
            try:
                # Late import keeps Atlas connection out of --dry-run and CI.
                from db.mongo import get_db  # noqa: PLC0415

                db = get_db()
            except Exception as exc:
                raise CommandError(f"Cannot connect to MongoDB: {exc}") from exc
        else:
            db = None

        totals = {"written": 0, "failed": 0}
        start = time.monotonic()

        for coll_name, (model_cls, converter, queryset) in targets.items():
            self.stdout.write(f"Migrating '{coll_name}'...")
            written, failed = self._migrate_collection(
                coll_name,
                queryset.iterator(chunk_size=batch_size),
                converter,
                db,
                dry_run,
            )
            totals["written"] += written
            totals["failed"] += failed
            verb = "Would write" if dry_run else "Wrote"
            suffix = f", {failed} failed" if failed else ""
            self.stdout.write(f"  \u2192 {verb} {written} document(s){suffix}")

        elapsed = time.monotonic() - start
        summary = (
            f"Done in {elapsed:.2f}s \u2014 "
            f"{'would migrate' if dry_run else 'migrated'} "
            f"{totals['written']} document(s)."
        )
        if totals["failed"]:
            raise CommandError(
                f"{summary}  {totals['failed']} document(s) failed "
                f"\u2014 check stderr for details."
            )
        self.stdout.write(self.style.SUCCESS(summary))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _migrate_collection(self, coll_name, queryset_iter, converter, db, dry_run):
        """Iterate over a queryset and upsert each document.

        Returns a ``(written, failed)`` tuple.  In dry-run mode every record
        counts as written and no Mongo calls are made.
        """
        written = failed = 0

        for orm_obj in queryset_iter:
            try:
                doc = dict(converter(orm_obj))
            except Exception as exc:
                self.stderr.write(
                    f"  [SKIP] Convert failed \u2014 "
                    f"{coll_name} id={getattr(orm_obj, 'id', '?')}: {exc}"
                )
                failed += 1
                continue

            if dry_run:
                written += 1
                continue

            try:
                db[coll_name].replace_one({"_id": doc["_id"]}, doc, upsert=True)
                written += 1
            except Exception as exc:
                self.stderr.write(
                    f"  [ERROR] Upsert failed \u2014 "
                    f"{coll_name} _id={doc.get('_id', '?')}: {exc}"
                )
                failed += 1

        return written, failed
