# app/mongodb/connect.py
import os
from typing import Any

import certifi
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

# Accept either env var name
mongourl: str | None = os.getenv("MONGO_URI") or os.getenv("mongodb")

if not mongourl:
    raise RuntimeError("MONGO_URI (or mongodb) is not set in .env")


def connectdb() -> Any:
    # Only enable TLS for Atlas (mongodb+srv:// or *.mongodb.net)
    is_atlas: bool = (
        mongourl.startswith("mongodb+srv://")  # type: ignore[union-attr]
        or "mongodb.net" in mongourl          # type: ignore[operator]
    )

    kwargs: dict[str, Any] = {"serverSelectionTimeoutMS": 10000}
    if is_atlas:
        kwargs["tls"] = True
        kwargs["tlsCAFile"] = certifi.where()

    client: MongoClient = MongoClient(mongourl, **kwargs)  # type: ignore[arg-type]
    return client["study-mart"]