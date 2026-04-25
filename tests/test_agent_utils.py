import unittest

from kautuk_offline_agent.agent import OfflineCodingAgent
from kautuk_offline_agent.memory import SessionMemory


class AgentUtilityTests(unittest.TestCase):
    def test_classify_error(self) -> None:
        self.assertEqual(OfflineCodingAgent._classify_error("SyntaxError: invalid syntax"), "syntax")
        self.assertEqual(
            OfflineCodingAgent._classify_error("ModuleNotFoundError: No module named 'x'"),
            "dependency",
        )
        self.assertEqual(OfflineCodingAgent._classify_error("Traceback (most recent call last):"), "runtime")
        self.assertEqual(OfflineCodingAgent._classify_error("unexpected behavior without traceback"), "logic")

    def test_describe_codebase(self) -> None:
        description = OfflineCodingAgent._describe_codebase(["a.py", "b.py"])
        self.assertIn("a.py", description)
        self.assertIn("b.py", description)

    def test_memory_compact(self) -> None:
        memory = SessionMemory(conversation_history=[f"item-{i}" for i in range(30)])
        memory.compact(max_items=10)
        self.assertEqual(len(memory.conversation_history), 10)
        self.assertIn("item-0", memory.conversation_summary)

    def test_select_relevant_files(self) -> None:
        files = ["src/api/server.py", "src/ui/view.py", "README.md"]
        selected = OfflineCodingAgent._select_relevant_files("update api server routes", files)
        self.assertIn("src/api/server.py", selected)
