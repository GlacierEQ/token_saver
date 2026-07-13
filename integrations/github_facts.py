"""First optional integration: a credential-optional GitHub fact store.

The transport is injected so tests never require a token or network access.
"""
from dataclasses import dataclass
from typing import Callable, Dict, Optional

@dataclass
class GitHubFactStore:
    owner: str
    repo: str
    token: Optional[str] = None
    transport: Optional[Callable[[str, Optional[str]], Dict]] = None

    @property
    def enabled(self) -> bool:
        return self.transport is not None and bool(self.owner and self.repo)

    def get(self, path: str) -> Optional[Dict]:
        if not self.enabled:
            return None
        return self.transport(path, self.token)

    def put(self, path: str, value: Dict) -> Dict:
        if not self.enabled:
            raise RuntimeError('GitHub fact store is disabled: provide an injected transport')
        return self.transport(path, self.token)  # write transport can be added without changing callers
