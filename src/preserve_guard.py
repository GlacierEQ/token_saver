import re

class BudgetUnmetProtectedError(Exception):
    pass

class PreserveGuard:
    def __init__(self):
        self.patterns = [
            # Negation/constraint statements
            re.compile(r'\bnot\b', re.IGNORECASE),
            re.compile(r'\bnever\b', re.IGNORECASE),
            re.compile(r'\bdo not\b', re.IGNORECASE),
            re.compile(r'\bmust\b', re.IGNORECASE),
            re.compile(r'\bforbidden\b', re.IGNORECASE),
            # Git SHAs / SHA-256 (heuristic: 40 or 64 hex chars)
            re.compile(r'\b[0-9a-f]{40}\b', re.IGNORECASE),
            re.compile(r'\b[0-9a-f]{64}\b', re.IGNORECASE),
            # URLs
            re.compile(r'https?://[^\s]+', re.IGNORECASE),
            # ISO timestamps
            re.compile(r'\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2}?)?\b'),
            # Docket/case numbers
            re.compile(r'\b\d+:\d{2}-[a-zA-Z]+-\d{1,5}-[a-zA-Z]+\b', re.IGNORECASE),
            # PRESERVE markers
            re.compile(r'PRESERVE'),
        ]

    def is_protected(self, block: str) -> bool:
        for pattern in self.patterns:
            if pattern.search(block):
                return True
        return False

    def enforce_budget(self, text: str, max_lines: int) -> dict:
        lines = text.split('\n')
        protected_lines = []
        unprotected_lines = []
        
        for idx, line in enumerate(lines):
            if self.is_protected(line):
                protected_lines.append((idx, line))
            else:
                unprotected_lines.append((idx, line))
        
        if len(protected_lines) > max_lines:
            raise BudgetUnmetProtectedError("BUDGET_UNMET_PROTECTED")
        
        # Keep all protected lines, and fill the rest with unprotected lines
        lines_to_keep = max_lines - len(protected_lines)
        selected_unprotected = unprotected_lines[:lines_to_keep]
        
        final_lines = protected_lines + selected_unprotected
        final_lines.sort(key=lambda x: x[0])
        
        final_text = "\n".join(line for _, line in final_lines)
        
        return {
            "text": final_text,
            "protected_recall": 1.0,
        }
