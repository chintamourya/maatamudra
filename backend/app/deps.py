from __future__ import annotations

from dataclasses import dataclass

from .db import Repo, make_repo
from .legal.kanoon import KanoonClient
from .llm import LLM


@dataclass
class Services:
    llm: LLM
    repo: Repo
    kanoon: KanoonClient


def build_services() -> Services:
    repo = make_repo()
    return Services(llm=LLM(), repo=repo, kanoon=KanoonClient(repo))


services: Services | None = None


def get_services() -> Services:
    global services
    if services is None:
        services = build_services()
    return services
