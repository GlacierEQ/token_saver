#!/usr/bin/env python3
"""Audits tokenized *visible text* from a ChatGPT export. NOT model usage telemetry."""
import argparse
import csv
import json
import math
import re
import sys
import zipfile
from pathlib import Path

MAX_JSON_BYTES = 450_000_000


def visible_text(message):
    content = (message or {}).get("content") or {}
    if isinstance(content, str):
        return content
    if not isinstance(content, dict):
        return ""
    parts = content.get("parts")
    if isinstance(parts, list):
        out = []
        for part in parts:
            if isinstance(part, str):
                out.append(part)
            elif isinstance(part, dict) and isinstance(part.get("text"), str):
                out.append(part["text"])
        return "\n".join(out)
    return content.get("text", "") if isinstance(content.get("text"), str) else ""


def selected_messages(conversation):
    mapping = conversation.get("mapping") or {}
    current = conversation.get("current_node")
    if current in mapping:
        chain, seen = [], set()
        while current in mapping and current not in seen:
            seen.add(current)
            node = mapping[current]
            chain.append((current, node))
            current = node.get("parent")
        chain.reverse()
    else:
        # Some export formats don't supply current_node. Mapping values are nodes,
        # and the branch is unknown; report all nodes and flag that uncertainty.
        chain = sorted(mapping.items(), key=lambda it: (
            (it[1].get("message") or {}).get("create_time") or 0,
            str(it[0]),
        ))
    for node_id, node in chain:
        message = node.get("message") or {}
        text = visible_text(message)
        if not text:
            continue
        author = message.get("author") or {}
        yield {
            "node_id": node_id,
            "role": author.get("role", "unknown"),
            "recipient": message.get("recipient") or "",
            "create_time": message.get("create_time") or "",
            "text": text,
            "branch_status": "current_branch" if conversation.get("current_node") in mapping else "branch_unknown",
        }


def token_measure(text, tokenizer=None):
    if tokenizer is not None:
        return len(tokenizer(text)), "tokenizer_count"
    return math.ceil(len(text) / 4) if text else 0, "chars_divided_by_four_estimate"


def analyze_conversations(conversations, tokenizer=None):
    rows = []
    for ci, conversation in enumerate(conversations, 1):
        turn_index = 0
        for idx, m in enumerate(selected_messages(conversation), 1):
            if m["role"] == "user":
                turn_index += 1
            num, method = token_measure(m["text"], tokenizer)
            rows.append({
                "conversation_index": ci,
                "conversation_id": conversation.get("id") or conversation.get("conversation_id") or "",
                "conversation_title": conversation.get("title") or "",
                "message_index": idx,
                "user_turn_index": turn_index,
                "role": m["role"],
                "recipient": m["recipient"],
                "node_id": m["node_id"],
                "create_time": m["create_time"],
                "branch_status": m["branch_status"],
                "characters": len(m["text"]),
                "words": len(re.findall(r"\S+", m["text"])),
                "measured_text_tokens": num,
                "measurement": method,
                "actual_inference_input_tokens": "UNAVAILABLE",
                "actual_inference_output_tokens": "UNAVAILABLE",
                "actual_reasoning_tokens": "UNAVAILABLE",
                "actual_inference_total_tokens": "UNAVAILABLE",
            })
    return rows


def extract_export(data):
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict) and "mapping" in x]
    if isinstance(data, dict):
        for key in ("conversations", "items", "data"):
            v = data.get(key)
            if isinstance(v, list):
                return extract_export(v)
        if "mapping" in data:
            return [data]
    return []


def load_exports(path):
    path = Path(path)
    results = []
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as bundle:
            names = [n for n in bundle.namelist() if re.search(r"(?:^|/)conversations(?:_\d+)?\.json$", n, re.I)]
            if not names:
                raise ValueError("No conversations.json (or numbered conversations_N.json) in ZIP")
            for name in names:
                info = bundle.getinfo(name)
                if info.file_size > MAX_JSON_BYTES:
                    raise ValueError("Export JSON too large for this program")
                results.extend(extract_export(json.loads(bundle.read(name))))
    else:
        if path.stat().st_size > MAX_JSON_BYTES:
            raise ValueError("Export JSON too large for this program")
        results.extend(extract_export(json.loads(path.read_text(encoding="utf-8"))))
    return results


def get_tokenizer():
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("o200k_base")
        return encoding.encode
    except (ImportError, OSError, ValueError):
        return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", help="ChatGPT export .zip or conversations.json")
    parser.add_argument("--text", help="Count this text instead of a conversation export")
    parser.add_argument("--output", default="token-audit", help="Output file prefix (without extension)")
    parser.add_argument("--require-tokenizer", action="store_true", help="Fail rather than estimate when tiktoken/o200k_base is unavailable")
    args = parser.parse_args(argv)
    tok = get_tokenizer()
    if args.require_tokenizer and tok is None:
        parser.error("tiktoken/o200k_base unavailable; install with: python3 -m pip install tiktoken")
    if args.text is not None:
        count, method = token_measure(args.text, tok)
        print(json.dumps({"measured_text_tokens": count, "measurement": method,
                          "encoding": "o200k_base" if tok else None,
                          "actual_chatgpt_model_usage": "UNAVAILABLE"}, indent=2))
        return 0
    if not args.source:
        parser.error("Supply a ChatGPT export ZIP/JSON or --text")
    rows = analyze_conversations(load_exports(args.source), tok)
    if not rows:
        parser.error("No export-visible text messages found")
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.with_suffix(".csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    totals = {}
    for row in rows:
        role = row["role"]
        totals[role] = totals.get(role, 0) + row["measured_text_tokens"]
    summary = {
        "scope": "Text visible in ChatGPT export; not full model inference usage or capacity consumption",
        "method": "o200k_base tokenizer" if tok else "Rough proxy: ceil(visible characters / 4)",
        "exact_for_encoding": bool(tok),
        "not_available_from_export": ["Actual per-turn input tokens incl. prompts/context", "Hidden reasoning tokens", "Model-cached tokens", "Real usage total", "Percent of maximum capability"],
        "conversations": len(set(row["conversation_index"] for row in rows)),
        "visible_messages": len(rows),
        "visible_text_token_totals_by_role": totals,
        "visible_text_token_total": sum(totals.values()),
        "note": "The same text may be re-sent as context many times. Summing visible message tokens is not the number consumed by the model.",
    }
    out.with_suffix(".json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print("Created:", out.with_suffix(".csv"), "and", out.with_suffix(".json"))
    return 0

if __name__ == "__main__":
    sys.exit(main())
