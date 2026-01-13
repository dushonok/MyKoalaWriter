"""
Unit tests for wp_post_gen.py
"""

import unittest
import sys
import os
from unittest.mock import Mock, MagicMock, patch

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ConfigKeeper')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'WordPress')))

from wp_post_gen import create_wp_post
from post_part_constants import (
    POST_PART_TITLE,
    POST_PART_INTRO,
    POST_PART_EQUIPMENT_MUST,
    POST_PART_EQUIPMENT_NICE,
    POST_PART_INGREDIENTS,
    POST_PART_INSTRUCTIONS,
    POST_PART_GOOD_TO_KNOW,
    POST_PART_CONCLUSION,
    POST_PART_ITEMS,
)
from ai_gen_config import POST_TOPIC_RECIPES


class TestCreateWpPostRecipe(unittest.TestCase):
    """Test create_wp_post for recipe posts"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.callback = Mock()
        self.notion_post = {'id': 'test-post-id'}
        self.website = 'test_site'
        self.post_slug = 'test-recipe-slug'
        self.categories = 'Recipes / Desserts'
        
        self.recipe_post_parts = {
            POST_PART_TITLE: 'Delicious Chocolate Cake',
            POST_PART_INTRO: 'This is an amazing chocolate cake recipe.',
            POST_PART_EQUIPMENT_MUST: ['Mixing bowl', 'Oven'],
            POST_PART_EQUIPMENT_NICE: ['Stand mixer'],
            POST_PART_INGREDIENTS: ['2 cups flour', '1 cup sugar', '3 eggs'],
            POST_PART_INSTRUCTIONS: ['Mix ingredients', 'Bake at 350F'],
            POST_PART_GOOD_TO_KNOW: 'Store in an airtight container.',
            POST_PART_CONCLUSION: ''
        }
    
    @patch('wp_post_gen.get_post_type')
    @patch('wp_post_gen.PostTypes')
    @patch('wp_post_gen.get_post_topic_from_cats')
    @patch('wp_post_gen.WPFormatter')
    @patch('wp_post_gen.WordPressClient')
    def test_create_recipe_post_success(
        self,
        mock_wp_client_class,
        mock_formatter_class,
        mock_get_topic,
        mock_post_types_class,
        mock_get_type
    ):
        """Test successful creation of a recipe post"""
        # Setup mocks
        mock_get_type.return_value = 'single_recipe'
        mock_post_types = Mock()
        mock_post_types.is_singular.return_value = True
        mock_post_types_class.return_value = mock_post_types
        mock_get_topic.return_value = POST_TOPIC_RECIPES
        
        mock_formatter = Mock()
        mock_formatter.generate_recipe.return_value = '<h2>Recipe content</h2>'
        mock_formatter_class.return_value = mock_formatter
        
        mock_wp_client = Mock()
        mock_wp_client.create_post.return_value = {
            'id': 123,
            'link': 'https://test.com/delicious-chocolate-cake',
            'slug': 'delicious-chocolate-cake'
        }
        mock_wp_client_class.return_value = mock_wp_client
        
        # Execute
        result = create_wp_post(
            self.notion_post,
            self.website,
            self.recipe_post_parts,
            self.post_slug,
            self.categories,
            callback=self.callback,
            test=False
        )
        
        # Verify
        self.assertEqual(result['id'], 123)
        self.assertEqual(result['link'], 'https://test.com/delicious-chocolate-cake')
        
        # Verify formatter was called with correct parameters
        mock_formatter.generate_recipe.assert_called_once_with(
            {
                'title': 'Delicious Chocolate Cake',
                'intro': 'This is an amazing chocolate cake recipe.',
                'equipment_must_haves': ['Mixing bowl', 'Oven'],
                'equipment_nice_to_haves': ['Stand mixer'],
                'ingredients': ['2 cups flour', '1 cup sugar', '3 eggs'],
                'instructions': ['Mix ingredients', 'Bake at 350F'],
                'good_to_know': 'Store in an airtight container.',
                'conclusion': ''
            }
        )
        
        # Verify WordPress client was called
        mock_wp_client.create_post.assert_called_once()
        call_args = mock_wp_client.create_post.call_args[1]
        self.assertEqual(call_args['title'], 'Delicious Chocolate Cake')
        self.assertEqual(call_args['slug'], 'test-recipe-slug')
        self.assertEqual(call_args['category_name'], 'Recipes / Desserts')
    
    @patch('wp_post_gen.get_post_type')
    @patch('wp_post_gen.PostTypes')
    @patch('wp_post_gen.get_post_topic_from_cats')
    @patch('wp_post_gen.WPFormatter')
    def test_create_recipe_post_test_mode(
        self,
        mock_formatter_class,
        mock_get_topic,
        mock_post_types_class,
        mock_get_type
    ):
        """Test recipe post creation in test mode"""
        # Setup mocks
        mock_get_type.return_value = 'single_recipe'
        mock_post_types = Mock()
        mock_post_types.is_singular.return_value = True
        mock_post_types_class.return_value = mock_post_types
        mock_get_topic.return_value = POST_TOPIC_RECIPES
        
        mock_formatter = Mock()
        mock_formatter.generate_recipe.return_value = '<h2>Recipe content</h2>'
        mock_formatter_class.return_value = mock_formatter
        
        # Execute
        result = create_wp_post(
            self.notion_post,
            self.website,
            self.recipe_post_parts,
            self.post_slug,
            self.categories,
            callback=self.callback,
            test=True
        )
        
        # Verify test mode returns mock data
        self.assertEqual(result['link'], 'https://example.com/test-post')
        self.assertEqual(result['id'], 123)
        self.assertEqual(result['slug'], 'test-recipe-slug')
        
        # Verify test mode logging
        self.callback.assert_any_call('\n[TEST MODE][create_wp_post] Post Title:\nDelicious Chocolate Cake\n')
    
    @patch('wp_post_gen.get_post_type')
    @patch('wp_post_gen.PostTypes')
    @patch('wp_post_gen.get_post_topic_from_cats')
    @patch('wp_post_gen.WPFormatter')
    def test_create_recipe_post_missing_optional_parts(
        self,
        mock_formatter_class,
        mock_get_topic,
        mock_post_types_class,
        mock_get_type
    ):
        """Test recipe post creation with missing optional parts"""
        # Setup mocks
        mock_get_type.return_value = 'single_recipe'
        mock_post_types = Mock()
        mock_post_types.is_singular.return_value = True
        mock_post_types_class.return_value = mock_post_types
        mock_get_topic.return_value = POST_TOPIC_RECIPES
        
        mock_formatter = Mock()
        mock_formatter.generate_recipe.return_value = '<h2>Recipe content</h2>'
        mock_formatter_class.return_value = mock_formatter
        
        # Minimal post parts
        minimal_parts = {
            POST_PART_TITLE: 'Simple Recipe',
            POST_PART_INGREDIENTS: ['Flour'],
            POST_PART_INSTRUCTIONS: ['Mix']
        }
        
        # Execute
        result = create_wp_post(
            self.notion_post,
            self.website,
            minimal_parts,
            self.post_slug,
            self.categories,
            callback=self.callback,
            test=True
        )
        
        # Verify formatter was called with empty defaults for missing parts
        mock_formatter.generate_recipe.assert_called_once_with(
            {
                'title': 'Simple Recipe',
                'ingredients': ['Flour'],
                'instructions': ['Mix']
            }
        )


class TestCreateWpPostListicle(unittest.TestCase):
    """Test create_wp_post for listicle/roundup posts"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.callback = Mock()
        self.notion_post = {'id': 'test-post-id'}
        self.website = 'test_site'
        self.post_slug = 'best-recipes-roundup'
        self.categories = 'Roundups / Desserts'
        
        self.listicle_post_parts = {
            POST_PART_TITLE: 'Top 10 Dessert Recipes',
            POST_PART_INTRO: 'Here are the best dessert recipes.',
            POST_PART_ITEMS: [
                {'title': 'Chocolate Cake', 'body': 'A rich chocolate cake.'},
                {'title': 'Apple Pie', 'body': 'Classic apple pie.'}
            ],
            POST_PART_CONCLUSION: 'Try these amazing recipes!'
        }
    
    @patch('wp_post_gen.get_post_type')
    @patch('wp_post_gen.PostTypes')
    @patch('wp_post_gen.get_post_topic_from_cats')
    @patch('wp_post_gen.WPFormatter')
    @patch('wp_post_gen.WordPressClient')
    def test_create_listicle_post_success(
        self,
        mock_wp_client_class,
        mock_formatter_class,
        mock_get_topic,
        mock_post_types_class,
        mock_get_type
    ):
        """Test successful creation of a listicle post"""
        # Setup mocks
        mock_get_type.return_value = 'roundup'
        mock_post_types = Mock()
        mock_post_types.is_singular.return_value = False
        mock_post_types_class.return_value = mock_post_types
        mock_get_topic.return_value = 'roundups'
        
        mock_formatter = Mock()
        mock_formatter.generate_listicle.return_value = '<h2>Listicle content</h2>'
        mock_formatter_class.return_value = mock_formatter
        
        mock_wp_client = Mock()
        mock_wp_client.create_post.return_value = {
            'id': 456,
            'link': 'https://test.com/top-10-desserts',
            'slug': 'top-10-desserts'
        }
        mock_wp_client_class.return_value = mock_wp_client
        
        # Execute
        result = create_wp_post(
            self.notion_post,
            self.website,
            self.listicle_post_parts,
            self.post_slug,
            self.categories,
            callback=self.callback,
            test=False
        )
        
        # Verify
        self.assertEqual(result['id'], 456)
        self.assertEqual(result['link'], 'https://test.com/top-10-desserts')
        
        # Verify formatter was called with correct parameters
        mock_formatter.generate_listicle.assert_called_once_with(
            intro='Here are the best dessert recipes.',
            conclusion='Try these amazing recipes!',
            items=[
                {'title': 'Chocolate Cake', 'body': 'A rich chocolate cake.'},
                {'title': 'Apple Pie', 'body': 'Classic apple pie.'}
            ]
        )
        
        # Verify WordPress client was called
        mock_wp_client.create_post.assert_called_once()
    
    @patch('wp_post_gen.get_post_type')
    @patch('wp_post_gen.PostTypes')
    @patch('wp_post_gen.get_post_topic_from_cats')
    @patch('wp_post_gen.WPFormatter')
    def test_create_listicle_post_test_mode(
        self,
        mock_formatter_class,
        mock_get_topic,
        mock_post_types_class,
        mock_get_type
    ):
        """Test listicle post creation in test mode"""
        # Setup mocks
        mock_get_type.return_value = 'roundup'
        mock_post_types = Mock()
        mock_post_types.is_singular.return_value = False
        mock_post_types_class.return_value = mock_post_types
        mock_get_topic.return_value = 'roundups'
        
        mock_formatter = Mock()
        mock_formatter.generate_listicle.return_value = '<h2>Listicle content</h2>'
        mock_formatter_class.return_value = mock_formatter
        
        # Execute
        result = create_wp_post(
            self.notion_post,
            self.website,
            self.listicle_post_parts,
            self.post_slug,
            self.categories,
            callback=self.callback,
            test=True
        )
        
        # Verify test mode returns mock data
        self.assertEqual(result['link'], 'https://example.com/test-post')
        self.assertIn('[TEST MODE][create_wp_post]', str(self.callback.call_args_list))


