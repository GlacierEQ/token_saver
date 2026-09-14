"""Optional read-only GitHub fact retrieval.

No network call is made unless a transport is explicitly supplied or a token is
present in the environment through ``from_environment``. Tests inject a mock
transport and never require credentials.
"""

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import quote
from urllib.request import Request, urlopen

Transport = Callable[[str, str | None], dict]


def urllib_transport(owner: str, repo: str, timeout: float = 10.0) -> Transport:
    """Create a small stdlib GitHub Contents API transport."""

    def fetch(path: str, token: str | None) -> dict:
        clean = path.strip("/")
        encoded = "/".join(quote(part, safe="") for part in clean.split("/"))
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{encoded}"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "token-saver",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = Request(url, headers=headers, method="GET")
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    return fetch


@dataclass
class GitHubFactStore:
    owner: str
    repo: str
    token: str | None = None
    transport: Transport | None = None

    @classmethod
    def from_environment(cls, owner: str, repo: str) -> "GitHubFactStore":
        token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        transport = urllib_transport(owner, repo) if token else None
        return cls(owner, repo, token=token, transport=transport)

    @property
    def enabled(self) -> bool:
        return bool(self.transport and self.owner and self.repo)

    def get(self, path: str) -> dict | None:
        if not self.enabled:
            return None
        if not path or ".." in path.split("/"):
            raise ValueError("path must be a non-empty repository-relative path")
        assert self.transport is not None
        return self.transport(path, self.token)
