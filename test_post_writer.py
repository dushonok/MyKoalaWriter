"""
Unit tests for post_writer.py
"""

import unittest
import sys
import os
import json
from unittest.mock import Mock, MagicMock, patch, call

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ConfigKeeper')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'WordPress')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'NotionAutomator')))

from post_writer import PostWriter
from notion_config import (
    POST_POST_TYPE_SINGLE_VAL,
    BLOG_POST_IMAGES_TITLE_PROP,
    BLOG_POST_IMAGES_DESCRIPTION_PROP,
    BLOG_POST_IMAGES_NOTES_PROP,
)
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
from wp_formatter import WP_FORMAT_ITEM_TITLE_KEY, WP_FORMAT_ITEM_BODY_KEY, WP_FORMAT_ITEM_LINK_KEY


class TestPostWriterInit(unittest.TestCase):
    """Test PostWriter initialization"""
    
    def test_init_default(self):
        """Test default initialization"""
        writer = PostWriter()
        self.assertEqual(writer.test, False)
        self.assertEqual(writer.callback, print)
    
    def test_init_with_params(self):
        """Test initialization with parameters"""
        callback = Mock()
        writer = PostWriter(test=True, callback=callback)
        self.assertEqual(writer.test, True)
        self.assertEqual(writer.callback, callback)


class TestPostWriterWritePost(unittest.TestCase):
    """Test write_post method"""
    
    def setUp(self):
        self.callback = Mock()
        self.writer = PostWriter(test=False, callback=self.callback)
        self.writer.website = "test.com"
        self.writer.post_title = "Amazing Chocolate Cake"
        self.writer.post_topic = POST_TOPIC_RECIPES
        self.writer.post_type = "single_recipe"
        self.writer.notion_url = "https://notion.so/test"
    
    @patch('post_writer.PostTypes')
    def test_write_post_validation_empty_title(self, mock_post_types):
        """Test validation error for empty title"""
        self.writer.post_title = ""
        
        with self.assertRaises(ValueError) as context:
            self.writer.write_post()
        
        self.assertIn('must be set before calling write_post', str(context.exception))
    
    @patch('post_writer.PostTypes')
    def test_write_post_validation_empty_topic(self, mock_post_types):
        """Test validation error for empty topic"""
        self.writer.post_topic = ""
        
        with self.assertRaises(ValueError) as context:
            self.writer.write_post()
        
        self.assertIn('must be set before calling write_post', str(context.exception))
    
    @patch('post_writer.PostTypes')
    def test_write_post_validation_empty_type(self, mock_post_types):
        """Test validation error for empty type"""
        self.writer.post_type = ""
        
        with self.assertRaises(ValueError) as context:
            self.writer.write_post()
        
        self.assertIn('must be set before calling write_post', str(context.exception))
    
    @patch.object(PostWriter, '_if_using_our_recipe')
    @patch.object(PostWriter, '_get_single_recipe_post')
    @patch('post_writer.PostTypes')
    def test_write_post_calls_single_recipe(self, mock_post_types, mock_get_single, mock_if_using_our):
        """Test that write_post calls single recipe method for singular posts"""
        mock_post_types_instance = Mock()
        mock_post_types_instance.is_singular.return_value = True
        mock_post_types.return_value = mock_post_types_instance
        
        mock_if_using_our.return_value = False
        
        # Set required fields
        self.writer.website = "test.com"
        self.writer.post_title = "Test Title"
        self.writer.post_topic = POST_TOPIC_RECIPES
        self.writer.post_type = POST_POST_TYPE_SINGLE_VAL
        
        mock_get_single.return_value = {POST_PART_TITLE: "Test"}
        
        result = self.writer.write_post()
        
        mock_get_single.assert_called_once()
        self.assertEqual(result, {POST_PART_TITLE: "Test"})
    
    @patch.object(PostWriter, '_if_using_our_recipe')
    @patch.object(PostWriter, '_get_roundup_post')
    @patch('post_writer.PostTypes')
    def test_write_post_calls_roundup(self, mock_post_types, mock_get_roundup, mock_if_using_our):
        """Test that write_post calls roundup method for non-singular posts"""
        mock_post_types_instance = Mock()
        mock_post_types_instance.is_singular.return_value = False
        mock_post_types.return_value = mock_post_types_instance
        
        mock_if_using_our.return_value = False
        
        # Set required fields
        self.writer.website = "test.com"
        self.writer.post_title = "Roundup Test Title"
        self.writer.post_topic = POST_TOPIC_RECIPES
        self.writer.post_type = "roundup"
        
        mock_get_roundup.return_value = {POST_PART_TITLE: "Roundup Test"}
        
        result = self.writer.write_post()
        
        mock_get_roundup.assert_called_once()
        self.assertEqual(result, {POST_PART_TITLE: "Roundup Test"})


