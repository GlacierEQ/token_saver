"""Measurement helpers that refuse unsupported savings claims."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Savings:
    before: int
    after: int
    measured: bool = True

    @property
    def saved(self) -> int:
        if not self.measured or self.before < 0 or self.after < 0:
            return 0
        return max(0, self.before - self.after)
