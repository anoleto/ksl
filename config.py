from __future__ import annotations

import os
import re

from dotenv import load_dotenv

load_dotenv()

def read_list(env_var: str) -> list[str]:
    value = os.getenv(env_var)
    return [item.strip() for item in value.replace("\n", ",").split(",") if item.strip()] if value else []

def read_bool(env_var: str) -> bool:
    value = os.getenv(env_var)
    return value.strip().lower() in ("true", "1", "yes", "y", "on") if value else False

TOKEN: str | None = os.getenv("TOKEN")
DEBUG: bool = read_bool("DEBUG")
OwnerID: int | None = int(os.getenv("OWNER_ID"))
MainServerID: int | None = int(os.getenv("MAIN_SERVER_ID"))

Status: str | None = os.getenv("STATUS")

db_config: dict[str, str | None] = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "db": os.getenv("DB_NAME"),
}

Bancho: str | None = os.getenv("BANCHO")
BanchoApiKey: str | None = os.getenv("BANCHO_API_KEY")

ownercheckmotd: list[str] = read_list("OWNER_MOTD")

lastfm: str | None = os.getenv("LASTFM")

use_start_prompt: bool = read_bool("USE_START_PROMPT")
starting_prompt_id: int | None = int(os.getenv("STARTING_PROMPT_ID"))
MODEL: str | None = os.getenv("MODEL")
