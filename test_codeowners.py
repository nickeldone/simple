"""
Unit tests for codeowners.py — CODEOWNERS parsing and path-to-owner mapping.
"""

import unittest
from codeowners import parse_codeowners, owners_for_path, match_path


class TestParseCodeowners(unittest.TestCase):
    """Tests for parse_codeowners()."""

    def test_empty_file(self):
        self.assertEqual(parse_codeowners(""), [])

    def test_blank_lines_and_comments_skipped(self):
        content = "\n# This is a comment\n\n  # indented comment\n"
        self.assertEqual(parse_codeowners(content), [])

    def test_global_owner(self):
        content = "* @global-owner\n"
        rules = parse_codeowners(content)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["pattern"], "*")
        self.assertEqual(rules[0]["owners"], ["@global-owner"])

    def test_multiple_owners(self):
        content = "*.js @frontend @js-team\n"
        rules = parse_codeowners(content)
        self.assertEqual(rules[0]["owners"], ["@frontend", "@js-team"])

    def test_pattern_no_owners(self):
        """A pattern with no owners marks the path as unowned."""
        content = "/build/\n"
        rules = parse_codeowners(content)
        self.assertEqual(rules[0]["pattern"], "/build/")
        self.assertEqual(rules[0]["owners"], [])

    def test_inline_comment_stripped(self):
        content = "*.py @python-team # Python files\n"
        rules = parse_codeowners(content)
        self.assertEqual(rules[0]["pattern"], "*.py")
        self.assertEqual(rules[0]["owners"], ["@python-team"])

    def test_email_owner(self):
        content = "/docs/ user@example.com\n"
        rules = parse_codeowners(content)
        self.assertEqual(rules[0]["owners"], ["user@example.com"])

    def test_line_numbers_recorded(self):
        content = "# comment\n\n*.md @docs\n*.rb @ruby\n"
        rules = parse_codeowners(content)
        self.assertEqual(rules[0]["line_number"], 3)
        self.assertEqual(rules[1]["line_number"], 4)

    def test_multiple_rules(self):
        content = (
            "# Global rule\n"
            "* @default\n"
            "*.js @js-team\n"
            "/docs/ @docs-team\n"
        )
        rules = parse_codeowners(content)
        self.assertEqual(len(rules), 3)
        self.assertEqual(rules[0]["pattern"], "*")
        self.assertEqual(rules[1]["pattern"], "*.js")
        self.assertEqual(rules[2]["pattern"], "/docs/")

    def test_org_team_owner(self):
        content = "*.go @my-org/backend\n"
        rules = parse_codeowners(content)
        self.assertEqual(rules[0]["owners"], ["@my-org/backend"])


class TestMatchPath(unittest.TestCase):
    """Tests for match_path()."""

    def test_wildcard_matches_any_file(self):
        self.assertTrue(match_path("README.md", "*"))
        self.assertTrue(match_path("src/main.py", "*"))

    def test_extension_pattern(self):
        self.assertTrue(match_path("app.js", "*.js"))
        self.assertFalse(match_path("app.py", "*.js"))

    def test_anchored_directory(self):
        self.assertTrue(match_path("docs/guide.md", "/docs/"))
        self.assertTrue(match_path("docs/nested/page.md", "/docs/"))
        self.assertFalse(match_path("other/docs/page.md", "/docs/"))

    def test_anchored_file(self):
        self.assertTrue(match_path("CODEOWNERS", "/CODEOWNERS"))
        self.assertFalse(match_path("docs/CODEOWNERS", "/CODEOWNERS"))

    def test_double_star(self):
        self.assertTrue(match_path("apps/frontend/src/index.js", "apps/**"))
        self.assertTrue(match_path("apps/backend/main.go", "apps/**"))
        self.assertFalse(match_path("lib/utils.go", "apps/**"))

    def test_unanchored_pattern_matches_any_depth(self):
        self.assertTrue(match_path("tests/unit/test_foo.py", "tests/"))
        self.assertTrue(match_path("tests/integration/test_bar.py", "tests/"))

    def test_question_mark(self):
        self.assertTrue(match_path("src/a.py", "src/?.py"))
        self.assertFalse(match_path("src/ab.py", "src/?.py"))


class TestOwnersForPath(unittest.TestCase):
    """Tests for owners_for_path() — last-match-wins semantics."""

    def _rules(self, content):
        return parse_codeowners(content)

    def test_global_owner_fallback(self):
        rules = self._rules("* @default\n")
        self.assertEqual(owners_for_path("anything/here.txt", rules), ["@default"])

    def test_last_match_wins(self):
        rules = self._rules(
            "* @default\n"
            "*.js @js-team\n"
        )
        self.assertEqual(owners_for_path("app.js", rules), ["@js-team"])
        self.assertEqual(owners_for_path("app.py", rules), ["@default"])

    def test_more_specific_rule_overrides(self):
        rules = self._rules(
            "* @default\n"
            "/docs/ @docs-team\n"
        )
        self.assertEqual(owners_for_path("docs/readme.md", rules), ["@docs-team"])
        self.assertEqual(owners_for_path("src/main.py", rules), ["@default"])

    def test_unowned_path(self):
        """A pattern with no owners explicitly un-owns the path."""
        rules = self._rules(
            "* @default\n"
            "/build/\n"         # no owners → unowned
        )
        self.assertEqual(owners_for_path("build/output.bin", rules), [])

    def test_no_matching_rule(self):
        rules = self._rules("*.js @js-team\n")
        self.assertEqual(owners_for_path("README.md", rules), [])

    def test_multiple_owners_returned(self):
        rules = self._rules("* @alice @bob\n")
        self.assertEqual(owners_for_path("foo.py", rules), ["@alice", "@bob"])

    def test_deep_path_with_global_rule(self):
        rules = self._rules("* @owner\n")
        self.assertEqual(owners_for_path("a/b/c/d/file.txt", rules), ["@owner"])

    def test_directory_rule_matches_nested_files(self):
        rules = self._rules("/src/ @src-team\n")
        self.assertEqual(owners_for_path("src/utils/helpers.py", rules), ["@src-team"])

    def test_empty_rules(self):
        self.assertEqual(owners_for_path("anything.py", []), [])


if __name__ == "__main__":
    unittest.main()
