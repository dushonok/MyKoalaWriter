import os
import re
import sys
from typing import List, Optional

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ConfigKeeper')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'WordPress')))

from ai_gen_config import POST_TOPIC_RECIPES
from config_utils import (
    get_ims_in_folder,
    get_post_folder,
    get_post_topic_by_cat,
    load_generic_input_folder,
)
from notion_api import get_post_slug, get_post_type
from notion_config import PostTypes
from wp_client import WordPressClient
from wp_formatter import WPFormatter


def _extract_leading_index(name: str) -> int:
    match = re.match(r"^(\d+)", str(name))
    return int(match.group(1)) if match else -1


def _sort_images(imgs: List[str]) -> List[str]:
    return sorted(
        imgs,
        key=lambda name: (_extract_leading_index(name), str(name).lower())
    )


def add_images_to_wp_post(
    website: str,
    notion_post: object,
    *,
    post_title: str = "",
    generic_input_folder: Optional[str] = None,
    imgs: Optional[List[str]] = None,
    callback=print,
    test: bool = False,
) -> Optional[str]:
    """Upload images for a Notion post to WordPress and insert them into the content.

    Supports automatic discovery of the post image folder and gracefully handles test mode.

    Args:
        website: WordPress website identifier.
        notion_post: Notion page object representing the post.
        post_title: Human-readable post title (for logging only).
        generic_input_folder: Optional override for the configured image root folder.
        imgs: Optional explicit list of image filenames to upload.
        callback: Logging callback.
        test: When True, no network actions are performed.

    Returns:
        The WordPress post hyperlink if images were inserted, None when no images found.
    """

    post_title = post_title or ""
    slug = get_post_slug(notion_post)
    if not slug:
        raise ValueError("[ERROR][add_images_to_wp_post] Post slug is empty; cannot continue.")

    if callback:
        callback(f"[INFO][add_images_to_wp_post] Preparing images for '{post_title or slug}'.")

    if generic_input_folder is None:
        generic_input_folder = load_generic_input_folder()
        if not generic_input_folder:
            raise ValueError("[ERROR][add_images_to_wp_post] Generic input folder is not configured.")

    post_folder = get_post_folder(generic_input_folder, notion_post)

    if imgs is None:
        imgs = get_ims_in_folder(post_folder, doSort=False)

    imgs = _sort_images(list(imgs))
    img_num = len(imgs)
    if img_num == 0:
        callback(f"[INFO][add_images_to_wp_post] No images to add for post '{post_title or slug}'.")
        return None

    if test:
        callback(
            f"[TEST][add_images_to_wp_post] Would upload {img_num} image(s) for slug '{slug}'."
        )
        return f"https://example.com/test-post/{slug}"

    post_types = PostTypes()
    try:
        post_type = get_post_type(notion_post)
        is_singular = post_types.is_singular(post_type)
        is_roundup = post_types.is_roundup(post_type)
    except ValueError as err:
        raise ValueError(f"[ERROR][add_images_to_wp_post] {err}") from err

    post_topic = get_post_topic_by_cat(notion_post, callback)

    wp = WordPressClient(website, callback)
    post_id = wp.get_post_id_by_slug(slug)
    callback(f"[INFO][add_images_to_wp_post] Found post ID {post_id} for slug '{slug}'.")

    if post_topic == POST_TOPIC_RECIPES and is_roundup:
        h2_count = wp.count_h2_headings(post_id)
        if h2_count == 0:
            raise ValueError(
                f"[ERROR][add_images_to_wp_post] No H2 headings found in roundup post '{slug}', cannot insert images."
            )
        if img_num > h2_count:
            raise ValueError(
                f"[ERROR][add_images_to_wp_post] More images ({img_num}) than H2 headings ({h2_count}) in roundup post '{slug}'."
            )

    formatter = WPFormatter()

    for img_name in imgs:
        img_path = os.path.join(post_folder, img_name)
        media = wp.upload_media(img_path, title=img_name)
        wp.media_for_post.append(media)

    callback(f"[INFO][add_images_to_wp_post] Uploaded {img_num} image(s) to WordPress for '{slug}'.")

    if post_topic == POST_TOPIC_RECIPES:
        if is_singular:
            featured_img = wp.media_for_post[-1]
            wp.set_featured_image_from_media(post_id, featured_img)
            callback(f"[INFO][add_images_to_wp_post] Set featured image for post '{slug}'.")
            modify_content_func = formatter.add_imgs_to_single_recipe
        elif is_roundup:
            modify_content_func = formatter.add_imgs_to_roundup
        else:
            modify_content_func = formatter.add_imgs_generic
    else:
        if post_topic:
            callback(
                f"[⚠️ WARNING][add_images_to_wp_post] Topic '{post_topic}' not specifically handled; appending images to end."
            )
        modify_content_func = formatter.add_imgs_generic

    wp.update_post_content(post_id, modify_content_func, callback)

    updated_post = wp.client.posts.get(id=post_id)
    wp_link = updated_post.get('link') if isinstance(updated_post, dict) else None
    if not wp_link:
        raise ValueError("[ERROR][add_images_to_wp_post] Unable to retrieve updated WordPress post link.")

    callback(f"[INFO][add_images_to_wp_post] Inserted images into post content for post '{slug}'.")
    return wp_link

