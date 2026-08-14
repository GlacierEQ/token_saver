from pathlib import Path
import re


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"expected {label} not found")
    return text.replace(old, new, 1)


path = Path("scripts/operate.py")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    "from __future__ import annotations\nimport importlib\n",
    "from __future__ import annotations\n\nimport enum\nimport importlib\n",
    "operate import block",
)
text = replace_once(
    text,
    '        except Exception as e:\n            errors.append("%s: %s: %s" % (name, type(e).__name__, e))\n',
    '        except ImportError as exc:\n            errors.append(f"{name}: {type(exc).__name__}: {exc}")\n',
    "import exception",
)

pattern = r'def _is_local_class\(mod, obj\) -> bool:\n    try:\n.*?    except Exception:\n        return False\n\n'
replacement = 'def _is_local_class(mod, obj) -> bool:\n    mod_name = getattr(obj, "__module__", None)\n    if mod_name in {mod.__name__, getattr(mod, "__package__", None)}:\n        return True\n    if getattr(mod, obj.__name__, None) is not obj:\n        return False\n    return not (\n        mod_name\n        and (\n            mod_name.startswith("typing")\n            or mod_name in {"builtins", "collections", "pathlib", "json", "sys", "os"}\n        )\n    )\n\n'
text, count = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL)
if count != 1:
    raise SystemExit("expected local-class predicate")

pattern = r'    try:\n        import enum\n        if isinstance\(value, enum\.Enum\):\n.*?    except Exception:\n        pass\n'
replacement = '    if isinstance(value, enum.Enum):\n        return called_name in {"status", "decide", "check", "verdict", "state"}\n'
text, count = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL)
if count != 1:
    raise SystemExit("expected enum content predicate")

pattern = r'        if inspect\.isawaitable\(result\):\n            try:\n                result\.close\(\)\n            except Exception:\n                pass\n            return None\n        return result\n    except SystemExit:\n        return None\n    except Exception:\n        return None\n'
replacement = '        if inspect.isawaitable(result):\n            close = getattr(result, "close", None)\n            if callable(close):\n                close()\n            return None\n        return result\n    except SystemExit:\n        return None\n    except (AttributeError, KeyError, OSError, RuntimeError, TypeError, ValueError):\n        return None\n'
text, count = re.subn(pattern, replacement, text, count=1)
if count != 1:
    raise SystemExit("expected safe-call probe")

text = replace_once(
    text,
    '_DEFERRED_FNS = ("digest",)  # weak helper — last resort after real ops\n',
    '_DEFERRED_FNS = ("digest",)  # weak helper — last resort after real ops\n_PROBE_ERRORS = (AttributeError, ImportError, KeyError, OSError, RuntimeError, TypeError, ValueError)\n\n\ndef _construct_quietly(factory, *args, **kwargs):\n    try:\n        return factory(*args, **kwargs)\n    except _PROBE_ERRORS:\n        return None\n',
    "probe error boundary",
)
text = text.replace(
    'value.startswith("<function ") or value.startswith("<class ")',
    'value.startswith(("<function ", "<class "))',
)
text = replace_once(
    text,
    '        if value.isupper() and value.isidentifier() and len(value) < 24:\n            if called_name not in {"status", "decide", "check", "verdict", "state", "allow_claim"}:\n                return False\n        return True\n',
    '        return not (\n            value.isupper()\n            and value.isidentifier()\n            and len(value) < 24\n            and called_name not in {"status", "decide", "check", "verdict", "state", "allow_claim"}\n        )\n',
    "all-caps predicate",
)
text = replace_once(
    text,
    '        if all(callable(x) or inspect.isclass(x) for x in value):\n            return False\n        return True\n',
    '        return not all(callable(x) or inspect.isclass(x) for x in value)\n',
    "collection content predicate",
)
text = text.replace("set(value.keys())", "set(value)")
text = text.replace("for k in value.keys()", "for k in value")
text = text.replace('"sample_%s" % name', 'f"sample_{name}"')
text = text.replace('"sample_%s" % p.name', 'f"sample_{p.name}"')
text = text.replace(
    '"no content-checked mechanism CALL; public=%s" % (public[:12],)',
    'f"no content-checked mechanism CALL; public={public[:12]}"',
)
text = replace_once(
    text,
    '    try:\n        sig = inspect.signature(cls)\n    except Exception:\n        return None\n    import enum\n',
    '    try:\n        sig = inspect.signature(cls)\n    except (TypeError, ValueError):\n        return None\n',
    "dataclass signature probe",
)
text = replace_once(
    text,
    '    try:\n        return cls(**kwargs)\n    except Exception:\n        try:\n            return cls()\n        except Exception:\n            return None\n',
    '    candidate = _construct_quietly(cls, **kwargs)\n    if candidate is not None:\n        return candidate\n    return _construct_quietly(cls)\n',
    "dataclass constructor fallback",
)
text = replace_once(
    text,
    '    try:\n        sig = inspect.signature(fn)\n    except Exception:\n        yield ()\n        return\n',
    '    try:\n        sig = inspect.signature(fn)\n    except (TypeError, ValueError):\n        yield ()\n        return\n',
    "call signature probe",
)
text = text.replace("\n    import enum\n    import tempfile\n", "\n    import tempfile\n", 1)
text = replace_once(
    text,
    '    except Exception:\n        methods = []\n',
    '    except _PROBE_ERRORS:\n        methods = []\n',
    "class method scoring exception",
)
text = replace_once(
    text,
    '    except Exception:\n        try:\n            return cls()\n        except Exception:\n            return None\n    if not required:\n        try:\n            return cls()\n        except Exception:\n            return None\n',
    '    except (TypeError, ValueError):\n        return _construct_quietly(cls)\n    if not required:\n        return _construct_quietly(cls)\n',
    "class construction signature fallback",
)
pattern = r'            if resolved is not None and inspect\.isclass\(resolved\):\n                try:\n                    import enum\n                    if issubclass\(resolved, enum\.Enum\):\n                        args\.append\(next\(iter\(resolved\)\)\)\n                        continue\n                except Exception:\n                    pass\n                s = _build_dataclass_sample\(resolved, mod\)'
replacement = '            if resolved is not None and inspect.isclass(resolved):\n                if issubclass(resolved, enum.Enum):\n                    args.append(next(iter(resolved)))\n                    continue\n                s = _build_dataclass_sample(resolved, mod)'
text, count = re.subn(pattern, replacement, text, count=1)
if count != 1:
    raise SystemExit("expected resolved-type construction block")
