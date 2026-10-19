# ChatGPT Token Auditor

**What this measures:** Export-visible text message tokens, by conversation, role, and turn. With `tiktoken`, the counts are exact for the specified **o200k_base tokenizer**. Without it, the program clearly labels **character-count estimates**, not exact tokens.

**What this does NOT measure:** The model's actual input, output, internal reasoning, cached, or total token usage. ChatGPT exports don't necessarily contain that telemetry; this program does not invent it. In particular, exporting text does not reveal how often an earlier message was re-sent as context. o200k_base may differ from the currently deployed ChatGPT model tokenizer.

## Obtain a ChatGPT export

ChatGPT → Settings → Data controls → Export data → Export → Confirm export. Download the resulting ZIP using your account; keep the ZIP private because it may contain sensitive messages and files. Official documentation: https://help.openai.com/en/articles/7260999-export-your-data-from-chatgpt

## On Mac (Python 3)

Install the tokenizer for exact **o200k_base counts of visible text**:

```bash
python3 -m pip install tiktoken
```

Run the standalone tool on the downloaded ZIP, without unzipping:

```bash
python3 chatgpt_token_audit.py ~/Downloads/chatgpt-export.zip --output ~/Desktop/chatgpt-token-audit --require-tokenizer
```

If you have extracted JSON, substitute `conversations.json` for the ZIP. If `--require-tokenizer` fails, install `tiktoken` or remove that flag to use a **rough character-based estimate**.

Output:
- `chatgpt-token-audit.csv`: each export-visible message with conversation, role, turn index, characters and measured tokens.
- `chatgpt-token-audit.json`: count totals and what cannot be observed.

An export can contain edited/regenerated branches. This tool follows `current_node` to count the selected branch only when it is available. If `current_node` is missing, `branch_status=branch_unknown` warns that messages from alternative branches may be included. Multimodal items such as image/audio payloads are excluded.

## Exact model-usage telemetry requires the right source

For OpenAI **API** calls, use the official `response.usage` fields (including `input_tokens`, `output_tokens`, `output_tokens_details.reasoning_tokens`, `total_tokens` when provided). These fields are actual usage data for the corresponding API call. **They do not expose the token usage of a separate ChatGPT subscription chat.**

OpenAI documentation: https://help.openai.com/en/articles/10478918-reviewing-api-usage-and-costs

## Test

```bash
python3 -m pytest -q tests/test_chatgpt_export_audit.py
```

This script performs no network requests and sends no chat content anywhere.
### Existing Token Saver integration

Install from this repository with `python3 -m pip install -e '.[audit]'`, then use `token-saver-chatgpt-audit ~/Downloads/chatgpt-export.zip --output ~/Desktop/chatgpt-token-audit --require-tokenizer`. Optional `audit` installs `tiktoken`. This utility never contacts ChatGPT or sends your private export anywhere.
