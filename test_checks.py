import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ConfigKeeper')))

import config_utils

# Provide missing attribute referenced during import
if not hasattr(config_utils, 'c'):
    config_utils.c = None

import checks


class RunChecksTests(unittest.TestCase):
    def test_run_checks_returns_empty_for_no_urls(self):
        with patch('checks.dedup_and_trim', return_value=[]), \
             patch('checks.reset_report_progress'), \
             patch('checks.report_progress'):
            results = checks.run_checks([], callback=lambda *_: None)

        self.assertEqual(results, [])

    def test_run_checks_records_resolution_failures(self):
        url = "https://notion.so/problem"

        with patch('checks.dedup_and_trim', side_effect=lambda urls, callback=None: urls), \
             patch('checks.reset_report_progress'), \
             patch('checks.report_progress'), \
             patch('checks.get_post_title_website_from_url', side_effect=Exception('boom')):
            results = checks.run_checks([url], callback=lambda *_: None)

        self.assertEqual(len(results), 1)
        entry = results[0]
        self.assertEqual(entry['url'], url)
        self.assertIn('Exception resolving URL: boom', entry['issues'][0])

    def test_run_checks_collects_issues_when_checks_fail(self):
        url = "https://notion.so/bug"
        notion_post = object()

        def fake_get_page_property(post, prop):
            if prop == checks.POST_WP_CATEGORY_PROP:
                return [checks.POST_TOPIC_RECIPES]
            if prop == checks.POST_POST_STATUS_PROP:
                return 'unexpected-status'
            return None

        with patch('checks.dedup_and_trim', side_effect=lambda urls, callback=None: urls), \
             patch('checks.reset_report_progress'), \
             patch('checks.report_progress'), \
             patch('checks.get_post_title_website_from_url', return_value=(notion_post, 'Broken Title', 'example.com')), \
             patch('checks.WordPressClient') as mock_wp_client, \
             patch('checks.get_post_title', return_value=''), \
             patch('checks.get_page_property', side_effect=fake_get_page_property), \
             patch('checks.get_post_type', return_value='unexpected-type'), \
             patch.object(checks.PostWriter, 'AI_TXT_GEN_PROMPTS_BY_TOPIC', {checks.POST_TOPIC_RECIPES: {'prompt': 'value'}}), \
             patch('checks.get_post_topic_from_cats', return_value=checks.POST_TOPIC_RECIPES), \
             patch.object(checks, 'get_post_status', create=True, return_value='unexpected-status'):
            mock_wp_client.return_value.test_connection.return_value = False

            results = checks.run_checks([url], callback=lambda *_: None)

        self.assertEqual(len(results), 1)
        issues = results[0]['issues']
        self.assertIn('Could not connect to WordPress site with provided credentials', issues)
        self.assertIn('Post title is empty', issues)
        self.assertTrue(any('Post status is unexpected' in issue for issue in issues))


class RunWpImgAddChecksTests(unittest.TestCase):
    def test_run_wp_img_add_checks_raises_unbound_local_error(self):
        with self.assertRaises(UnboundLocalError):
            checks.run_wp_img_add_checks(object())


class FormatCheckResTests(unittest.TestCase):
    def test_format_check_res_formats_output(self):
        data = [
            {
                'url': 'https://notion.so/1',
                'title': 'First',
                'website': 'site-a',
                'issues': ['Issue A', 'Issue B'],
            },
            {
                'url': 'https://notion.so/2',
                'title': 'Second',
                'website': 'site-b',
                'issues': [],
            },
        ]

        formatted = checks.format_check_res(data)

        self.assertIn('❌Checks failed! Issues found:', formatted)
        self.assertIn('URL: https://notion.so/1', formatted)
        self.assertIn('  - Issue A', formatted)
        self.assertIn('Issues: None', formatted)


if __name__ == '__main__':
    unittest.main()
