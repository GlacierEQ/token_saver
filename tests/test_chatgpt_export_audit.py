import json
import unittest
from src.chatgpt_export_audit import visible_text, selected_messages, analyze_conversations, token_measure, extract_export

class TokenAuditTests(unittest.TestCase):
    def test_extracts_only_string_parts_not_multimodal_payload(self):
        m={"content":{"content_type":"multimodal_text","parts":["hello",{"asset_pointer":"secret"},"world"]}}
        self.assertEqual(visible_text(m), "hello\nworld")

    def test_does_not_double_count_abandoned_branches(self):
        c={"title":"Branches", "current_node":"answer_b", "mapping":{
          "root":{"id":"root","parent":None,"message":None},
          "user":{"id":"user","parent":"root","message":{"author":{"role":"user"},"content":{"parts":["question"]}}},
          "answer_a":{"id":"answer_a","parent":"user","message":{"author":{"role":"assistant"},"content":{"parts":["abandoned"]}}},
          "answer_b":{"id":"answer_b","parent":"user","message":{"author":{"role":"assistant"},"content":{"parts":["selected"]}}},
        }}
        self.assertEqual([m["text"] for m in selected_messages(c)], ["question","selected"])

    def test_includes_exact_when_tokenizer_supplied(self):
        self.assertEqual(token_measure("one two",lambda t:[0,1]),(2,"tokenizer_count"))

    def test_fallback_is_labeled_estimate(self):
        n,method=token_measure("abcd efgh",None)
        self.assertEqual((n,method),(3,"chars_divided_by_four_estimate"))

    def test_aggregates_per_assistant_reply_without_calling_it_actual_usage(self):
        c={"id":"conv1", "title":"Hi", "current_node":"a", "mapping":{
          "u":{"id":"u","parent":None,"message":{"author":{"role":"user"},"content":{"parts":["question"]}}},
          "a":{"id":"a","parent":"u","message":{"author":{"role":"assistant"},"content":{"parts":["answer"]}}},
        }}
        rows=analyze_conversations([c],lambda t:[0]*len(t.split()))
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[1]["measured_text_tokens"],1)
        self.assertEqual(rows[1]["measurement"],"tokenizer_count")
        self.assertEqual(rows[1]["actual_inference_total_tokens"],"UNAVAILABLE")

    def test_export_wrapper(self):
        obj={"conversations":[{"title":"One","mapping":{} }]}
        self.assertEqual(len(extract_export(obj)),1)

if __name__=='__main__':unittest.main()

# Regression: count only exported visible text; never imply hidden telemetry.
class ExportAndSafetyTests(unittest.TestCase):
    def test_empty_text_does_not_invent_tokens(self):
        self.assertEqual(token_measure("", None), (0, "chars_divided_by_four_estimate"))

    def test_branch_unknown_is_labeled(self):
        conversation = {"mapping": {"a": {"parent": None, "message": {
            "author": {"role": "assistant"}, "content": {"parts": ["visible"]}
        }}}}
        rows = analyze_conversations([conversation])
        self.assertEqual(rows[0]["branch_status"], "branch_unknown")
        self.assertEqual(rows[0]["actual_reasoning_tokens"], "UNAVAILABLE")

    def test_loads_zip_without_exposing_chat_text_in_reports(self):
        import csv
        import tempfile
        import zipfile
        from pathlib import Path
        from src.chatgpt_export_audit import main
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            payload = [{"title": "Sensitive title", "current_node": "x", "mapping": {
                "x": {"parent": None, "message": {"author": {"role": "user"},
                    "content": {"parts": ["PRIVATE_SENTINEL_NEVER_IN_REPORT"]}}}}}]
            archive = directory / "export.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("conversations.json", json.dumps(payload))
            destination = directory / "audit"
            self.assertEqual(main([str(archive), "--output", str(destination)]), 0)
            with destination.with_suffix(".csv").open(newline="", encoding="utf-8") as fp:
                rows = list(csv.DictReader(fp))
            self.assertEqual(len(rows), 1)
            self.assertNotIn("PRIVATE_SENTINEL_NEVER_IN_REPORT", destination.with_suffix(".csv").read_text())
            self.assertNotIn("PRIVATE_SENTINEL_NEVER_IN_REPORT", destination.with_suffix(".json").read_text())
            self.assertEqual(rows[0]["actual_inference_total_tokens"], "UNAVAILABLE")