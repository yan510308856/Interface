from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from experiment import qwen_native_debug, runner


ROOT = Path(__file__).resolve().parents[2]


class FakeNativeModel:
    def __init__(self) -> None:
        self.turn = 0

    def generate(self, messages, tools):
        outputs = [
            '<tool_call>{"name":"read_file","arguments":{"path":"sample.py"}}</tool_call>',
            '<tool_call>{"name":"replace_text","arguments":{"path":"sample.py","old_text":"VALUE = 1","new_text":"VALUE = 2"}}</tool_call>',
            '<tool_call>{"name":"run_process","arguments":{"argv":["python3","-m","unittest","tests.test_sample"],"timeout_seconds":10}}</tool_call>',
            "The requested change is complete and the unit test passes.",
        ]
        text = outputs[self.turn]
        self.turn += 1
        return {
            "text": text,
            "prompt_tokens": 10,
            "output_tokens": 10,
            "generation_seconds": 0.001,
        }


class QwenNativeDebugTests(unittest.TestCase):
    def test_parser_accepts_qwen_xml_and_string_arguments(self):
        text = (
            'prefix <tool_call>{"name":"read_file","arguments":'
            '"{\\"path\\": \\"sample.py\\"}"}</tool_call>'
        )
        self.assertEqual(
            [{"name": "read_file", "arguments": {"path": "sample.py"}}],
            qwen_native_debug.parse_tool_calls(text),
        )

    def test_parser_rejects_malformed_calls(self):
        self.assertEqual([], qwen_native_debug.parse_tool_calls("not a tool call"))
        self.assertEqual(
            [],
            qwen_native_debug.parse_tool_calls(
                '<tool_call>{"name":"read_file","arguments":[]}</tool_call>'
            ),
        )

    def test_native_tool_schema_uses_canonical_names(self):
        config = runner.build_effective_config(
            ROOT / "experiment/configs/r6p_pilot_clean.yaml",
            interface="atomic",
            model="fake",
            output_root="/tmp/qwen-native-schema-test",
        )
        tools = qwen_native_debug.native_tools(config["operations"])
        self.assertEqual(
            set(qwen_native_debug.DEBUG_OPERATIONS),
            {tool["function"]["name"] for tool in tools},
        )
        read_file = next(
            tool for tool in tools if tool["function"]["name"] == "read_file"
        )
        self.assertIn("path", read_file["function"]["parameters"]["required"])

    def test_fake_native_loop_solves_clean_fixture(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = runner.build_effective_config(
                ROOT / "experiment/configs/r6p_pilot_clean.yaml",
                interface="atomic",
                model="fake",
                output_root=temporary,
                episode_id="native-debug-test",
            )
            output = qwen_native_debug.run_clean_debug(config, FakeNativeModel())
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual("PASS", summary["functional_status"])
            self.assertEqual(3, summary["tool_calls"])
            self.assertEqual(0, summary["backend_failed_requests"])
            self.assertIn("VALUE = 2", (output / "final.patch").read_text())


if __name__ == "__main__":
    unittest.main()
