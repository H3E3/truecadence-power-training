#!/usr/bin/env python3
"""TrueCadence FIT parser regression checks.

This script is intentionally lightweight and does not import app.py, because app.py
starts Streamlit page setup at import time. It mirrors the FIT parsing core that
TrueCadence currently depends on and verifies sample FIT files can still be read.

Usage:
  .venv_mac/bin/python tests/test_fit_parser_regression.py [fit files...]

If no files are passed, the script searches common local sample locations.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fitparse import FitFile  # noqa: E402

try:  # noqa: E402
    from fitparse.base import FitFile as _FitParseBaseFile
    from fitparse.profile import MESSAGE_TYPES as _FIT_MESSAGE_TYPES
    from fitparse.records import (
        FieldDefinition as _FitFieldDefinition,
        DevFieldDefinition as _FitDevFieldDefinition,
        DefinitionMessage as _FitDefinitionMessage,
        BASE_TYPES as _FIT_BASE_TYPES,
        BASE_TYPE_BYTE as _FIT_BASE_TYPE_BYTE,
        get_dev_type as _fit_get_dev_type,
    )
except Exception:  # pragma: no cover - mirrors production fallback guards
    _FitParseBaseFile = None
    _FIT_MESSAGE_TYPES = {}
    _FIT_BASE_TYPES = {}
    _FIT_BASE_TYPE_BYTE = None
    _FitFieldDefinition = None
    _FitDevFieldDefinition = None
    _FitDefinitionMessage = None
    _fit_get_dev_type = None


class TolerantFitFile(_FitParseBaseFile if _FitParseBaseFile else FitFile):
    """Fallback for malformed native field definitions seen in COROS DURA FITs."""

    def _parse_definition_message(self, header):
        if not all([
            _FIT_MESSAGE_TYPES is not None,
            _FIT_BASE_TYPES is not None,
            _FIT_BASE_TYPE_BYTE,
            _FitFieldDefinition,
            _FitDefinitionMessage,
        ]):
            return super()._parse_definition_message(header)
        endian = ">" if self._read_struct("xB") else "<"
        global_mesg_num, num_fields = self._read_struct("HB", endian=endian)
        mesg_type = _FIT_MESSAGE_TYPES.get(global_mesg_num)
        field_defs = []

        for _ in range(num_fields):
            field_def_num, field_size, base_type_num = self._read_struct("3B", endian=endian)
            field = mesg_type.fields.get(field_def_num) if mesg_type else None
            base_type = _FIT_BASE_TYPES.get(base_type_num, _FIT_BASE_TYPE_BYTE)
            if base_type and base_type.size and (field_size % base_type.size) != 0:
                base_type = _FIT_BASE_TYPE_BYTE
            field_defs.append(_FitFieldDefinition(field=field, def_num=field_def_num, base_type=base_type, size=field_size))

        dev_field_defs = []
        if header.is_developer_data:
            num_dev_fields = self._read_struct("B", endian=endian)
            for _ in range(num_dev_fields):
                field_def_num, field_size, dev_data_index = self._read_struct("3B", endian=endian)
                field = _fit_get_dev_type(dev_data_index, field_def_num) if _fit_get_dev_type else None
                dev_field_defs.append(_FitDevFieldDefinition(field=field, dev_data_index=dev_data_index, def_num=field_def_num, size=field_size))

        def_mesg = _FitDefinitionMessage(
            header=header,
            endian=endian,
            mesg_type=mesg_type,
            mesg_num=global_mesg_num,
            field_defs=field_defs,
            dev_field_defs=dev_field_defs,
        )
        self._local_mesgs[header.local_mesg_num] = def_mesg
        return def_mesg


def open_fit_file(path: Path):
    """Open FIT with strict parser first, then tolerant parser."""
    try:
        fit = FitFile(str(path))
        list(fit.get_messages("session"))
        return fit, False, ""
    except Exception as first_error:
        if _FitParseBaseFile is None:
            raise
        tolerant = TolerantFitFile(str(path), check_crc=False)
        list(tolerant.get_messages("session"))
        return tolerant, True, str(first_error)


def rolling_best_average(values, window):
    if not values or window <= 0 or len(values) < window:
        return 0
    vals = [float(v or 0) for v in values]
    cur = sum(vals[:window])
    best = cur
    for i in range(window, len(vals)):
        cur += vals[i] - vals[i - window]
        if cur > best:
            best = cur
    return round(best / window)


def extract_fit_power_series(fit):
    powers = []
    for msg in fit.get_messages("record"):
        v = msg.get_values()
        pw = v.get("power")
        if pw is None:
            continue
        try:
            pw = float(pw)
        except Exception:
            continue
        if 0 <= pw <= 2500:
            powers.append(pw)
    return powers


def summarize_fit(path: Path) -> dict:
    fit, tolerant, strict_error = open_fit_file(path)
    sessions = [m.get_values() for m in fit.get_messages("session")]
    assert sessions, f"no session message: {path}"
    s = sessions[0]
    powers = extract_fit_power_series(fit)
    return {
        "file": str(path),
        "parser": "tolerant" if tolerant else "standard",
        "strict_error": strict_error,
        "sessions": len(sessions),
        "date": str(s.get("start_time"))[:10] if s.get("start_time") else "unknown",
        "duration_min": round(float(s.get("total_timer_time") or 0) / 60, 1),
        "distance_km": round(float(s.get("total_distance") or 0) / 1000, 1),
        "avg_power": round(float(s.get("avg_power") or 0)),
        "np": round(float(s.get("normalized_power") or 0)),
        "max_power": round(float(s.get("max_power") or 0)),
        "hr_avg": round(float(s.get("avg_heart_rate") or 0)),
        "record_power_count": len(powers),
        "best_20min": rolling_best_average(powers, 1200),
    }


def default_candidates() -> list[Path]:
    candidates = []
    roots = [
        ROOT / "tests" / "fixtures" / "fit",
        ROOT / "data" / "test",
        Path.home() / "Downloads" / "20260529101237",
        Path.home() / "Downloads",
    ]
    for root in roots:
        if not root.exists():
            continue
        if root == ROOT / "tests" / "fixtures" / "fit":
            candidates.extend(sorted(root.rglob("*.fit")))
        else:
            candidates.extend(sorted(root.glob("*.fit")))
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="*", help="FIT files to check")
    args = parser.parse_args()

    paths = [Path(p).expanduser() for p in args.files] if args.files else default_candidates()
    paths = [p for p in paths if p.exists() and p.suffix.lower() == ".fit"]
    if not paths:
        print("SKIP: no FIT samples found. Put private samples under tests/fixtures/fit/ or pass paths explicitly.")
        return 0

    failures = []
    for path in paths:
        try:
            info = summarize_fit(path)
            print("OK", info)
            assert info["sessions"] >= 1
            if info["record_power_count"]:
                assert info["record_power_count"] > 100, f"too few power records: {path}"
        except Exception as exc:
            failures.append((path, exc))
            print(f"FAIL {path}: {exc}")

    if failures:
        print(f"\n{len(failures)} FIT regression failure(s).")
        return 1
    print(f"\nAll {len(paths)} FIT sample(s) parsed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