class TestPostWriterSingleRecipePost(unittest.TestCase):
    """Test _get_single_recipe_post method"""
    
    def setUp(self):
        self.callback = Mock()
        self.writer = PostWriter(test=True, callback=self.callback)
        self.writer.post_title = "Delicious Cake"
        self.writer.post_topic = POST_TOPIC_RECIPES
        self.writer.post_type = "single item"
    
    def test_get_single_recipe_post_test_mode(self):
        """Test single recipe generation in test mode"""
        result = self.writer._get_single_recipe_post()
        
        # Verify all required keys are present
        self.assertIn(POST_PART_TITLE, result)
        self.assertIn(POST_PART_INTRO, result)
        self.assertIn(POST_PART_EQUIPMENT_MUST, result)
        self.assertIn(POST_PART_EQUIPMENT_NICE, result)
        self.assertIn(POST_PART_INGREDIENTS, result)
        self.assertIn(POST_PART_INSTRUCTIONS, result)
        self.assertIn(POST_PART_GOOD_TO_KNOW, result)
        
        # Verify test mode returns mock data
        self.assertIsInstance(result[POST_PART_INGREDIENTS], list)
        self.assertIsInstance(result[POST_PART_INSTRUCTIONS], list)
        self.assertTrue(len(result[POST_PART_INGREDIENTS]) > 0)
        self.assertTrue(len(result[POST_PART_INSTRUCTIONS]) > 0)
    
    @patch('post_writer.send_prompt_to_openai')
    @patch.object(PostWriter, '_generate_title_with_ai')
    def test_get_single_recipe_post_ai_mode(self, mock_gen_title, mock_send_prompt):
        """Test single recipe generation with AI"""
        self.writer.test = False
        
        # Mock AI response
        mock_send_prompt.return_value = {
            'error': '',
            'message': '''{
                "intro": "This is a great recipe.",
                "equipment_must_haves": ["Bowl", "Oven"],
                "equipment_nice_to_haves": ["Mixer"],
                "ingredients": ["2 cups flour", "1 cup sugar"],
                "instructions": ["Mix ingredients", "Bake"],
                "good_to_know": "Store in airtight container."
            }'''
        }
        mock_gen_title.return_value = "Amazing Chocolate Cake"
        
        result = self.writer._get_single_recipe_post()
        
        # Verify AI was called
        mock_send_prompt.assert_called_once()
        mock_gen_title.assert_called_once()
        
        # Verify result structure
        self.assertEqual(result[POST_PART_TITLE], "Amazing Chocolate Cake")
        self.assertEqual(len(result[POST_PART_INGREDIENTS]), 2)
        self.assertEqual(len(result[POST_PART_INSTRUCTIONS]), 2)
    
    @patch('post_writer.send_prompt_to_openai')
    def test_get_single_recipe_post_ai_error(self, mock_send_prompt):
        """Test error handling when AI returns error"""
        self.writer.test = False
        
        mock_send_prompt.return_value = {
            'error': 'API_ERROR',
            'message': 'Rate limit exceeded'
        }
        
        with self.assertRaises(Exception):
            self.writer._get_single_recipe_post()
    
    @patch('post_writer.send_prompt_to_openai')
    @patch.object(PostWriter, '_generate_title_with_ai')
    def test_get_single_recipe_post_invalid_json(self, mock_gen_title, mock_send_prompt):
        """Test error handling for invalid JSON response"""
        self.writer.test = False
        
        mock_send_prompt.return_value = {
            'error': '',
            'message': 'This is not valid JSON'
        }
        
        with self.assertRaises(ValueError) as context:
            self.writer._get_single_recipe_post()
        
        self.assertIn('Failed to parse AI response as JSON', str(context.exception))


