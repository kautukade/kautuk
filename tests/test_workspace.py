import unittest

from kautuk_offline_agent.workspace import parse_structured_output


class WorkspaceParserTests(unittest.TestCase):
    def test_parse_structured_output_full_blocks(self) -> None:
        raw = """<plan>
step 1
</plan>
<reflection>
looks good
</reflection>
<files>
<file path=\"app.py\">
print('hi')
</file>
</files>
<commands>
python app.py
</commands>
<iteration_log>
first pass
</iteration_log>"""

        parsed = parse_structured_output(raw)
        self.assertEqual(parsed.plan, "step 1")
        self.assertEqual(parsed.reflection, "looks good")
        self.assertEqual(parsed.files[0].path, "app.py")
        self.assertEqual(parsed.commands, ["python app.py"])
        self.assertEqual(parsed.iteration_log, "first pass")
