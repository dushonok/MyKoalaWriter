"""Unit tests for update_wp_content.add_images_to_wp_post."""

import os
import sys
import unittest
from unittest.mock import Mock, call, patch

# Ensure project modules are discoverable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ConfigKeeper')))

from ai_gen_config import POST_TOPIC_RECIPES
from update_wp_content import add_images_to_wp_post


class TestAddImagesToWpPost(unittest.TestCase):
    """Exercises the add_images_to_wp_post helper."""

    @patch('update_wp_content.load_generic_input_folder')
    @patch('update_wp_content.get_post_folder')
    @patch('update_wp_content.get_ims_in_folder')
    @patch('update_wp_content.get_post_slug')
    @patch('update_wp_content.get_post_type')
    @patch('update_wp_content.get_post_topic_by_cat')
    @patch('update_wp_content.update_post_status')
    @patch('update_wp_content.PostStatuses')
    @patch('update_wp_content.WordPressClient')
    @patch('update_wp_content.WPFormatter')
    @patch('update_wp_content.PostTypes')
    def test_accepts_post_title_keyword_and_uploads(
        self,
        mock_post_types_cls,
        mock_wp_formatter_cls,
        mock_wp_client_cls,
        mock_post_statuses_cls,
        mock_update_post_status,
        mock_get_post_topic,
        mock_get_post_type,
        mock_get_post_slug,
        mock_get_images,
        mock_get_post_folder,
        mock_load_input_folder,
    ):
        mock_load_input_folder.return_value = 'C:/input'
        post_folder = os.path.join('C:/input', 'post')
        mock_get_post_folder.return_value = post_folder
        mock_get_images.return_value = ['002_image.jpg', '001_cover.jpg']
        mock_get_post_slug.return_value = 'tasty-cake'
        mock_get_post_type.return_value = 'single item'
        mock_get_post_topic.return_value = POST_TOPIC_RECIPES

        mock_post_types = Mock()
        mock_post_types.is_singular.return_value = True
        mock_post_types.is_roundup.return_value = False
        mock_post_types_cls.return_value = mock_post_types

        mock_formatter = Mock()
        mock_formatter.add_imgs_to_single_recipe = Mock(return_value='updated')
        mock_wp_formatter_cls.return_value = mock_formatter

        mock_wp = Mock()
        mock_wp.media_for_post = []
        mock_wp.get_post_id_by_slug.return_value = 321
        mock_wp.client = Mock()
        mock_wp.client.posts.get.return_value = {'link': 'https://example.com/tasty-cake/'}

        def upload_side_effect(path, title):
            return {
                'id': len(mock_wp.media_for_post) + 1,
                'source_url': f'https://cdn/{os.path.basename(path)}',
            }

        mock_wp.upload_media.side_effect = upload_side_effect
        mock_wp_client_cls.return_value = mock_wp

        mock_statuses = Mock()
        mock_statuses.published_imgs_added_id = 'status-id'
        mock_statuses.get_status_name.return_value = 'Published + images added'
        mock_post_statuses_cls.return_value = mock_statuses
        mock_update_post_status.return_value = {'id': 'fake'}

        result = add_images_to_wp_post(
            website='FoodSite',
            notion_post={'id': 'fake'},
            post_title='Delicious Cake',
            callback=lambda *_args, **_kwargs: None,
            test=False,
        )

        self.assertEqual(result, 'https://example.com/tasty-cake/')

        mock_load_input_folder.assert_called_once()
        mock_get_post_folder.assert_called_once_with('C:/input', {'id': 'fake'}, for_pins=True)
        self.assertEqual(mock_get_images.call_count, 1)
        mock_get_post_slug.assert_called_once_with({'id': 'fake'})
        mock_wp_client_cls.assert_called_once_with('FoodSite', unittest.mock.ANY)
        expected_calls = [
            call(os.path.join(post_folder, '001_cover.jpg'), title='001_cover.jpg'),
            call(os.path.join(post_folder, '002_image.jpg'), title='002_image.jpg'),
        ]
        mock_wp.upload_media.assert_has_calls(expected_calls)
        self.assertEqual(len(mock_wp.media_for_post), 2)
        mock_wp.set_featured_image_from_media.assert_called_once()
        featured_call_args = mock_wp.set_featured_image_from_media.call_args[0]
        self.assertEqual(featured_call_args, (321, mock_wp.media_for_post[-1]))
        mock_wp.update_post_content.assert_called_once_with(321, mock_formatter.add_imgs_to_single_recipe, unittest.mock.ANY)
        mock_wp.client.posts.get.assert_called_once_with(id=321)
        mock_post_statuses_cls.assert_called_once()
        mock_update_post_status.assert_called_once_with({'id': 'fake'}, 'status-id', test=False)

    @patch('update_wp_content.load_generic_input_folder')
    @patch('update_wp_content.get_post_folder')
    @patch('update_wp_content.get_ims_in_folder')
    @patch('update_wp_content.get_post_slug')
    def test_test_mode_skips_wordpress_calls(
        self,
        mock_get_post_slug,
        mock_get_images,
        mock_get_post_folder,
        mock_load_input_folder,
    ):
        mock_load_input_folder.return_value = 'C:/input'
        mock_get_post_folder.return_value = 'C:/input/post'
        mock_get_images.return_value = ['001_cover.jpg']
        mock_get_post_slug.return_value = 'test-slug'

        with patch('update_wp_content.WordPressClient') as mock_wp_client, \
             patch('update_wp_content.PostTypes') as mock_post_types_cls, \
             patch('update_wp_content.WPFormatter') as mock_formatter_cls, \
             patch('update_wp_content.PostStatuses') as mock_post_statuses_cls, \
             patch('update_wp_content.update_post_status') as mock_update_post_status, \
             patch('update_wp_content.get_post_topic_by_cat') as mock_get_post_topic, \
             patch('update_wp_content.get_post_type') as mock_get_post_type:
            mock_get_post_type.return_value = 'single item'
            mock_get_post_topic.return_value = POST_TOPIC_RECIPES
            mock_post_types = Mock()
            mock_post_types.is_singular.return_value = True
            mock_post_types.is_roundup.return_value = False
            mock_post_types_cls.return_value = mock_post_types
            result = add_images_to_wp_post(
                website='FoodSite',
                notion_post={'id': 'fake'},
                post_title='Test Post',
                callback=lambda *_args, **_kwargs: None,
                test=True,
            )

        self.assertEqual(result, 'https://example.com/test-post/test-slug')
        mock_wp_client.assert_not_called()
        mock_formatter_cls.assert_not_called()
        mock_post_statuses_cls.assert_not_called()
        mock_update_post_status.assert_not_called()
        mock_get_post_topic.assert_called_once_with({'id': 'fake'}, unittest.mock.ANY)
        mock_get_post_type.assert_called_once_with({'id': 'fake'})
        mock_post_types_cls.assert_called_once()

    @patch('update_wp_content.load_generic_input_folder')
    @patch('update_wp_content.get_post_folder')
    @patch('update_wp_content.get_ims_in_folder')
    @patch('update_wp_content.get_post_slug')
    def test_returns_none_when_no_images_found(
        self,
        mock_get_post_slug,
        mock_get_images,
        mock_get_post_folder,
        mock_load_input_folder,
    ):
        mock_load_input_folder.return_value = 'C:/input'
        mock_get_post_folder.return_value = 'C:/input/post'
        mock_get_images.return_value = []
        mock_get_post_slug.return_value = 'empty-slug'

        with patch('update_wp_content.WordPressClient') as mock_wp_client, \
             patch('update_wp_content.update_post_status') as mock_update_post_status, \
             patch('update_wp_content.PostStatuses') as mock_post_statuses_cls, \
             patch('update_wp_content.get_post_type') as mock_get_post_type, \
             patch('update_wp_content.get_post_topic_by_cat') as mock_get_post_topic:
            mock_get_post_type.return_value = 'single item'
            mock_get_post_topic.return_value = POST_TOPIC_RECIPES
            result = add_images_to_wp_post(
                website='FoodSite',
                notion_post={'id': 'fake'},
                post_title='No Images Post',
                callback=lambda *_args, **_kwargs: None,
                test=False,
            )

        self.assertIsNone(result)
        mock_wp_client.assert_not_called()
        mock_post_statuses_cls.assert_not_called()
        mock_update_post_status.assert_not_called()


def run_tests():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestAddImagesToWpPost)
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


if __name__ == '__main__':
    test_result = run_tests()
    print("\n" + "=" * 70)
    print(f"Tests run: {test_result.testsRun}")
    print(f"Failures: {len(test_result.failures)}")
    print(f"Errors: {len(test_result.errors)}")
    print(f"Skipped: {len(test_result.skipped)}")
    print("=" * 70)
    sys.exit(0 if test_result.wasSuccessful() else 1)
