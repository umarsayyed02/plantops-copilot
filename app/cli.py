from __future__ import annotations

import argparse

from app.config import Settings
from app.service import PlantOpsService


def main() -> None:
    parser = argparse.ArgumentParser(description="PlantOps Copilot utilities")
    parser.add_argument("command", choices=["ingest"])
    arguments = parser.parse_args()

    service = PlantOpsService(Settings.from_env())
    if arguments.command == "ingest":
        documents, chunks, sources = service.ingest_all()
        print(f"Indexed {documents} documents into {chunks} chunks")
        for source in sources:
            print(f"- {source}")


if __name__ == "__main__":
    main()

