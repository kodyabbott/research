"""Extraction rules: one test per rule plus the edge cases models actually produce."""

import unittest

import context  # noqa: F401

from harness.extract import MAX_CODE_BYTES, Extraction, extract, fenced_blocks, indent_body, \
    strip_repl_noise

PROMPT = (
    "from typing import List\n"
    "\n"
    "\n"
    "def has_close_elements(numbers: List[float], threshold: float) -> bool:\n"
    '    """ Check if any two numbers are closer than threshold. """\n'
)
ENTRY = "has_close_elements"


class FenceRuleCase(unittest.TestCase):
    def test_fence_entry_picks_first_block_defining_the_entry_point(self):
        content = (
            "Here are some helpers first.\n"
            "```python\n"
            "def helper(x):\n"
            "    return x\n"
            "```\n"
            "And the solution:\n"
            "```python\n"
            "def has_close_elements(numbers, threshold):\n"
            "    return False\n"
            "```\n"
            "```python\n"
            "def has_close_elements(numbers, threshold):\n"
            "    return True\n"
            "```\n"
        )
        result = extract(content, ENTRY, PROMPT)
        self.assertEqual(result.rule, "fence-entry")
        self.assertEqual(result.blocks, 3)
        self.assertIn("return False", result.code)
        self.assertNotIn("return True", result.code)
        self.assertFalse(result.completion_prefixed)

    def test_fence_entry_accepts_space_before_parenthesis(self):
        content = "```python\ndef has_close_elements (numbers, threshold):\n    return False\n```"
        self.assertEqual(extract(content, ENTRY, PROMPT).rule, "fence-entry")

    def test_fence_language_variants_all_count_as_blocks(self):
        for language in ("python", "py", "Python", "python3", "", "PYTHON"):
            content = f"```{language}\ndef has_close_elements(n, t):\n    return False\n```"
            with self.subTest(language=language):
                self.assertEqual(extract(content, ENTRY, PROMPT).rule, "fence-entry")

    def test_tilde_fences_are_recognised(self):
        content = "~~~python\ndef has_close_elements(n, t):\n    return False\n~~~"
        self.assertEqual(extract(content, ENTRY, PROMPT).rule, "fence-entry")

    def test_fence_last_used_when_no_block_defines_the_entry_point(self):
        content = (
            "```text\nsome notes\n```\n"
            "```python\ndef other(x):\n    return x\n```\n"
        )
        result = extract(content, ENTRY, PROMPT)
        self.assertEqual(result.rule, "fence-last")
        self.assertTrue(result.completion_prefixed)
        self.assertIn("def other", result.code)
        self.assertIn("def has_close_elements", result.code)  # prompt prepended

    def test_unterminated_final_fence_is_still_extracted(self):
        content = "Sure.\n```python\ndef has_close_elements(n, t):\n    return False\n"
        result = extract(content, ENTRY, PROMPT)
        self.assertEqual(result.rule, "fence-entry")
        self.assertIn("return False", result.code)

    def test_indented_fence_markers(self):
        content = "  ```python\n  def has_close_elements(n, t):\n      return False\n  ```"
        self.assertEqual(extract(content, ENTRY, PROMPT).rule, "fence-entry")


class RawRuleCase(unittest.TestCase):
    def test_raw_entry_uses_whole_content(self):
        content = "def has_close_elements(numbers, threshold):\n    return False\n"
        result = extract(content, ENTRY, PROMPT)
        self.assertEqual(result.rule, "raw-entry")
        self.assertFalse(result.completion_prefixed)
        self.assertEqual(result.code, content)

    def test_raw_body_is_indented_and_appended_to_the_prompt(self):
        content = "sorted_numbers = sorted(numbers)\nreturn len(sorted_numbers) > 0\n"
        result = extract(content, ENTRY, PROMPT)
        self.assertEqual(result.rule, "raw-body")
        self.assertTrue(result.completion_prefixed)
        self.assertTrue(result.code.startswith(PROMPT.rstrip("\n")))
        self.assertIn("    sorted_numbers = sorted(numbers)", result.code)
        compile(result.code, "<test>", "exec")  # the assembled program must parse

    def test_already_indented_body_is_not_double_indented(self):
        content = "    return len(numbers) > 0\n"
        result = extract(content, ENTRY, PROMPT)
        self.assertEqual(result.rule, "raw-body")
        self.assertNotIn("        return", result.code)
        compile(result.code, "<test>", "exec")

    def test_raw_body_disabled_for_mbpp(self):
        result = extract("return 1\n", "f", "", allow_body_completion=False)
        self.assertEqual(result.rule, "empty")
        self.assertFalse(result.usable)

    def test_unfenced_foreign_def_is_not_usable(self):
        # DESIGN rule 3 requires the entry point; rule 4 requires no `def` at all.
        result = extract("def other(x):\n    return x\n", ENTRY, PROMPT)
        self.assertEqual(result.rule, "empty")
        self.assertFalse(result.usable)


class EdgeCase(unittest.TestCase):
    def test_empty_content(self):
        for content in (None, "", "   \n\n"):
            with self.subTest(content=content):
                result = extract(content, ENTRY, PROMPT)
                self.assertEqual(result.rule, "empty")
                self.assertFalse(result.usable)

    def test_prose_only_content_is_treated_as_a_body_for_humaneval(self):
        # No `def` anywhere, so rule 4 applies; the result will not compile and is graded as a
        # syntax error rather than silently scored as no-code.
        result = extract("I cannot help with that request.", ENTRY, PROMPT)
        self.assertEqual(result.rule, "raw-body")

    def test_repl_noise_is_stripped(self):
        content = ("```python\n"
                   ">>> def has_close_elements(n, t):\n"
                   "...     return False\n"
                   "```")
        result = extract(content, ENTRY, PROMPT)
        self.assertEqual(result.rule, "fence-entry")
        self.assertNotIn(">>>", result.code)
        compile(result.code, "<test>", "exec")

    def test_repl_stripping_leaves_ordinary_code_alone(self):
        code = "x = 1\n# >>> not a prompt\n"
        self.assertEqual(strip_repl_noise(code), code)

    def test_size_cap(self):
        content = "```python\ndef has_close_elements(n, t):\n" + ("    # pad\n" * 40000) + "```"
        self.assertGreater(len(content), MAX_CODE_BYTES)
        result = extract(content, ENTRY, PROMPT)
        self.assertEqual(result.rule, "too-large")
        self.assertFalse(result.usable)
        self.assertEqual(result.code, "")

    def test_completion_prefix_only_when_prompt_defines_the_entry_point(self):
        content = "```python\ndef other(x):\n    return x\n```"
        result = extract(content, "missing_entry", "no def here")
        self.assertEqual(result.rule, "fence-last")
        self.assertFalse(result.completion_prefixed)

    def test_fenced_blocks_reports_language_and_body(self):
        blocks = fenced_blocks("```python\na = 1\n```\n```\nb = 2\n```")
        self.assertEqual(blocks, [("python", "a = 1"), ("", "b = 2")])

    def test_indent_body_preserves_blank_lines(self):
        self.assertEqual(indent_body("a = 1\n\nb = 2"), "    a = 1\n\n    b = 2")

    def test_extraction_dataclass_usable_flag(self):
        self.assertFalse(Extraction("", "empty").usable)
        self.assertTrue(Extraction("x = 1", "raw-entry").usable)


if __name__ == "__main__":
    unittest.main()
