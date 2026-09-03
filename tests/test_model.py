from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch

from experiment.model import Model


CONFIG = {"name": "test-model", "base_url": "http://model/v1"}


class ModelTests(unittest.TestCase):
    def response(self, message: dict[str, object]) -> io.BytesIO:
        return io.BytesIO(json.dumps({
            "choices": [{"message": message}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 7},
        }).encode())

    def request_body(self, mocked_urlopen) -> dict[str, object]:
        request = mocked_urlopen.call_args.args[0]
        return json.loads(request.data)

    def test_generate_without_tools_omits_native_tool_fields(self):
        with patch("experiment.model.urllib.request.urlopen", return_value=self.response({"content": "done"})) as urlopen:
            generation = Model(CONFIG).generate([{"role": "user", "content": "task"}], 1)
        body = self.request_body(urlopen)
        self.assertNotIn("tools", body)
        self.assertNotIn("tool_choice", body)
        self.assertEqual("done", generation.text)
        self.assertEqual([], generation.tool_calls)

    def test_generate_parses_native_tool_calls_and_null_content(self):
        tools = [{"type": "function", "function": {"name": "read_file"}}]
        tool_calls = [{
            "id": "call-1",
            "type": "function",
            "function": {"name": "read_file", "arguments": '{"path":"README.md"}'},
        }]
        with patch("experiment.model.urllib.request.urlopen", return_value=self.response({
            "content": None, "tool_calls": tool_calls,
        })) as urlopen:
            generation = Model(CONFIG).generate(
                [{"role": "user", "content": "task"}], 1, tools=tools, tool_choice="auto",
            )
        body = self.request_body(urlopen)
        self.assertEqual(tools, body["tools"])
        self.assertEqual("auto", body["tool_choice"])
        self.assertEqual("", generation.text)
        self.assertEqual(tool_calls, generation.tool_calls)
        self.assertEqual("call-1", generation.tool_calls[0]["id"])

    def test_count_tokens_sends_tools_only_for_atomic_context(self):
        tools = [{"type": "function", "function": {"name": "read_file"}}]
        messages = [{"role": "user", "content": "task"}]
        with patch("experiment.model.urllib.request.urlopen", side_effect=[
            io.BytesIO(json.dumps({"count": 17}).encode()),
            io.BytesIO(json.dumps({"count": 9}).encode()),
        ]) as urlopen:
            self.assertEqual(17, Model(CONFIG).count_tokens(messages, tools=tools))
            self.assertEqual(9, Model(CONFIG).count_tokens(messages))

        first_body = json.loads(urlopen.call_args_list[0].args[0].data)
        second_body = json.loads(urlopen.call_args_list[1].args[0].data)
        self.assertEqual(CONFIG["name"], first_body["model"])
        self.assertEqual(messages, first_body["messages"])
        self.assertEqual(tools, first_body["tools"])
        self.assertNotIn("tools", second_body)
        self.assertTrue(urlopen.call_args_list[0].args[0].full_url.endswith("/tokenize"))


if __name__ == "__main__":
    unittest.main()
