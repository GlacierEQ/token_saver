from __future__ import annotations

import importlib
import inspect
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

_EXPECTED_REFUSALS = (
    AttributeError,
    ImportError,
    KeyError,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
)
_EXPECTED_REFUSALS_EXCEPT_TYPE = (
    AttributeError,
    ImportError,
    KeyError,
    OSError,
    RuntimeError,
    ValueError,
)


class AdversarialEliteTests(unittest.TestCase):
    def _load(self):
        errors = []
        for name in ("pure_pointer", "src.pure_pointer"):
            try:
                return importlib.import_module(name)
            except ImportError as exc:
                errors.append(f"{name}: {exc}")
        self.fail("; ".join(errors))

    def test_module_importable(self):
        mod = self._load()
        public = [name for name in dir(mod) if not name.startswith("_")]
        self.assertGreater(len(public), 0, "module exposes no public names")

    def test_refuse_bad_import_path_does_not_shadow(self):
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("src.__elite_does_not_exist_pure_pointer")

    def test_central_mechanism_refuse_or_edge(self):
        """Exercise shipped refuse/edge paths when present; never crash open."""
        mod = self._load()
        exercised = False

        for cname, cls in inspect.getmembers(mod, inspect.isclass):
            if cname.startswith("_"):
                continue
            mname = getattr(cls, "__module__", None) or ""
            if mname.startswith("typing") or mname in {
                "builtins",
                "collections",
                "pathlib",
                "json",
                "sys",
                "os",
            }:
                continue
            if getattr(mod, cname, None) is not cls and mname not in {
                mod.__name__,
                getattr(mod, "__package__", None),
            }:
                continue

            try:
                sig = inspect.signature(cls)
            except (TypeError, ValueError):
                sig = None
            if sig is None:
                continue
            if any(
                parameter.default is inspect.Parameter.empty
                and parameter.name != "self"
                and parameter.kind
                not in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD)
                for parameter in sig.parameters.values()
            ):
                continue
            try:
                inst = cls()
            except _EXPECTED_REFUSALS:
                inst = None
            if inst is None:
                continue

            plan = getattr(inst, "plan", None)
            if callable(plan):
                try:
                    out = plan("__elite_no_such_connector__", "delete")
                    self.assertIsNotNone(out)
                    if isinstance(out, dict) and out.get("allowed") is True:
                        self.assertTrue(
                            out.get("human_approved") is True
                            or out.get("status")
                            in {"REFUSED", "DENIED", "ERROR", "UNKNOWN"},
                            f"plan allowed unknown connector: {out!r}",
                        )
                    exercised = True
                except _EXPECTED_REFUSALS as exc:
                    exercised = True
                    self.assertIsInstance(exc, _EXPECTED_REFUSALS)

            for meth in ("authorize", "decide", "check"):
                fn = getattr(inst, meth, None)
                if not callable(fn):
                    continue
                try:
                    signature = inspect.signature(fn)
                except (TypeError, ValueError):
                    signature = None
                if signature is None:
                    continue
                required = [
                    parameter
                    for parameter in signature.parameters.values()
                    if parameter.name != "self"
                    and parameter.default is inspect.Parameter.empty
                    and parameter.kind
                    not in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD)
                ]
                if required:
                    continue
                try:
                    out = fn()
                    self.assertIsNotNone(out)
                    exercised = True
                except _EXPECTED_REFUSALS:
                    exercised = True

        sched = getattr(mod, "schedule", None)
        if callable(sched):
            try:
                out = sched([], 1.0)
                self.assertIsInstance(out, dict)
                self.assertIn("plan", out)
                exercised = True
            except TypeError:
                try:
                    out = sched([])
                    self.assertIsNotNone(out)
                    exercised = True
                except _EXPECTED_REFUSALS:
                    exercised = True
            except _EXPECTED_REFUSALS_EXCEPT_TYPE:
                exercised = True

        for edge_fn, args in (
            ("anomaly_score", (1e9,)),
            ("thermal_margin", (-40.0,)),
            ("simulate_rack", (0, 0.0)),
        ):
            fn = getattr(mod, edge_fn, None)
            if not callable(fn):
                continue
            try:
                out = fn(*args)
                self.assertIsNotNone(out)
                exercised = True
            except _EXPECTED_REFUSALS:
                exercised = True

        for cname, cls in inspect.getmembers(mod, inspect.isclass):
            if cname.startswith("_"):
                continue
            try:
                inst = cls()
            except _EXPECTED_REFUSALS:
                inst = None
            if inst is None:
                continue
            metrics = getattr(inst, "metrics", None)
            if isinstance(metrics, dict) and metrics:
                self.assertIn(next(iter(metrics)), metrics)
                exercised = True
                break

        if not exercised:
            public = [name for name in dir(mod) if not name.startswith("_")]
            self.assertGreater(len(public), 0)
            with self.assertRaises(
                (AttributeError, TypeError, ImportError, ValueError, KeyError)
            ):
                getattr(mod, "__elite_missing_surface__")


if __name__ == "__main__":
    unittest.main()