class TestCreateWpPostErrors(unittest.TestCase):
    """Test error handling in create_wp_post"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.callback = Mock()
        self.notion_post = {'id': 'test-post-id'}
        self.website = 'test_site'
        self.post_slug = 'test-slug'
        self.categories = 'Category'
    
    @patch('wp_post_gen.get_post_type')
    @patch('wp_post_gen.PostTypes')
    @patch('wp_post_gen.get_post_topic_from_cats')
    def test_unsupported_post_type_combination(
        self,
        mock_get_topic,
        mock_post_types_class,
        mock_get_type
    ):
        """Test error for unsupported post type/topic combination"""
        # Setup mocks for unsupported combination
        mock_get_type.return_value = 'unknown_type'
        mock_post_types = Mock()
        mock_post_types.is_singular.return_value = True
        mock_post_types_class.return_value = mock_post_types
        mock_get_topic.return_value = 'unknown_topic'
        
        post_parts = {POST_PART_TITLE: 'Test'}
        
        # Execute and verify error
        with self.assertRaises(ValueError) as context:
            create_wp_post(
                self.notion_post,
                self.website,
                post_parts,
                self.post_slug,
                self.categories,
                callback=self.callback,
                test=False
            )
        
        self.assertIn('Unsupported post type/topic combination', str(context.exception))
    
    @patch('wp_post_gen.get_post_type')
    @patch('wp_post_gen.PostTypes')
    @patch('wp_post_gen.get_post_topic_from_cats')
    @patch('wp_post_gen.WPFormatter')
    @patch('wp_post_gen.WordPressClient')
    def test_wordpress_post_creation_fails(
        self,
        mock_wp_client_class,
        mock_formatter_class,
        mock_get_topic,
        mock_post_types_class,
        mock_get_type
    ):
        """Test error when WordPress post creation fails"""
        # Setup mocks
        mock_get_type.return_value = 'single_recipe'
        mock_post_types = Mock()
        mock_post_types.is_singular.return_value = True
        mock_post_types_class.return_value = mock_post_types
        mock_get_topic.return_value = POST_TOPIC_RECIPES
        
        mock_formatter = Mock()
        mock_formatter.generate_recipe.return_value = '<h2>Content</h2>'
        mock_formatter_class.return_value = mock_formatter
        
        mock_wp_client = Mock()
        mock_wp_client.create_post.return_value = None  # Simulate failure
        mock_wp_client_class.return_value = mock_wp_client
        
        post_parts = {
            POST_PART_TITLE: 'Test Recipe',
            POST_PART_INGREDIENTS: ['Flour'],
            POST_PART_INSTRUCTIONS: ['Mix']
        }
        
        # Execute and verify error
        with self.assertRaises(ValueError) as context:
            create_wp_post(
                self.notion_post,
                self.website,
                post_parts,
                self.post_slug,
                self.categories,
                callback=self.callback,
                test=False
            )
        
        self.assertIn('Failed to create post on WordPress', str(context.exception))


class TestCreateWpPostContentFormatting(unittest.TestCase):
    """Test content formatting logic"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.callback = Mock()
        self.notion_post = {'id': 'test-post-id'}
        self.website = 'test_site'
        self.post_slug = 'test-slug'
        self.categories = 'Recipes'
    
    @patch('wp_post_gen.get_post_type')
    @patch('wp_post_gen.PostTypes')
    @patch('wp_post_gen.get_post_topic_from_cats')
    @patch('wp_post_gen.WPFormatter')
    def test_content_length_logging(
        self,
        mock_formatter_class,
        mock_get_topic,
        mock_post_types_class,
        mock_get_type
    ):
        """Test that content length is logged"""
        # Setup mocks
        mock_get_type.return_value = 'single_recipe'
        mock_post_types = Mock()
        mock_post_types.is_singular.return_value = True
        mock_post_types_class.return_value = mock_post_types
        mock_get_topic.return_value = POST_TOPIC_RECIPES
        
        mock_formatter = Mock()
        test_content = 'x' * 1500  # 1500 characters
        mock_formatter.generate_recipe.return_value = test_content
        mock_formatter_class.return_value = mock_formatter
        
        post_parts = {
            POST_PART_TITLE: 'Test',
            POST_PART_INGREDIENTS: ['Flour'],
            POST_PART_INSTRUCTIONS: ['Mix']
        }
        
        # Execute
        result = create_wp_post(
            self.notion_post,
            self.website,
            post_parts,
            self.post_slug,
            self.categories,
            callback=self.callback,
            test=True
        )
        
        # Verify length logging
        self.callback.assert_any_call('[INFO][create_wp_post] Content formatted (1500 chars)')


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCreateWpPostRecipe))
    suite.addTests(loader.loadTestsFromTestCase(TestCreateWpPostListicle))
    suite.addTests(loader.loadTestsFromTestCase(TestCreateWpPostErrors))
    suite.addTests(loader.loadTestsFromTestCase(TestCreateWpPostContentFormatting))
    
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
