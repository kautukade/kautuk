import unittest

from kautuk_offline_agent.agent import OfflineCodingAgent


class AgentUtilityTests(unittest.TestCase):
    def test_classify_error(self) -> None:
        self.assertEqual(OfflineCodingAgent._classify_error("SyntaxError: invalid syntax"), "syntax")
        self.assertEqual(
            OfflineCodingAgent._classify_error("ModuleNotFoundError: No module named 'x'"),
            "dependency",
        )
        self.assertEqual(OfflineCodingAgent._classify_error("Traceback (most recent call last):"), "runtime")
        self.assertEqual(OfflineCodingAgent._classify_error("unexpected behavior without traceback"), "logic")
