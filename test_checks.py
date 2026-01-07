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

        def fake_test_wp_connection(website, tested_websites, issues, callback):
            issues.append("Could not connect to WordPress site with provided credentials")

        with patch('checks.dedup_and_trim', side_effect=lambda urls, callback=None: urls), \
             patch('checks.reset_report_progress'), \
             patch('checks.report_progress'), \
             patch('checks.get_post_title_website_from_url', return_value=(notion_post, 'Broken Title', 'example.com')), \
             patch('checks.test_wp_connection', side_effect=fake_test_wp_connection), \
             patch('checks.get_post_title', return_value=''), \
             patch('checks.get_page_property', side_effect=fake_get_page_property), \
             patch('checks.get_post_type', return_value='unexpected-type'), \
             patch.object(checks.PostWriter, 'AI_TXT_GEN_PROMPTS_BY_TOPIC', {checks.POST_TOPIC_RECIPES: {'prompt': 'value'}}), \
             patch('checks.get_post_topic_from_cats', return_value=checks.POST_TOPIC_RECIPES), \
             patch.object(checks, 'get_post_status', create=True, return_value='unexpected-status'):

            results = checks.run_checks([url], callback=lambda *_: None)

        self.assertEqual(len(results), 1)
        issues = results[0]['issues']
        self.assertIn('Could not connect to WordPress site with provided credentials', issues)
        self.assertIn('Post title is empty', issues)
        self.assertTrue(any('Post status is unexpected' in issue for issue in issues))


class RunWpImgAddChecksTests(unittest.TestCase):
    def test_run_wp_img_add_checks_with_empty_url_list(self):
        """Empty list should return empty results."""
        with patch('checks.dedup_and_trim', return_value=[]), \
             patch('checks.reset_report_progress'), \
             patch('checks.load_generic_input_folder', return_value='/fake/folder'):
            results = checks.run_wp_img_add_checks([], callback=lambda *_: None)

        self.assertEqual(results, [])

    def test_run_wp_img_add_checks_validates_post_status(self):
        """Should flag posts that aren't Published or Published+images."""
        url = "https://notion.so/test-img-add"
        notion_post = object()
        
        with patch('checks.dedup_and_trim', side_effect=lambda urls, callback=None: urls), \
             patch('checks.reset_report_progress'), \
             patch('checks.report_progress'), \
             patch('checks.load_generic_input_folder', return_value='/fake/folder'), \
             patch('checks.get_post_title_website_from_url', return_value=(notion_post, 'Test Title', 'example.com')), \
             patch('checks.test_wp_connection'), \
             patch('checks.get_post_title', return_value='Test Post'), \
             patch('checks.get_post_slug', return_value='test-post'), \
             patch('checks.get_page_property', return_value=[checks.POST_TOPIC_RECIPES]), \
             patch('checks.get_post_topic_from_cats', return_value=checks.POST_TOPIC_RECIPES), \
             patch('checks.get_post_type', return_value=checks.POST_POST_TYPE_SINGLE_ITEM_ID), \
             patch('checks.get_post_status', return_value='wrong-status'), \
             patch('checks.get_post_folder', return_value='/fake/folder'), \
             patch('checks.get_ims_in_folder', return_value=['img1.jpg']):

            results = checks.run_wp_img_add_checks([url], callback=lambda *_: None)

        self.assertEqual(len(results), 1)
        issues = results[0]['issues']
        self.assertTrue(any('Post status is unexpected' in issue for issue in issues))

    def test_run_wp_img_add_checks_detects_missing_images_in_folder(self):
        """Should report when expected image folder has no images."""
        url = "https://notion.so/no-images"
        notion_post = object()
        
        with patch('checks.dedup_and_trim', side_effect=lambda urls, callback=None: urls), \
             patch('checks.reset_report_progress'), \
             patch('checks.report_progress'), \
             patch('checks.load_generic_input_folder', return_value='/fake/folder'), \
             patch('checks.get_post_title_website_from_url', return_value=(notion_post, 'Test Title', 'example.com')), \
             patch('checks.test_wp_connection'), \
             patch('checks.get_post_title', return_value='Test Post'), \
             patch('checks.get_post_slug', return_value='test-post'), \
             patch('checks.get_page_property', return_value=[checks.POST_TOPIC_RECIPES]), \
             patch('checks.get_post_topic_from_cats', return_value=checks.POST_TOPIC_RECIPES), \
             patch('checks.get_post_type', return_value=checks.POST_POST_TYPE_SINGLE_ITEM_ID), \
             patch('checks.PostStatuses') as mock_post_statuses_class, \
             patch('checks.get_post_status', return_value='published'), \
             patch('checks.get_post_folder', return_value='/fake/folder'), \
             patch('checks.get_ims_in_folder', return_value=[]):
            mock_post_statuses = MagicMock()
            mock_post_statuses.post_done_with_post_statuses = ['published']
            mock_post_statuses_class.return_value = mock_post_statuses

            results = checks.run_wp_img_add_checks([url], callback=lambda *_: None)

        self.assertEqual(len(results), 1)
        issues = results[0]['issues']
        self.assertTrue(any('No images found in post folder' in issue for issue in issues))

    def test_run_wp_img_add_checks_handles_missing_slug(self):
        """Should capture exceptions when post slug cannot be retrieved."""
        url = "https://notion.so/no-slug"
        notion_post = object()
        
        with patch('checks.dedup_and_trim', side_effect=lambda urls, callback=None: urls), \
             patch('checks.reset_report_progress'), \
             patch('checks.report_progress'), \
             patch('checks.load_generic_input_folder', return_value='/fake/folder'), \
             patch('checks.get_post_title_website_from_url', return_value=(notion_post, 'Test Title', 'example.com')), \
             patch('checks.test_wp_connection'), \
             patch('checks.get_post_title', return_value='Test Post'), \
             patch('checks.get_post_slug', side_effect=Exception('No slug property')), \
             patch('checks.get_page_property', return_value=[checks.POST_TOPIC_RECIPES]), \
             patch('checks.get_post_topic_from_cats', return_value=checks.POST_TOPIC_RECIPES), \
             patch('checks.get_post_type', return_value=checks.POST_POST_TYPE_SINGLE_ITEM_ID), \
             patch('checks.PostStatuses') as mock_post_statuses_class, \
             patch('checks.get_post_status', return_value='published'), \
             patch('checks.get_post_folder', return_value='/fake/folder'), \
             patch('checks.get_ims_in_folder', return_value=['img1.jpg']):
            mock_post_statuses = MagicMock()
            mock_post_statuses.post_done_with_post_statuses = ['published']
            mock_post_statuses_class.return_value = mock_post_statuses

            results = checks.run_wp_img_add_checks([url], callback=lambda *_: None)

        self.assertEqual(len(results), 1)
        issues = results[0]['issues']
        self.assertTrue(any('Exception while retreiving post slug' in issue for issue in issues))


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