text = replace_once(
    text,
    '    if None not in args:\n        try:\n            return cls(*args)\n        except Exception:\n            pass\n',
    '    if None not in args:\n        candidate = _construct_quietly(cls, *args)\n        if candidate is not None:\n            return candidate\n',
    "class positional construction",
)
text = replace_once(
    text,
    '    for trial in (\n        [[] for _ in required],\n        [set() for _ in required],\n        [{} for _ in required],\n        [b"elite-operate-secret" if i == 0 else 1 for i in range(len(required))],\n    ):\n        try:\n            return cls(*trial)\n        except Exception:\n            continue\n    return None\n',
    '    for trial in (\n        [[] for _ in required],\n        [set() for _ in required],\n        [{} for _ in required],\n        [b"elite-operate-secret" if i == 0 else 1 for i in range(len(required))],\n    ):\n        candidate = _construct_quietly(cls, *trial)\n        if candidate is not None:\n            return candidate\n    return None\n',
    "constructor trial loop",
)
pattern = r'    for cname, obj in members:\n        try:\n            import enum\n            if inspect\.isclass\(obj\) and issubclass\(obj, enum\.Enum\):\n                continue\n        except Exception:\n            pass\n        filtered\.append\(\(cname, obj\)\)'
replacement = '    for cname, obj in members:\n        if issubclass(obj, enum.Enum):\n            continue\n        filtered.append((cname, obj))'
text, count = re.subn(pattern, replacement, text, count=1)
if count != 1:
    raise SystemExit("expected enum class filtering block")
text = replace_once(
    text,
    '    except Exception as e:\n        out = {\n            "repository": "GlacierEQ/token_saver",\n            "module": imported_as,\n            "smoke": {"kind": "error", "error": str(e)},\n',
    '    except _PROBE_ERRORS as exc:\n        out = {\n            "repository": "GlacierEQ/token_saver",\n            "module": imported_as,\n            "smoke": {"kind": "error", "error": str(exc)},\n',
    "main probe exception",
)
if "except Exception" in text:
    raise SystemExit("blanket exception remains in scripts/operate.py")
path.write_text(text, encoding="utf-8")

pure_pointer = Path("src/pure_pointer.py")
content = pure_pointer.read_text(encoding="utf-8")
if content.startswith("#!/usr/bin/env python3\n"):
    pure_pointer.write_text(content.split("\n", 1)[1], encoding="utf-8")

adversarial = Path("tests/test_adversarial.py")
content = adversarial.read_text(encoding="utf-8")
content = content.replace(
    "                mod.__elite_missing_surface__\n",
    '                getattr(mod, "__elite_missing_surface__")\n',
)
adversarial.write_text(content, encoding="utf-8")