class TestPostWriterRoundupPost(unittest.TestCase):
    """Test _get_roundup_post method"""
    
    def setUp(self):
        self.callback = Mock()
        self.writer = PostWriter(test=False, callback=self.callback)
        self.writer.post_title = "Best Recipes Roundup"
        self.writer.post_topic = POST_TOPIC_RECIPES
        self.writer.post_type = "Roundup"
        self.writer.notion_url = "https://notion.so/roundup-test"
    
    @patch('post_writer.get_post_images_for_blog_url')
    @patch.object(PostWriter, '_generate_title_intro_conclusion_with_ai')
    def test_get_roundup_post_success(self, mock_gen_content, mock_get_images):
        """Test successful roundup post generation"""
        # Mock Notion items
        mock_get_images.return_value = [
            {
                'Image Title': 'Recipe 1',
                'Image Description': 'https://example.com/recipe1',
                'Notes': 'This is a great recipe for beginners.'
            },
            {
                'Image Title': 'Recipe 2',
                'Image Description': 'https://example.com/recipe2',
                'Notes': 'An advanced technique for pros.'
            }
        ]
        
        # Mock AI generation
        mock_gen_content.return_value = (
            "Top 10 Recipes",
            "Welcome to our roundup!",
            "Thanks for reading!"
        )
        
        result = self.writer._get_roundup_post()
        
        # Verify structure
        self.assertEqual(result[POST_PART_TITLE], "Top 10 Recipes")
        self.assertEqual(result[POST_PART_INTRO], "Welcome to our roundup!")
        self.assertEqual(result[POST_PART_CONCLUSION], "Thanks for reading!")
        self.assertEqual(len(result[POST_PART_ITEMS]), 2)
        
        # Verify items structure
        self.assertEqual(result[POST_PART_ITEMS][0][WP_FORMAT_ITEM_TITLE_KEY], 'Recipe 1')
        self.assertIn('https://example.com/recipe1', result[POST_PART_ITEMS][0][WP_FORMAT_ITEM_BODY_KEY])
        self.assertEqual(result[POST_PART_ITEMS][0][WP_FORMAT_ITEM_LINK_KEY], 'https://example.com/recipe1')
        self.assertEqual(result[POST_PART_ITEMS][1][WP_FORMAT_ITEM_LINK_KEY], 'https://example.com/recipe2')
    
    @patch('post_writer.get_post_images_for_blog_url')
    def test_get_roundup_post_no_items(self, mock_get_images):
        """Test error when no roundup items found"""
        mock_get_images.return_value = []
        
        with self.assertRaises(ValueError) as context:
            self.writer._get_roundup_post()
        
        self.assertIn('No roundup items found', str(context.exception))
    
    @patch('post_writer.get_post_images_for_blog_url')
    @patch.object(PostWriter, '_generate_title_intro_conclusion_with_ai')
    @patch.object(PostWriter, '_append_cta')
    def test_get_roundup_post_cta_appended(self, mock_append_cta, mock_gen_content, mock_get_images):
        """Test that CTA is appended to items with URLs"""
        mock_get_images.return_value = [
            {
                'Image Title': 'Recipe 1',
                'Image Description': 'https://example.com/recipe1',
                'Notes': 'Great recipe.'
            }
        ]
        
        mock_gen_content.return_value = ("Title", "Intro", "Conclusion")
        mock_append_cta.return_value = "Great recipe.\nCheck it out here"
        
        result = self.writer._get_roundup_post()
        
        # Verify CTA was appended
        mock_append_cta.assert_called_once()


class TestPostWriterTitleGeneration(unittest.TestCase):
    """Test title generation methods"""
    
    def setUp(self):
        self.callback = Mock()
        self.writer = PostWriter(test=False, callback=self.callback)
        self.writer.post_title = "Chocolate Cake"
        self.writer.post_topic = POST_TOPIC_RECIPES
        self.writer.post_type = "single item"
    
    @patch('post_writer.send_prompt_to_openai')
    def test_generate_title_with_ai_success(self, mock_send_prompt):
        """Test successful title generation"""
        from chatgpt_api import AIPromptConfig
        
        mock_send_prompt.return_value = {
            'error': '',
            'message': 'The Ultimate Chocolate Cake Recipe'
        }
        
        prompt_config = AIPromptConfig(
            system_prompt="",
            user_prompt="",
            response_format="",
            ai_model="gpt-4",
            verbosity=3
        )
        
        result = self.writer._generate_title_with_ai(prompt_config, "Test intro", ["ingredient1", "ingredient2"], ["step1", "step2"])
        
        self.assertEqual(result, 'The Ultimate Chocolate Cake Recipe')
        mock_send_prompt.assert_called_once()
    
    def test_generate_title_with_ai_test_mode(self):
        """Test title generation in test mode"""
        from chatgpt_api import AIPromptConfig
        
        self.writer.test = True
        prompt_config = AIPromptConfig(
            system_prompt="",
            user_prompt="",
            response_format="",
            ai_model="gpt-4",
            verbosity=3
        )
        
        intro = "Test intro"
        ingredients = ["ingredient1", "ingredient2"]
        instructions = ["step1", "step2"]
        result = self.writer._generate_title_with_ai(prompt_config, intro, ingredients, instructions)
        
        # The code returns early with temp_body included in test mode
        self.assertIn("[TEST]", result)
        self.assertIn(self.writer.post_title, result)
        self.assertIn("Intro:", result)
        self.assertIn("Ingredients:", result)
        self.assertIn("Instructions:", result)
    
    @patch('post_writer.send_prompt_to_openai')
    def test_generate_title_with_ai_error(self, mock_send_prompt):
        """Test error handling in title generation"""
        from chatgpt_api import AIPromptConfig
        
        mock_send_prompt.return_value = {
            'error': 'API_ERROR',
            'message': 'Something went wrong'
        }
        
        prompt_config = AIPromptConfig(
            system_prompt="",
            user_prompt="",
            response_format="",
            ai_model="gpt-4",
            verbosity=3
        )
        
        with self.assertRaises(Exception):
            self.writer._generate_title_with_ai(prompt_config, "Test intro", [], [])


