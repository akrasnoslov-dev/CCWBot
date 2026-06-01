"""Import shim for the ops-agent package stored under ops-agent/."""

from __future__ import annotations

from pathlib import Path
from pkgutil import extend_path

__version__ = "0.1.0"

__path__ = extend_path(__path__, __name__)
_impl_path = Path(__file__).resolve().parent.parent / "ops-agent" / "ops_agent"
if _impl_path.is_dir():
    __path__.append(str(_impl_path))
