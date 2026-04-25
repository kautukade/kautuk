import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from kautuk_offline_agent.agent import OfflineCodingAgent
from kautuk_offline_agent.memory import SessionMemory
from kautuk_offline_agent.tools import LocalTooling


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

    def test_materialize_produces_change_preview(self) -> None:
        raw = """<spec>\ns\n</spec>\n<plan>\np\n</plan>\n<reflection>\nr\n</reflection>\n<codebase_analysis>\nc\n</codebase_analysis>\n<files>\n<file path=\"a.py\">\nprint('x')\n</file>\n</files>\n<commands>\npython a.py\n</commands>\n<iteration_log>\nlog\n</iteration_log>"""
        with TemporaryDirectory() as tmp:
            tooling = LocalTooling(Path(tmp))
            _, changes = OfflineCodingAgent._materialize(raw, tooling, approve_major_changes=True)
            self.assertEqual(changes[0].status, "created")
            self.assertIn("a/a.py", changes[0].diff_preview)

    def test_materialize_blocks_major_changes_without_approval(self) -> None:
        raw = """<spec>\ns\n</spec>\n<plan>\np\n</plan>\n<reflection>\nr\n</reflection>\n<codebase_analysis>\nc\n</codebase_analysis>\n<files>\n<file path=\"a.py\">\n1\n</file>\n<file path=\"b.py\">\n2\n</file>\n</files>\n<commands>\npython a.py\n</commands>\n<iteration_log>\nlog\n</iteration_log>"""
        with TemporaryDirectory() as tmp:
            tooling = LocalTooling(Path(tmp))
            with self.assertRaises(ValueError):
                OfflineCodingAgent._materialize(
                    raw,
                    tooling,
                    approve_major_changes=False,
                    major_change_threshold=1,
                )

    def test_materialize_honors_apply_callback_decline(self) -> None:
        raw = """<spec>\ns\n</spec>\n<plan>\np\n</plan>\n<reflection>\nr\n</reflection>\n<codebase_analysis>\nc\n</codebase_analysis>\n<files>\n<file path=\"a.py\">\n1\n</file>\n</files>\n<commands>\npython a.py\n</commands>\n<iteration_log>\nlog\n</iteration_log>"""
        with TemporaryDirectory() as tmp:
            tooling = LocalTooling(Path(tmp))
            with self.assertRaises(ValueError):
                OfflineCodingAgent._materialize(
                    raw,
                    tooling,
                    apply_changes_callback=lambda _changes: False,
                )

    def test_materialize_propose_only_does_not_write_files(self) -> None:
        raw = """<spec>\ns\n</spec>\n<plan>\np\n</plan>\n<reflection>\nr\n</reflection>\n<codebase_analysis>\nc\n</codebase_analysis>\n<files>\n<file path=\"a.py\">\n1\n</file>\n</files>\n<commands>\npython a.py\n</commands>\n<iteration_log>\nlog\n</iteration_log>"""
        with TemporaryDirectory() as tmp:
            tooling = LocalTooling(Path(tmp))
            _parsed, changes = OfflineCodingAgent._materialize(raw, tooling, apply_writes=False)
            self.assertFalse((Path(tmp) / "a.py").exists())
            self.assertFalse(changes[0].applied)
