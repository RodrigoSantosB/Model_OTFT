"""Helpers to map per-curve idleak keys (JSON) to ordered float lists."""
import os


def normalize_idleak_curve_key(key):
    """Normalize a curve key for case-insensitive matching (underscores vs hyphens, strip .csv)."""
    s = str(key).strip().lower()
    if s.endswith(".csv"):
        s = s[:-4]
    return s.replace("_", "-")


def _float_idleak_value(val):
    return float(val)


def _voltage_key_variants(v):
    """Generate common aliases for transfer curves keyed by fixed VDS."""
    fv = float(v)
    tags = []
    if abs(fv - round(fv)) < 1e-9:
        vi = int(round(fv))
        tags.append(f"transfer-{vi}v")
        tags.append(f"transfer_{vi}v".replace("_", "-"))
        tags.append(f"{vi}vds")
        tags.append(f"vds-{vi}v")
    tags.append(f"transfer-{fv}v")
    s = f"{fv:g}".lower()
    tags.append(f"transfer-{s}v")
    tags.append(f"{s}vds")
    tags.append(f"vds-{s}v")
    return tags


def resolve_idleak_for_transfers(loaded_idleak_dict, path_voltages, count_transfer):
    """
    Map a dict of curve-id -> idleak string/number to a list ordered like transfer curves
    in path_voltages (first count_transfer entries with curve_type == 0).

    Candidate keys per curve: filename stem, transfer/vds voltage aliases and transfer-<index>.
    """
    if path_voltages is None:
        raise ValueError(
            "path_voltages is required when loaded_idleak is a dict mapping curve ids to values."
        )
    if not isinstance(loaded_idleak_dict, dict):
        raise TypeError("loaded_idleak dict expected, got %s" % type(loaded_idleak_dict).__name__)

    lookup = {}
    for raw_k, raw_v in loaded_idleak_dict.items():
        nk = normalize_idleak_curve_key(raw_k)
        lookup[nk] = _float_idleak_value(raw_v)

    transfer_rows = [pv for pv in path_voltages if pv[1] == 0]
    if len(transfer_rows) < count_transfer:
        raise ValueError(
            "path_voltages has %s transfer curves but count_transfer is %s"
            % (len(transfer_rows), count_transfer)
        )

    selected = transfer_rows[: int(count_transfer)]
    result = []

    for j, curve in enumerate(selected):
        path, _, v_ds = curve
        stem = os.path.splitext(os.path.basename(str(path)))[0]
        candidates = [
            stem,
            normalize_idleak_curve_key(stem),
            f"transfer-{j}",
            f"transfer_{j}".replace("_", "-"),
        ]
        for tag in _voltage_key_variants(v_ds):
            candidates.append(tag)
            candidates.append(normalize_idleak_curve_key(tag))

        seen = set()
        ordered = []
        for c in candidates:
            nc = normalize_idleak_curve_key(c)
            if nc not in seen:
                seen.add(nc)
                ordered.append(nc)

        matched = None
        for nc in ordered:
            if nc in lookup:
                matched = lookup[nc]
                break

        if matched is None:
            raise ValueError(
                "No loaded_idleak entry matched transfer curve %s (file=%s, V=%s). "
                "Tried normalized keys among: %s. Dict keys (normalized): %s"
                % (
                    j,
                    path,
                    v_ds,
                    ordered[:12],
                    list(lookup.keys()),
                )
            )
        result.append(matched)

    return result