class TestPostWriterTitleIntroConclusion(unittest.TestCase):
    """Test _generate_title_intro_conclusion_with_ai method"""
    
    def setUp(self):
        self.callback = Mock()
        self.writer = PostWriter(test=False, callback=self.callback)
        self.writer.post_title = "Best Recipes"
        self.writer.post_topic = POST_TOPIC_RECIPES
        self.writer.post_type = "Roundup"
    
    @patch('post_writer.send_prompt_to_openai')
    def test_generate_title_intro_conclusion_success(self, mock_send_prompt):
        """Test successful generation of title, intro, and conclusion"""
        mock_send_prompt.return_value = {
            'error': '',
            'message': '''{
                "title": "10 Best Recipes You Must Try",
                "intro": "Welcome to our collection of amazing recipes.",
                "conclusion": "Thanks for reading our roundup!"
            }'''
        }
        
        title, intro, conclusion = self.writer._generate_title_intro_conclusion_with_ai("Body text")
        
        self.assertEqual(title, "10 Best Recipes You Must Try")
        self.assertIn("Welcome", intro)
        self.assertIn("Thanks", conclusion)
    
    def test_generate_title_intro_conclusion_test_mode(self):
        """Test generation in test mode"""
        self.writer.test = True
        
        title, intro, conclusion = self.writer._generate_title_intro_conclusion_with_ai("Body text")
        
        self.assertIn("[TEST]", title)
        self.assertIn("[TEST]", intro)
        self.assertIn("[TEST]", conclusion)
        self.assertIn(self.writer.post_title, title)
    
    @patch('post_writer.send_prompt_to_openai')
    def test_generate_title_intro_conclusion_invalid_json(self, mock_send_prompt):
        """Test error handling for invalid JSON"""
        mock_send_prompt.return_value = {
            'error': '',
            'message': 'Invalid JSON content'
        }
        
        with self.assertRaises(ValueError) as context:
            self.writer._generate_title_intro_conclusion_with_ai("Body text")
        
        self.assertIn('Failed to parse AI response as JSON', str(context.exception))


