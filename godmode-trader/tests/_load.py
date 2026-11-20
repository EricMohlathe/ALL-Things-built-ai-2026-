"""Load a script from a skill folder (the folder names have hyphens), and run tests in a scratch folder."""

import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "tests", "fixtures")
CHARTS = os.path.join(FIX, "charts")
CALENDAR = os.path.join(FIX, "calendar", "ff_calendar_thisweek.json")
COT = os.path.join(FIX, "cot", "legacy-futures.json.gz")
NEWS = os.path.join(FIX, "news")
DAILY = os.path.join(FIX, "scanner", "daily-3mo1d.json.gz")
sys.path.insert(0, os.path.join(ROOT, "trader-core"))
_CACHE = {}


def load(folder, name):
    key = (folder, name)
    if key not in _CACHE:
        path = os.path.join(ROOT, folder, name + ".py")
        spec = importlib.util.spec_from_file_location("trader_%s_%s" % (folder.replace("-", "_"), name), path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _CACHE[key] = mod
    return _CACHE[key]


def core():
    """The one tradercore module every tool imports (so its exception classes are the same objects)."""
    import tradercore
    return tradercore


class Scratch(object):
    """A temporary working folder with trader/config.json from the example (balance 5000)."""

    def __init__(self, config=None):
        self.config = config

    def __enter__(self):
        self.old = os.getcwd()
        self.dir = tempfile.mkdtemp(prefix="godmode-trader-")
        os.chdir(self.dir)
        os.makedirs("trader")
        with open(os.path.join(ROOT, "trader-budget", "config.example.json")) as fh:
            cfg = json.load(fh)
        cfg.update(self.config or {})
        with open("trader/config.json", "w") as fh:
            json.dump(cfg, fh)
        return self

    def __exit__(self, *exc):
        os.chdir(self.old)
        shutil.rmtree(self.dir, ignore_errors=True)


def run(mod, argv):
    """(exit code, stdout, stderr) of mod.main(argv)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = mod.main(argv)
    return code, out.getvalue(), err.getvalue()


def read(path):
    with open(path) as fh:
        return json.load(fh)


def write(path, doc):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w") as fh:
        json.dump(doc, fh)
