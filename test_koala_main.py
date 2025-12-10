"""
Unit tests for koala_main.py functions
"""

import unittest
import sys
import os
from unittest.mock import Mock, MagicMock, patch, call

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ConfigKeeper')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'NotionAutomator')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'NotionUtils')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'WordPress')))

from koala_main import write_post, add_wp_imgs, _update_page_ai_img_prompt, print_results_pretty
from notion_config import (
    POST_POST_STATUS_SETTING_UP_ID,
    POST_POST_STATUS_DRAFT_GENERATED_ID,
    POST_POST_STATUS_PUBLISHED_ID,
    POST_AI_IMAGE_PROMPT_PROP,
)
from post_part_constants import POST_PART_TITLE, POST_PART_INGREDIENTS


class TestWritePost(unittest.TestCase):
    """Test write_post function"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.callback = Mock()
        self.test_urls = ["https://notion.so/test-page-1", "https://notion.so/test-page-2"]
        self.mock_post = {'id': 'test-post-id'}
        self.mock_post_parts = {
            POST_PART_TITLE: 'Test Recipe Title',
            POST_PART_INGREDIENTS: 'flour, sugar, eggs'
        }
    
    @patch('koala_main.dedup_and_trim')
    @patch('koala_main.reset_report_progress')
    @patch('koala_main.run_checks')
    @patch('koala_main.format_check_res')
    @patch('koala_main.PostWriter')
    @patch('koala_main.get_post_title_website_from_url')
    @patch('koala_main.get_post_type')
    @patch('koala_main.get_page_property')
    @patch('koala_main.get_post_topic_from_cats')
    @patch('koala_main.update_post_status')
    @patch('koala_main._update_page_ai_img_prompt')
    @patch('koala_main.create_wp_post')
    @patch('koala_main.report_progress')
    def test_write_post_success(
        self,
        mock_report_progress,
        mock_create_wp_post,
        mock_update_ai_prompt,
        mock_update_status,
        mock_get_topic,
        mock_get_property,
        mock_get_type,
        mock_get_post_title,
        mock_post_writer_class,
        mock_format_check,
        mock_run_checks,
        mock_reset_progress,
        mock_dedup
    ):
        """Test successful post writing workflow"""
        # Setup mocks
        mock_dedup.return_value = ["https://notion.so/test-page-1"]
        mock_run_checks.return_value = []  # No problems
        mock_format_check.return_value = "✅ All the checks passed!"
        
        mock_post_writer = Mock()
        mock_post_writer.write_post.return_value = self.mock_post_parts
        mock_post_writer_class.return_value = mock_post_writer
        
        mock_get_post_title.return_value = (self.mock_post, 'Test Title', 'test_site')
        mock_get_type.return_value = 'recipe'
        mock_get_property.side_effect = ['Category / Subcategory', 'test-slug']
        mock_get_topic.return_value = 'recipes'
        mock_update_status.return_value = self.mock_post
        mock_create_wp_post.return_value = {'link': 'https://wordpress.com/test-post'}
        
        # Execute
        results = write_post(self.test_urls, do_run_checks=True, test=False, callback=self.callback)
        
        # Verify
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['Test Recipe Title'], 'https://wordpress.com/test-post')
        
        # Verify workflow steps
        mock_run_checks.assert_called_once()
        mock_post_writer.write_post.assert_called_once()
        self.assertEqual(mock_update_status.call_count, 3)  # Three status updates
        mock_create_wp_post.assert_called_once()
        mock_update_ai_prompt.assert_called_once()
    
    @patch('koala_main.dedup_and_trim')
    @patch('koala_main.reset_report_progress')
    @patch('koala_main.run_checks')
    @patch('koala_main.format_check_res')
    def test_write_post_with_check_problems(
        self,
        mock_format_check,
        mock_run_checks,
        mock_reset_progress,
        mock_dedup
    ):
        """Test that write_post stops when checks find problems"""
        mock_dedup.return_value = ["https://notion.so/test-page-1"]
        mock_run_checks.return_value = [{'url': 'test', 'issue': 'Problem found'}]
        mock_format_check.return_value = "❌Checks failed! Issues found"
        
        results = write_post(self.test_urls, do_run_checks=True, test=False, callback=self.callback)
        
        # Should return empty results without proceeding
        self.assertEqual(results, [])
        self.callback.assert_any_call('\n\n[ERROR][write_post] Cannot proceed due to the issues found ☝️')
    
    @patch('koala_main.dedup_and_trim')
    @patch('koala_main.reset_report_progress')
    @patch('koala_main.run_checks')
    @patch('koala_main.format_check_res')
    @patch('koala_main.PostWriter')
    @patch('koala_main.get_post_title_website_from_url')
    def test_write_post_notion_url_resolution_fails(
        self,
        mock_get_post_title,
        mock_post_writer_class,
        mock_format_check,
        mock_run_checks,
        mock_reset_progress,
        mock_dedup
    ):
        """Test error handling when Notion URL cannot be resolved"""
        mock_dedup.return_value = ["https://notion.so/test-page-1"]
        mock_run_checks.return_value = []
        mock_format_check.return_value = "No problems"
        
        mock_post_writer = Mock()
        mock_post_writer_class.return_value = mock_post_writer
        
        # Return None for post
        mock_get_post_title.return_value = (None, None, None)
        
        with self.assertRaises(ValueError) as context:
            write_post(self.test_urls, do_run_checks=True, test=False, callback=self.callback)
        
        self.assertIn('Could not resolve Notion URL', str(context.exception))
    
    @patch('koala_main.dedup_and_trim')
    @patch('koala_main.reset_report_progress')
    @patch('koala_main.run_checks')
    @patch('koala_main.format_check_res')
    @patch('koala_main.PostWriter')
    @patch('koala_main.get_post_title_website_from_url')
    def test_write_post_no_website(
        self,
        mock_get_post_title,
        mock_post_writer_class,
        mock_format_check,
        mock_run_checks,
        mock_reset_progress,
        mock_dedup
    ):
        """Test error handling when website cannot be determined"""
        mock_dedup.return_value = ["https://notion.so/test-page-1"]
        mock_run_checks.return_value = []
        mock_format_check.return_value = "✅ All the checks passed!"
        
        mock_post_writer = Mock()
        mock_post_writer_class.return_value = mock_post_writer
        
        # Return post but no website
        mock_get_post_title.return_value = (self.mock_post, 'Test Title', None)
        
        with self.assertRaises(ValueError) as context:
            write_post(self.test_urls, do_run_checks=True, test=False, callback=self.callback)
        
        self.assertIn('Could not determine website', str(context.exception))
    
    @patch('koala_main.dedup_and_trim')
    @patch('koala_main.reset_report_progress')
    @patch('koala_main.run_checks')
    @patch('koala_main.format_check_res')
    @patch('koala_main.PostWriter')
    @patch('koala_main.get_post_title_website_from_url')
    @patch('koala_main.get_post_type')
    @patch('koala_main.get_page_property')
    @patch('koala_main.get_post_topic_from_cats')
    @patch('koala_main.update_post_status')
    def test_write_post_status_update_fails(
        self,
        mock_update_status,
        mock_get_topic,
        mock_get_property,
        mock_get_type,
        mock_get_post_title,
        mock_post_writer_class,
        mock_format_check,
        mock_run_checks,
        mock_reset_progress,
        mock_dedup
    ):
        """Test error handling when status update fails"""
        mock_dedup.return_value = ["https://notion.so/test-page-1"]
        mock_run_checks.return_value = []
        mock_format_check.return_value = "✅ All the checks passed!"
        
        mock_post_writer = Mock()
        mock_post_writer_class.return_value = mock_post_writer
        
        mock_get_post_title.return_value = (self.mock_post, 'Test Title', 'test_site')
        mock_get_type.return_value = 'recipe'
        mock_get_property.side_effect = ['Category', 'test-slug']
        mock_get_topic.return_value = 'recipes'
        
        # First status update fails
        mock_update_status.return_value = None
        
        with self.assertRaises(ValueError) as context:
            write_post(self.test_urls, do_run_checks=True, test=False, callback=self.callback)
        
        self.assertIn('Post status #1 was not updated', str(context.exception))
    
    @patch('koala_main.dedup_and_trim')
    @patch('koala_main.reset_report_progress')
    @patch('koala_main.run_checks')
    @patch('koala_main.format_check_res')
    @patch('koala_main.PostWriter')
    @patch('koala_main.get_post_title_website_from_url')
    @patch('koala_main.get_post_type')
    @patch('koala_main.get_page_property')
    @patch('koala_main.get_post_topic_from_cats')
    @patch('koala_main.update_post_status')
    @patch('koala_main._update_page_ai_img_prompt')
    @patch('koala_main.create_wp_post')
    def test_write_post_wp_creation_fails(
        self,
        mock_create_wp_post,
        mock_update_ai_prompt,
        mock_update_status,
        mock_get_topic,
        mock_get_property,
        mock_get_type,
        mock_get_post_title,
        mock_post_writer_class,
        mock_format_check,
        mock_run_checks,
        mock_reset_progress,
        mock_dedup
    ):
        """Test error handling when WordPress post creation fails"""
        mock_dedup.return_value = ["https://notion.so/test-page-1"]
        mock_run_checks.return_value = []
        mock_format_check.return_value = "✅ All the checks passed!"
        
        mock_post_writer = Mock()
        mock_post_writer.write_post.return_value = self.mock_post_parts
        mock_post_writer_class.return_value = mock_post_writer
        
        mock_get_post_title.return_value = (self.mock_post, 'Test Title', 'test_site')
        mock_get_type.return_value = 'recipe'
        mock_get_property.side_effect = ['Category', 'test-slug']
        mock_get_topic.return_value = 'recipes'
        mock_update_status.return_value = self.mock_post
        
        # WordPress post creation returns no link
        mock_create_wp_post.return_value = {}
        
        with self.assertRaises(ValueError) as context:
            write_post(self.test_urls, do_run_checks=True, test=False, callback=self.callback)
        
        self.assertIn('WordPress post was not created', str(context.exception))
    
    @patch('koala_main.dedup_and_trim')
    @patch('koala_main.reset_report_progress')
    @patch('koala_main.run_checks')
    @patch('koala_main.format_check_res')
    def test_write_post_test_mode(
        self,
        mock_format_check,
        mock_run_checks,
        mock_reset_progress,
        mock_dedup
    ):
        """Test that test mode is indicated in callback"""
        mock_dedup.return_value = []
        mock_run_checks.return_value = []
        mock_format_check.return_value = "✅ All the checks passed!"
        
        write_post([], do_run_checks=False, test=True, callback=self.callback)
        
        self.callback.assert_any_call('\n[INFO][write_post] Running in TEST mode!\n')
    
    @patch('koala_main.dedup_and_trim')
    @patch('koala_main.reset_report_progress')
    @patch('koala_main.run_checks')
    @patch('koala_main.format_check_res')
    @patch('koala_main.PostWriter')
    @patch('koala_main.get_post_title_website_from_url')
    @patch('koala_main.get_post_type')
    @patch('koala_main.get_page_property')
    @patch('koala_main.get_post_topic_from_cats')
    @patch('koala_main.update_post_status')
    @patch('koala_main._update_page_ai_img_prompt')
    @patch('koala_main.create_wp_post')
    @patch('koala_main.report_progress')
    def test_write_post_multiple_urls(
        self,
        mock_report_progress,
        mock_create_wp_post,
        mock_update_ai_prompt,
        mock_update_status,
        mock_get_topic,
        mock_get_property,
        mock_get_type,
        mock_get_post_title,
        mock_post_writer_class,
        mock_format_check,
        mock_run_checks,
        mock_reset_progress,
        mock_dedup
    ):
        """Test processing multiple URLs"""
        mock_dedup.return_value = ["https://notion.so/page-1", "https://notion.so/page-2"]
        mock_run_checks.return_value = []
        mock_format_check.return_value = "✅ All the checks passed!"
        
        mock_post_writer = Mock()
        mock_post_writer.write_post.return_value = self.mock_post_parts
        mock_post_writer_class.return_value = mock_post_writer
        
        mock_get_post_title.side_effect = [
            (self.mock_post, 'Title 1', 'site1'),
            (self.mock_post, 'Title 2', 'site2')
        ]
        mock_get_type.return_value = 'recipe'
        mock_get_property.side_effect = ['Cat1', 'slug1', 'Cat2', 'slug2']
        mock_get_topic.return_value = 'recipes'
        mock_update_status.return_value = self.mock_post
        mock_create_wp_post.side_effect = [
            {'link': 'https://wp.com/post1'},
            {'link': 'https://wp.com/post2'}
        ]
        
        results = write_post(["url1", "url2"], do_run_checks=True, test=False, callback=self.callback)
        
        self.assertEqual(len(results), 2)
        self.assertEqual(mock_post_writer.write_post.call_count, 2)
        self.assertEqual(mock_create_wp_post.call_count, 2)


class TestUpdatePageAiImgPrompt(unittest.TestCase):
    """Test _update_page_ai_img_prompt function"""
    
    def setUp(self):
        self.callback = Mock()
        self.mock_post = {'id': 'test-post-id'}
    
    @patch('koala_main.update_post_ai_img_prompt')
    def test_update_prompt_success(self, mock_update):
        """Test successful prompt update"""
        mock_update.return_value = self.mock_post
        
        result = _update_page_ai_img_prompt(
            self.mock_post,
            "flour, sugar, eggs",
            test=False,
            callback=self.callback
        )
        
        self.assertEqual(result, self.mock_post)
        mock_update.assert_called_once_with(self.mock_post, "flour, sugar, eggs")
        self.callback.assert_any_call(f"[INFO][_update_page_ai_img_prompt] '{POST_AI_IMAGE_PROMPT_PROP}' updated successfully.")
    
    @patch('koala_main.update_post_ai_img_prompt')
    def test_update_prompt_test_mode(self, mock_update):
        """Test prompt update in test mode"""
        result = _update_page_ai_img_prompt(
            self.mock_post,
            "flour, sugar, eggs",
            test=True,
            callback=self.callback
        )
        
        mock_update.assert_not_called()
        self.callback.assert_any_call('[TEST][_update_page_ai_img_prompt] No update is made. Would set to: flour, sugar, eggs')
    
    def test_update_prompt_empty_string(self):
        """Test that empty prompt skips update"""
        result = _update_page_ai_img_prompt(
            self.mock_post,
            "",
            test=False,
            callback=self.callback
        )
        
        self.assertIsNone(result)
        self.callback.assert_any_call('[WARNING][_update_page_ai_img_prompt] New prompt is empty, skipping update.')
    
    def test_update_prompt_whitespace_only(self):
        """Test that whitespace-only prompt skips update"""
        result = _update_page_ai_img_prompt(
            self.mock_post,
            "   \n\t  ",
            test=False,
            callback=self.callback
        )
        
        self.assertIsNone(result)
        self.callback.assert_any_call('[WARNING][_update_page_ai_img_prompt] New prompt is empty, skipping update.')
    
    @patch('koala_main.update_post_ai_img_prompt')
    def test_update_prompt_list_input(self, mock_update):
        """Test that list input is joined into string"""
        mock_update.return_value = self.mock_post
        
        result = _update_page_ai_img_prompt(
            self.mock_post,
            ["flour", "sugar", "eggs"],
            test=False,
            callback=self.callback
        )
        
        # Should join list with spaces
        mock_update.assert_called_once_with(self.mock_post, "flour sugar eggs")
    
    def test_update_prompt_invalid_type(self):
        """Test error when prompt is not string or list"""
        with self.assertRaises(ValueError) as context:
            _update_page_ai_img_prompt(
                self.mock_post,
                123,  # Invalid type (int)
                test=False,
                callback=self.callback
            )
        
        self.assertIn('must be a string or list', str(context.exception))
    
    def test_update_prompt_invalid_type_dict(self):
        """Test error when prompt is a dict"""
        with self.assertRaises(ValueError) as context:
            _update_page_ai_img_prompt(
                self.mock_post,
                {"key": "value"},  # Invalid type (dict)
                test=False,
                callback=self.callback
            )
        
        self.assertIn('must be a string or list', str(context.exception))
    
    @patch('koala_main.update_post_ai_img_prompt')
    def test_update_prompt_update_fails(self, mock_update):
        """Test error handling when update fails"""
        mock_update.return_value = None
        
        with self.assertRaises(ValueError) as context:
            _update_page_ai_img_prompt(
                self.mock_post,
                "flour, sugar, eggs",
                test=False,
                callback=self.callback
            )
        
        self.assertIn('Failed to update', str(context.exception))


class TestAddWpImgs(unittest.TestCase):
    """Test add_wp_imgs function"""
    
    def setUp(self):
        self.callback = Mock()
        self.test_urls = ["https://notion.so/test-page"]
        self.mock_post = {'id': 'test-post-id'}
    
    @patch('koala_main.dedup_and_trim')
    @patch('koala_main.reset_report_progress')
    @patch('koala_main.get_post_title_website_from_url')
    @patch('koala_main.add_images_to_wp_post')
    @patch('koala_main.report_progress')
    def test_add_wp_imgs_success(
        self,
        mock_report_progress,
        mock_add_images,
        mock_get_post_title,
        mock_reset_progress,
        mock_dedup
    ):
        """Test successful image addition"""
        mock_dedup.return_value = ["https://notion.so/test-page"]
        mock_get_post_title.return_value = (self.mock_post, 'Test Post', 'test_site')
        mock_add_images.return_value = 'https://wordpress.com/test-post'
        
        results = add_wp_imgs(self.test_urls, do_run_checks=False, test=True, callback=self.callback)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['Test Post'], 'https://wordpress.com/test-post')
        mock_add_images.assert_called_once()
    
    @patch('koala_main.dedup_and_trim')
    @patch('koala_main.reset_report_progress')
    @patch('koala_main.get_post_title_website_from_url')
    def test_add_wp_imgs_notion_url_fails(
        self,
        mock_get_post_title,
        mock_reset_progress,
        mock_dedup
    ):
        """Test error handling when Notion URL cannot be resolved"""
        mock_dedup.return_value = ["https://notion.so/test-page"]
        mock_get_post_title.return_value = (None, None, None)
        
        with self.assertRaises(ValueError) as context:
            add_wp_imgs(self.test_urls, do_run_checks=False, test=False, callback=self.callback)
        
        self.assertIn('Could not resolve Notion URL', str(context.exception))
    
    @patch('koala_main.dedup_and_trim')
    @patch('koala_main.reset_report_progress')
    @patch('koala_main.get_post_title_website_from_url')
    def test_add_wp_imgs_no_website(
        self,
        mock_get_post_title,
        mock_reset_progress,
        mock_dedup
    ):
        """Test error handling when website cannot be determined"""
        mock_dedup.return_value = ["https://notion.so/test-page"]
        mock_get_post_title.return_value = (self.mock_post, 'Test Post', None)
        
        with self.assertRaises(ValueError) as context:
            add_wp_imgs(self.test_urls, do_run_checks=False, test=False, callback=self.callback)
        
        self.assertIn('Could not determine website', str(context.exception))


class TestPrintResultsPretty(unittest.TestCase):
    """Test print_results_pretty function"""
    
    @patch('builtins.print')
    def test_print_results_pretty(self, mock_print):
        """Test pretty printing of results"""
        results = [
            {'Test Post 1': 'https://wp.com/post1'},
            {'Test Post 2': 'https://wp.com/post2'}
        ]
        
        print_results_pretty(results)
        
        # Verify header and footer printed
        calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any('Koala Writer Results' in call for call in calls))
        
        # Verify both results printed
        self.assertTrue(any('Test Post 1' in call for call in calls))
        self.assertTrue(any('Test Post 2' in call for call in calls))
    
    @patch('builtins.print')
    def test_print_results_empty(self, mock_print):
        """Test printing empty results"""
        print_results_pretty([])
        
        # Should still print header and footer
        self.assertTrue(mock_print.called)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestWritePost))
    suite.addTests(loader.loadTestsFromTestCase(TestUpdatePageAiImgPrompt))
    suite.addTests(loader.loadTestsFromTestCase(TestAddWpImgs))
    suite.addTests(loader.loadTestsFromTestCase(TestPrintResultsPretty))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == '__main__':
    result = run_tests()
    
    # Print summary
    print("\n" + "="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print("="*70)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
