"""Render the matrix results as markdown tables for spike/RESULTS.md.

  uv run python -m spike.matrix_report            # print to stdout
  uv run python -m spike.matrix_report --write    # replace the block between the markers

The block between <!-- matrix:start --> and <!-- matrix:end --> in RESULTS.md is generated.
Everything outside it is written by hand.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from spike.s3_consolidation import totals

HERE = Path(__file__).parent
RESULTS = HERE / "results" / "matrix"
REPORT = HERE / "RESULTS.md"
START, END = "<!-- matrix:start -->", "<!-- matrix:end -->"

ORDER = ["gemma3:4b", "gemma3:12b", "gemma4:e2b", "gemma4:e4b", "gemma4:12b"]
CONTEXTS = ["2048", "32768", "full"]


def load() -> list[dict]:
    cells = [json.loads(p.read_text()) for p in sorted(RESULTS.glob("*.json"))]

    def key(c: dict) -> tuple[int, int]:
        model = ORDER.index(c["model"]) if c["model"] in ORDER else len(ORDER)
        ctx = CONTEXTS.index(c["context_label"]) if c["context_label"] in CONTEXTS else 9
        return model, ctx

    return sorted(cells, key=key)


def pct(value: float | None, digits: int = 0) -> str:
    return "n/a" if value is None else f"{value * 100:.{digits}f}%"


def gb(value: float | None) -> str:
    return "n/a" if not value else f"{value / 1e9:.1f}"


def ctx_name(cell: dict) -> str:
    label = cell["context_label"]
    tokens = cell.get("context_tokens")
    if label == "full":
        return f"full ({tokens // 1024}k)" if tokens else "full"
    return f"{int(label) // 1024}k" if int(label) >= 1024 and int(label) != 2048 else "2k"


def usable(cell: dict) -> bool:
    return cell.get("status") in ("ok", "partial") and "s3" in cell


def table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(out)


def footprint(cells: list[dict]) -> str:
    rows = []
    for c in cells:
        mem = c.get("memory") or {}
        after = c.get("memory_after") or {}
        rows.append(
            [
                c["model"],
                ctx_name(c),
                f"{c['info'].get('parameter_size') or '?'} / {c['info'].get('quantization') or '?'}",
                gb(c["info"].get("disk_bytes")),
                gb(mem.get("memory_bytes")),
                gb(after.get("memory_bytes") or mem.get("memory_bytes")),
                str(mem.get("loaded_context") or "n/a"),
                c["status"],
            ]
        )
    return table(
        [
            "Model",
            "Context",
            "Params / quant",
            "Disk GB",
            "Loaded GB",
            "After run GB",
            "Ctx loaded",
            "Status",
        ],
        rows,
    )


def s3_view(cell: dict) -> tuple[dict, dict, int]:
    """Headline S3 numbers without the haystack, so every cell is judged on the same corpus.

    The haystack only runs in windows that can hold it, and its 4,800 lines of small talk
    swamp precision. It is reported in its own column instead.
    """
    rows = [r for r in cell["rows"] if r["set"] != "haystack"]
    signal = [r for r in rows if not r["noise"]]
    by_lang = {
        lang: totals([r for r in signal if r["lang"] == lang])
        for lang in ("en", "it", "mixed")
        if any(r["lang"] == lang for r in signal)
    }
    return totals(signal), by_lang, sum(r["memories"] for r in rows if r["noise"])


def quality(cells: list[dict]) -> str:
    rows = []
    for c in filter(usable, cells):
        s3, s4 = c["s3"], c["s4"]
        o, _, noise = s3_view(c)
        by = s3["by_set"]
        rows.append(
            [
                c["model"],
                ctx_name(c),
                pct(o["recall"]),
                pct(o["precision"]),
                pct(o["wrong_source_rate"]),
                pct(o["duplicate_rate"]),
                str(noise),
                pct(by.get("hand", {}).get("recall")),
                pct(by.get("short", {}).get("recall")),
                pct(by.get("long", {}).get("recall")),
                pct(by.get("day100", {}).get("recall")),
                pct(by.get("haystack", {}).get("recall")),
                pct(s4["detect_rate"]),
                pct(s4["false_scenario_rate"]),
                str(s4["false_insights_surviving"]),
            ]
        )
    return table(
        [
            "Model", "Context", "Recall", "Precision", "Wrong speaker", "Duplicates",
            "Noise memories", "hand", "short", "long", "day100", "haystack",
            "Insights found", "False-Insight scenarios", "False Insights passing code",
        ],
        rows,
    )  # fmt: skip


def languages(cells: list[dict]) -> str:
    rows = []
    for c in filter(usable, cells):
        by = s3_view(c)[1]
        rows.append(
            [c["model"], ctx_name(c)]
            + [
                f"{pct(by[k]['recall'])} / {pct(by[k]['precision'])}" if k in by else "n/a"
                for k in ("en", "it", "mixed")
            ]
        )
    return table(["Model", "Context", "English", "Italian", "Mixed"], rows)


def position(cells: list[dict]) -> str:
    rows = []
    for c in filter(usable, cells):
        for name in ("day100", "haystack"):
            row = c["s3"]["by_set"].get(name)
            if row and row.get("recall_by_third"):
                first, mid, last = (pct(x) for x in row["recall_by_third"])
                rows.append([c["model"], ctx_name(c), name, first, mid, last])
    return table(["Model", "Context", "Set", "First third", "Middle third", "Last third"], rows)


def speed(cells: list[dict]) -> str:
    rows = []
    for c in filter(usable, cells):
        calls = c["s3"]["calls"]
        sp = c.get("speed") or {}
        rows.append(
            [
                c["model"],
                ctx_name(c),
                str(calls["calls"]),
                f"{calls['strict']}/{calls['recovered']}/{calls['partial']}/{calls['failed']}",
                str(calls["truncated"]),
                f"{c.get('load_seconds', 'n/a')}",
                f"{c.get('s3_seconds', 0) / 60:.1f}",
                f"{sp.get('prompt_tokens_per_s') or 'n/a'}",
                f"{sp.get('output_tokens_per_s') or 'n/a'}",
            ]
        )
    return table(
        ["Model", "Context", "S3 calls", "JSON strict/fenced/partial/failed", "Cut off", "Load s", "S3 min", "Prompt tok/s", "Output tok/s"],
        rows,
    )  # fmt: skip


def issues(cells: list[dict]) -> str:
    lines = []
    for c in cells:
        name = f"`{c['model']}` @ {ctx_name(c)}"
        if c.get("status") not in ("ok",):
            lines.append(f"- {name}: **{c['status']}** {c.get('note', '')}")
        if usable(c) and c["s3"].get("skipped"):
            lines.append(f"- {name}: skipped {', '.join(c['s3']['skipped'])}")
    return "\n".join(lines) or "- none"


def render() -> str:
    cells = load()
    if not cells:
        return "_No matrix results yet._"
    parts = [
        ("Memory and disk footprint", footprint(cells)),
        (
            "Quality (headline columns exclude the haystack; `haystack` shows it alone)",
            quality(cells),
        ),
        ("Recall / precision by language", languages(cells)),
        ("Recall by position in the Conversation", position(cells)),
        ("Speed and output reliability (on the M5 Pro)", speed(cells)),
    ]
    out = []
    for title, body in parts:
        out.append(f"#### {title}\n\n{body}\n")
    out.append(f"#### Cells that did not finish cleanly\n\n{issues(cells)}\n")
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    block = render()
    if not args.write:
        print(block)
        return
    text = REPORT.read_text()
    if START not in text or END not in text:
        raise SystemExit(f"{REPORT} has no {START} ... {END} block")
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    REPORT.write_text(f"{head}{START}\n\n{block}\n{END}{tail}")
    print(f"wrote {len(block.splitlines())} lines into {REPORT.name}")


if __name__ == "__main__":
    main()