class TestPostWriterHelperMethods(unittest.TestCase):
    """Test helper methods"""
    
    def setUp(self):
        self.callback = Mock()
        self.writer = PostWriter(callback=self.callback)
        self.writer.post_topic = POST_TOPIC_RECIPES
        self.writer.post_type = "single item"
    
    def test_split_into_paragraphs(self):
        """Test paragraph splitting"""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        result = self.writer._split_into_paragraphs(text, sentences_per_paragraph=2)
        
        # Should have 2 paragraphs with 2 sentences each
        paragraphs = result.split('\n')
        self.assertEqual(len(paragraphs), 2)
    
    def test_split_into_paragraphs_empty(self):
        """Test splitting empty text"""
        result = self.writer._split_into_paragraphs("")
        self.assertEqual(result, "")
    
    def test_split_into_paragraphs_single_sentence(self):
        """Test splitting single sentence"""
        text = "Single sentence."
        result = self.writer._split_into_paragraphs(text)
        self.assertEqual(result, "Single sentence.")
    
    @patch('post_writer.PostTypes')
    def test_get_is_post_type_singular(self, mock_post_types):
        """Test singular post type check"""
        mock_post_types_instance = Mock()
        mock_post_types_instance.is_singular.return_value = True
        mock_post_types.return_value = mock_post_types_instance
        
        result = self.writer._get_is_post_type_singular()
        
        self.assertTrue(result)
        mock_post_types_instance.is_singular.assert_called_once_with(self.writer.post_type)
    
    def test_get_cta_with_link(self):
        """Test CTA generation with link"""
        url = "https://example.com/recipe"
        result = self.writer._get_cta_with_link(url)
        
        self.assertIn('href="https://example.com/recipe"', result)
        self.assertIn('target="_blank"', result)
        self.assertIn('rel="noopener"', result)
    
    def test_append_cta(self):
        """Test appending CTA to body text"""
        body = "This is a great recipe."
        url = "https://example.com/recipe"
        
        result = self.writer._append_cta(body, url)
        
        self.assertIn(body, result)
        self.assertIn(url, result)
        self.assertIn('\n', result)  # CTA should be on new line
    
    def test_append_cta_empty_body(self):
        """Test appending CTA with empty body"""
        result = self.writer._append_cta("", "https://example.com")
        self.assertEqual(result, "")
    
    def test_append_cta_empty_url(self):
        """Test appending CTA with empty URL"""
        result = self.writer._append_cta("Body text", "")
        self.assertEqual(result, "Body text")
    
    def test_is_escaped(self):
        """Test HTML escape detection"""
        escaped = "&lt;div&gt;"
        unescaped = "<div>"
        
        self.assertTrue(self.writer._is_escaped(escaped))
        self.assertFalse(self.writer._is_escaped(unescaped))


class TestPostWriterPrompts(unittest.TestCase):
    """Test prompt generation methods"""
    
    def setUp(self):
        self.callback = Mock()
        self.writer = PostWriter(callback=self.callback)
        self.writer.post_title = "Test Recipe"
        self.writer.post_topic = POST_TOPIC_RECIPES
        self.writer.post_type = "single item"
    
    def test_get_sys_prompt_base(self):
        """Test system prompt generation"""
        result = self.writer._get_sys_prompt_base()
        
        self.assertIn(self.writer.post_topic, result)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)
    
    def test_get_post_prompt_valid(self):
        """Test getting valid post prompt"""
        result = self.writer._get_post_prompt("title")
        
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)
    
    def test_get_post_prompt_invalid(self):
        """Test getting invalid prompt type"""
        with self.assertRaises(ValueError) as context:
            self.writer._get_post_prompt("nonexistent_type")
        
        self.assertIn("No 'nonexistent_type' prompt found", str(context.exception))
    
    @patch('post_writer.PostTypes')
    def test_get_single_plural_subj_singular(self, mock_post_types):
        """Test subject for singular posts"""
        mock_post_types_instance = Mock()
        mock_post_types_instance.is_singular.return_value = True
        mock_post_types.return_value = mock_post_types_instance
        
        result = self.writer._get_single_plural_subj()
        
        self.assertIn("single item", result)
    
    @patch('post_writer.PostTypes')
    def test_get_single_plural_subj_plural(self, mock_post_types):
        """Test subject for plural posts"""
        mock_post_types_instance = Mock()
        mock_post_types_instance.is_singular.return_value = False
        mock_post_types.return_value = mock_post_types_instance
        
        result = self.writer._get_single_plural_subj()
        
        self.assertNotIn("single item", result)


