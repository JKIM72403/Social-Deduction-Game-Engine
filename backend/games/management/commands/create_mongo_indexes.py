"""
Management command: create_mongo_indexes

Creates all required MongoDB indexes for the Social Deduction Game backend.
Safe to run multiple times — pymongo's create_index() is idempotent when the
index specification and options already match.

Usage:
    python manage.py create_mongo_indexes          # create only
    python manage.py create_mongo_indexes --drop   # drop all app indexes first, then recreate
    python manage.py create_mongo_indexes --list   # print current indexes and exit
"""

from django.core.management.base import BaseCommand, CommandError

INDEX_SPEC = {
    # ------------------------------------------------------------------ #
    # Collection: sessions                                                 #
    # ------------------------------------------------------------------ #
    "sessions": [
        {
            "keys": [("join_code", 1)],
            "options": {"unique": True, "name": "sessions_join_code_unique"},
        },
        {
            "keys": [("host_user_id", 1), ("status", 1)],
            "options": {"name": "sessions_host_status"},
        },
        {
            "keys": [("status", 1), ("created_at", -1)],
            "options": {"name": "sessions_status_created"},
        },
    ],
    # ------------------------------------------------------------------ #
    # Collection: participants                                             #
    # ------------------------------------------------------------------ #
    "participants": [
        {
            "keys": [("session_id", 1), ("user_id", 1)],
            "options": {"unique": True, "name": "participants_session_user_unique"},
        },
        {
            "keys": [("session_id", 1), ("display_name", 1)],
            "options": {"unique": True, "name": "participants_session_name_unique"},
        },
        {
            "keys": [("session_id", 1), ("seat_order", 1)],
            "options": {"unique": True, "name": "participants_session_seat_unique"},
        },
        {
            "keys": [("session_id", 1), ("is_alive", 1)],
            "options": {"name": "participants_session_alive"},
        },
    ],
    # ------------------------------------------------------------------ #
    # Collection: actions                                                  #
    # ------------------------------------------------------------------ #
    "actions": [
        {
            # Hot path for vote-duplicate check and vote resolution queries.
            "keys": [
                ("session_id", 1),
                ("participant_id", 1),
                ("turn_number", 1),
                ("phase", 1),
                ("action_type", 1),
            ],
            "options": {
                "name": "actions_unique_vote_submission",
                "unique": True,
            },
        },
        {
            "keys": [("session_id", 1), ("turn_number", 1), ("status", 1)],
            "options": {"name": "actions_session_turn_status"},
        },
    ],
    # ------------------------------------------------------------------ #
    # Collection: game_templates                                           #
    # ------------------------------------------------------------------ #
    "game_templates": [
        {
            "keys": [("creator_id", 1)],
            "options": {"name": "templates_creator"},
        },
        {
            "keys": [("is_public", 1), ("creator_id", 1)],
            "options": {"name": "templates_public_creator"},
        },
    ],
    # ------------------------------------------------------------------ #
    # Collection: role_templates                                           #
    # ------------------------------------------------------------------ #
    "role_templates": [
        {
            "keys": [("is_default", 1)],
            "options": {"name": "roles_is_default"},
        },
        {
            "keys": [("alignment", 1)],
            "options": {"name": "roles_alignment"},
        },
    ],
    # ------------------------------------------------------------------ #
    # Collection: ability_templates                                        #
    # ------------------------------------------------------------------ #
    "ability_templates": [
        {
            "keys": [("is_default", 1)],
            "options": {"name": "abilities_is_default"},
        },
        {
            "keys": [("ability_type", 1)],
            "options": {"name": "abilities_type"},
        },
    ],
    # ------------------------------------------------------------------ #
    # Collection: auth_tokens                                              #
    # ------------------------------------------------------------------ #
    "auth_tokens": [
        {
            "keys": [("key", 1)],
            "options": {"unique": True, "name": "tokens_key_unique"},
        },
        {
            "keys": [("user_id", 1)],
            "options": {"name": "tokens_user"},
        },
    ],
}


class Command(BaseCommand):
    help = "Create (or recreate) all required MongoDB indexes"

    def add_arguments(self, parser):
        parser.add_argument(
            "--drop",
            action="store_true",
            help="Drop all application-managed indexes before recreating them",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            dest="list_indexes",
            help="Print current indexes for all managed collections and exit",
        )

    def handle(self, *args, **options):
        try:
            from db.mongo import get_db
        except RuntimeError as exc:
            raise CommandError(str(exc)) from exc

        try:
            db = get_db()
            # Quick connectivity check
            db.command("ping")
        except Exception as exc:
            raise CommandError(f"Cannot connect to MongoDB: {exc}") from exc

        if options["list_indexes"]:
            self._list_indexes(db)
            return

        if options["drop"]:
            self._drop_managed_indexes(db)

        self._create_indexes(db)

    # ------------------------------------------------------------------ #

    def _create_indexes(self, db):
        from pymongo import ASCENDING, DESCENDING

        direction_map = {1: ASCENDING, -1: DESCENDING}

        total = 0
        for collection_name, index_defs in INDEX_SPEC.items():
            collection = db[collection_name]
            for spec in index_defs:
                keys = [(field, direction_map[dir_]) for field, dir_ in spec["keys"]]
                try:
                    result = collection.create_index(keys, **spec["options"])
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  [{collection_name}] ensured index: {result}"
                        )
                    )
                    total += 1
                except Exception as exc:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  [{collection_name}] FAILED index {spec['options'].get('name')}: {exc}"
                        )
                    )

        self.stdout.write(self.style.SUCCESS(f"\n{total} indexes ensured across {len(INDEX_SPEC)} collections."))

    def _drop_managed_indexes(self, db):
        for collection_name, index_defs in INDEX_SPEC.items():
            collection = db[collection_name]
            for spec in index_defs:
                name = spec["options"].get("name")
                if not name:
                    continue
                try:
                    collection.drop_index(name)
                    self.stdout.write(f"  [{collection_name}] dropped index: {name}")
                except Exception:
                    pass  # Index may not exist yet; that's fine.

    def _list_indexes(self, db):
        for collection_name in INDEX_SPEC:
            collection = db[collection_name]
            self.stdout.write(f"\n--- {collection_name} ---")
            try:
                for idx in collection.list_indexes():
                    self.stdout.write(f"  {idx.get('name')}: {idx.get('key')}")
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f"  (could not list: {exc})"))
