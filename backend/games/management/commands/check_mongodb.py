import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from pymongo import MongoClient
from pymongo.errors import ConfigurationError, PyMongoError


class Command(BaseCommand):
    help = "Validate MongoDB connectivity and optional replica set requirement"

    def add_arguments(self, parser):
        parser.add_argument(
            "--require-replica-set",
            action="store_true",
            help="Fail if the connected deployment is not a replica set",
        )

    def handle(self, *args, **options):
        mongodb_uri = os.getenv("MONGODB_URI", settings.MONGODB_URI)
        mongodb_db_name = os.getenv("MONGODB_DB_NAME", settings.MONGODB_DB_NAME)
        require_replica_set = bool(options.get("require_replica_set")) or bool(
            settings.MONGODB_REQUIRE_REPLICA_SET
        )

        if not mongodb_uri:
            raise CommandError("MONGODB_URI is not configured.")

        if "<db_username>" in mongodb_uri or "<db_password>" in mongodb_uri:
            raise CommandError(
                "MONGODB_URI still contains placeholder credentials. Set real credentials in backend/.env."
            )

        self.stdout.write("Checking MongoDB connection...")
        self.stdout.write(f"URI: {mongodb_uri}")
        self.stdout.write(f"Database: {mongodb_db_name}")

        try:
            client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=8000)
            ping_result = client.admin.command("ping")
            if int(ping_result.get("ok", 0)) != 1:
                raise CommandError("MongoDB ping did not return ok=1")

            hello = client.admin.command("hello")
            set_name = hello.get("setName")
            is_writable_primary = bool(hello.get("isWritablePrimary"))

            if require_replica_set and not set_name:
                raise CommandError(
                    "Replica set is required but not detected. Ensure Atlas/replica-set deployment is used."
                )

            self.stdout.write(self.style.SUCCESS("MongoDB connection successful."))
            if set_name:
                self.stdout.write(self.style.SUCCESS(f"Replica set: {set_name}"))
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "No replica set reported. Multi-document transactions may not be available."
                    )
                )
            self.stdout.write(
                self.style.SUCCESS(f"Writable primary available: {is_writable_primary}")
            )
        except ConfigurationError as exc:
            raise CommandError(f"MongoDB configuration error: {exc}") from exc
        except PyMongoError as exc:
            raise CommandError(f"MongoDB connection failed: {exc}") from exc
        finally:
            try:
                client.close()
            except Exception:
                pass