class TestPostWriterGeneratePostUsingOur(unittest.TestCase):
    """Tests for _get_single_recipe_post_using_ours method - skipped due to early return in implementation."""
    
    def setUp(self):
        self.callback = Mock()
        self.writer = PostWriter(test=False, callback=self.callback)
        # Set required fields to avoid KeyError
        self.writer.post_topic = POST_TOPIC_RECIPES
        self.writer.post_title = "Test Recipe"
        self.writer.post_type = "single item"
        self.writer.website = "test.com"
    
    @patch.object(PostWriter, '_generate_title_with_ai')
    @patch.object(PostWriter, '_update_add_missing_post_parts')
    @patch('post_writer.NotionRecipeParser')
    def test_extract_content_from_grouped_post_parts(self, mock_parser_class, mock_update_parts, mock_gen_title):
        """Test that content is correctly extracted from nested grouped_post_parts structure"""
        # Setup parser mock with nested structure
        mock_parser = Mock()
        mock_parser.parse_recipe_from_url.return_value = {
            'post': {'id': 'page123'},
            'title': 'Test Recipe',
            'website': 'mywebsite.com',
            'grouped_post_parts': {
                'Equipment': {
                    'content': 'Bowl, spoon, oven',
                    'Equipment: Must-haves': {
                        'content': 'Large bowl\nMixing spoon'
                    },
                    'Equipment: Nice-to-haves': {
                        'content': 'Stand mixer'
                    }
                },
                'Ingredients': {
                    'content': '2 cups flour\n1 cup sugar\n3 eggs'
                },
                'Instructions': {
                    'content': 'Step 1: Mix dry ingredients\nStep 2: Add wet ingredients'
                },
                'What Else You Should Know': {
                    'content': 'This recipe is great for beginners'
                },
                'Low FODMAP Serving Size': {
                    'content': '1 serving = 2 cookies'
                }
            }
        }
        mock_parser_class.return_value = mock_parser
        
        # Mock the dependencies
        from post_part_constants import PostParts
        mock_update_parts.return_value = {
            PostParts.INTRO.field_name: "Test intro",
            PostParts.EQUIPMENT.field_name: "Equipment",
            PostParts.LOW_FODMAP.field_name: "LF",
            PostParts.GOOD_TO_KNOW.field_name: "GTK",
            PostParts.CONCLUSION.field_name: "Conclusion"
        }
        mock_gen_title.return_value = "Generated Title"
        
        # Execute
        result = self.writer._get_single_recipe_post_using_ours('https://notion.so/test-page')
        
        # Verify parser was called
        mock_parser.parse_recipe_from_url.assert_called_once_with('https://notion.so/test-page')
        
        # Verify callback messages about extraction
        callback_messages = [call[0][0] for call in self.callback.call_args_list]
        extraction_messages = [msg for msg in callback_messages if 'Extracted' in msg and 'post parts' in msg]
        self.assertTrue(len(extraction_messages) > 0, "Should log extraction summary")
    
    @patch.object(PostWriter, '_generate_title_with_ai')
    @patch.object(PostWriter, '_update_add_missing_post_parts')
    @patch('post_writer.NotionRecipeParser')
    def test_uses_postparts_to_match_headings(self, mock_parser_class, mock_update_parts, mock_gen_title):
        """Test that PostParts.get_field_name_by_heading is used to match heading text"""
        # Setup parser mock with ingredients
        mock_parser = Mock()
        mock_parser.parse_recipe_from_url.return_value = {
            'post': {'id': 'page123'},
            'title': 'Test Recipe',
            'website': 'mywebsite.com',
            'grouped_post_parts': {
                'Ingredients': {'content': '2 cups flour\n1 cup sugar'}
            }
        }
        mock_parser_class.return_value = mock_parser
        
        # Mock the dependencies - _update_add_missing_post_parts requires ingredients
        # So it should be called successfully
        from post_part_constants import PostParts
        mock_update_parts.return_value = {
            PostParts.INTRO.field_name: "Test intro",
            PostParts.EQUIPMENT.field_name: "Equipment",
            PostParts.LOW_FODMAP.field_name: "LF",
            PostParts.GOOD_TO_KNOW.field_name: "GTK",
            PostParts.CONCLUSION.field_name: "Conclusion"
        }
        mock_gen_title.return_value = "Generated Title"
        
        # Execute - should succeed now with mocks
        result = self.writer._get_single_recipe_post_using_ours('https://notion.so/test-page')
        
        # Verify the result has a title
        self.assertIn(PostParts.TITLE.field_name, result)
        self.assertEqual(result[PostParts.TITLE.field_name], "Generated Title")
    
    @patch.object(PostWriter, '_generate_title_with_ai')
    @patch.object(PostWriter, '_update_add_missing_post_parts')
    @patch('post_writer.NotionRecipeParser')
    def test_handles_empty_grouped_post_parts(self, mock_parser_class, mock_update_parts, mock_gen_title):
        """Test handling of empty grouped_post_parts"""
        # Setup parser mock with empty structure
        mock_parser = Mock()
        mock_parser.parse_recipe_from_url.return_value = {
            'post': {'id': 'page123'},
            'title': 'Test Recipe',
            'website': 'mywebsite.com',
            'grouped_post_parts': {}
        }
        mock_parser_class.return_value = mock_parser
        
        # Mock _update_add_missing_post_parts to raise ValueError when called with empty dict
        mock_update_parts.side_effect = ValueError("No extracted Notion recipe parts provided")
        
        # Execute - should raise error due to no extracted parts
        with self.assertRaises(ValueError) as context:
            self.writer._get_single_recipe_post_using_ours('https://notion.so/test-page')
        
        # Verify error message
        self.assertIn("No extracted Notion recipe parts provided", str(context.exception))
    
    @unittest.skip("Method has early return for testing/development")
    @patch('post_writer.WordPressClient')
    @patch('post_writer.get_page_property')
    @patch.object(PostWriter, '_get_generate_post_parts')
    @patch('post_writer.NotionRecipeParser')
    def test_successful_post_generation(
        self,
        mock_parser_class,
        mock_generate_parts,
        mock_get_property,
        mock_wp_client
    ):
        """Test successful post generation from Notion URL"""
        # Setup parser mock
        mock_parser = Mock()
        mock_parser.parse_recipe_from_url.return_value = {
            'post': {'id': 'page123'},
            'title': 'Test Recipe',
            'website': 'mywebsite.com',
            'post_parts': [
                {'type': 'paragraph', 'text': 'Paragraph 1'},
                {'type': 'bulleted_list_item', 'text': 'Item 1'}
            ]
        }
        mock_parser_class.return_value = mock_parser
        
        mock_generate_parts.return_value = "<p>Generated content</p>"
        mock_get_property.side_effect = ['Category1', 'test-slug']
        
        # Mock WordPress client
        mock_wp = MagicMock()
        mock_wp.create_post.return_value = {'id': 'wp123'}
        mock_wp_client.return_value = mock_wp
        
        # Execute
        self.writer._get_single_recipe_post_using_ours('https://notion.so/test-page')
        
        # Verify
        mock_parser.parse_recipe_from_url.assert_called_once_with('https://notion.so/test-page')
        mock_wp.create_post.assert_called_once()
        call_args = mock_wp.create_post.call_args
        self.assertEqual(call_args[1]['title'], 'Test Recipe')
        self.assertEqual(call_args[1]['category_name'], 'Category1')
        self.assertEqual(call_args[1]['slug'], 'test-slug')
    
    @unittest.skip("Method has early return for testing/development")
    @patch('post_writer.WordPressClient')
    @patch('post_writer.get_page_property')
    @patch.object(PostWriter, '_get_generate_post_parts')
    @patch('post_writer.NotionRecipeParser')
    def test_failed_wp_post_creation(
        self,
        mock_parser_class,
        mock_generate_parts,
        mock_get_property,
        mock_wp_client
    ):
        """Test error handling when WordPress post creation fails"""
        # Setup parser mock
        mock_parser = Mock()
        mock_parser.parse_recipe_from_url.return_value = {
            'post': {'id': 'page123'},
            'title': 'Test Recipe',
            'website': 'mywebsite.com',
            'post_parts': [{'type': 'paragraph', 'text': 'Text'}]
        }
        mock_parser_class.return_value = mock_parser
        
        mock_generate_parts.return_value = "<p>Content</p>"
        mock_get_property.side_effect = ['Category', 'slug']
        
        # Mock WordPress client to return None (failure)
        mock_wp = MagicMock()
        mock_wp.create_post.return_value = None
        mock_wp_client.return_value = mock_wp
        
        # Execute and verify exception
        with self.assertRaises(ValueError) as context:
            self.writer._get_single_recipe_post_using_ours('https://notion.so/test-page')
        
        self.assertIn("Failed to create post", str(context.exception))


class TestPostWriterUpdateAddMissingPostParts(unittest.TestCase):
    """Test _update_add_missing_post_parts method"""
    
    def setUp(self):
        self.callback = Mock()
        self.writer = PostWriter(test=False, callback=self.callback)
    
    def test_missing_extracted_parts(self):
        """Test error when extracted_parts is empty"""
        with self.assertRaises(ValueError) as context:
            self.writer._update_add_missing_post_parts({})
        
        self.assertIn("No extracted Notion recipe parts provided", str(context.exception))
    
    def test_missing_ingredients(self):
        """Test error when ingredients are missing"""
        from post_part_constants import PostParts
        extracted_parts = {
            PostParts.INTRO.field_name: "Some intro",
            PostParts.INSTRUCTIONS.field_name: "Some instructions"
        }
        
        with self.assertRaises(ValueError) as context:
            self.writer._update_add_missing_post_parts(extracted_parts)
        
        self.assertIn("Ingredients part is missing", str(context.exception))
    
    def test_test_mode(self):
        """Test that test mode returns mock sections"""
        from post_part_constants import PostParts
        self.writer.test = True
        extracted_parts = {
            PostParts.INTRO.field_name: "Test intro",
            PostParts.INGREDIENTS.field_name: "2 cups flour\n1 cup sugar",
            PostParts.INSTRUCTIONS.field_name: "Mix ingredients\nBake at 350F"
        }
        
        result = self.writer._update_add_missing_post_parts(extracted_parts)
        
        # Should return dict with 5 sections
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 5)
        self.assertIn(PostParts.INTRO.field_name, result)
        self.assertIn(PostParts.EQUIPMENT.field_name, result)
        self.assertIn(PostParts.LOW_FODMAP.field_name, result)
        self.assertIn(PostParts.GOOD_TO_KNOW.field_name, result)
        self.assertIn(PostParts.CONCLUSION.field_name, result)
    
    @patch('post_writer.send_prompt_to_openai')
    def test_production_mode_success(self, mock_openai):
        """Test successful AI generation in production mode"""
        from post_part_constants import PostParts
        mock_response = {
            PostParts.INTRO.field_name: "Enhanced intro",
            PostParts.EQUIPMENT.field_name: "Must-haves: Bowl\nNice-haves: Mixer",
            PostParts.LOW_FODMAP.field_name: "LF info",
            PostParts.GOOD_TO_KNOW.field_name: "Important facts",
            PostParts.CONCLUSION.field_name: "Final words"
        }
        mock_openai.return_value = {
            'error': '',
            'message': json.dumps(mock_response)
        }
        
        extracted_parts = {
            PostParts.INTRO.field_name: "Original intro",
            PostParts.INGREDIENTS.field_name: "2 cups flour",
            PostParts.INSTRUCTIONS.field_name: "Mix and bake"
        }
        
        result = self.writer._update_add_missing_post_parts(extracted_parts)
        
        mock_openai.assert_called_once()
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 5)
    
    @patch('post_writer.send_prompt_to_openai')
    def test_openai_error(self, mock_openai):
        """Test error handling when OpenAI API fails"""
        from post_part_constants import PostParts
        mock_openai.return_value = {
            'error': 'API Error',
            'message': 'Failed to connect'
        }
        
        extracted_parts = {
            PostParts.INGREDIENTS.field_name: "2 cups flour",
            PostParts.INSTRUCTIONS.field_name: "Mix and bake"
        }
        
        from chatgpt_api import OpenAIAPIError
        with self.assertRaises(OpenAIAPIError):
            self.writer._update_add_missing_post_parts(extracted_parts)
    
    def test_all_parts_present(self):
        """Test when all parts are already present and need review"""
        from post_part_constants import PostParts
        self.writer.test = True
        extracted_parts = {
            PostParts.INTRO.field_name: "Existing intro",
            PostParts.EQUIPMENT.field_name: "Existing equipment",
            PostParts.INGREDIENTS.field_name: "2 cups flour",
            PostParts.INSTRUCTIONS.field_name: "Mix and bake",
            PostParts.GOOD_TO_KNOW.field_name: "Existing tips",
            PostParts.LOW_FODMAP.field_name: "Existing LF info",
            PostParts.CONCLUSION.field_name: "Existing conclusion"
        }
        
        result = self.writer._update_add_missing_post_parts(extracted_parts)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 5)
    
    def test_partial_parts_present(self):
        """Test when only some parts are present"""
        from post_part_constants import PostParts
        self.writer.test = True
        extracted_parts = {
            PostParts.INTRO.field_name: "Existing intro",
            PostParts.INGREDIENTS.field_name: "2 cups flour",
            PostParts.INSTRUCTIONS.field_name: "Mix and bake"
            # Missing: equipment, good_to_know, low_fodmap_portion, conclusion
        }
        
        result = self.writer._update_add_missing_post_parts(extracted_parts)
        
        self.assertIsInstance(result, dict)
        # Should generate missing parts
        self.assertEqual(len(result), 5)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestPostWriterInit))
    suite.addTests(loader.loadTestsFromTestCase(TestPostWriterWritePost))
    suite.addTests(loader.loadTestsFromTestCase(TestPostWriterSingleRecipePost))
    suite.addTests(loader.loadTestsFromTestCase(TestPostWriterRoundupPost))
    suite.addTests(loader.loadTestsFromTestCase(TestPostWriterTitleGeneration))
    suite.addTests(loader.loadTestsFromTestCase(TestPostWriterTitleIntroConclusion))
    suite.addTests(loader.loadTestsFromTestCase(TestPostWriterHelperMethods))
    suite.addTests(loader.loadTestsFromTestCase(TestPostWriterPrompts))
    suite.addTests(loader.loadTestsFromTestCase(TestPostWriterGeneratePostUsingOur))
    suite.addTests(loader.loadTestsFromTestCase(TestPostWriterUpdateAddMissingPostParts))
    
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
