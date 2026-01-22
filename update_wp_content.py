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
from notion_api import (
    get_post_slug, 
    get_post_type, 
    update_post_status,
)
from notion_config import (
    PostTypes, 
    PostStatuses,
)
from wp_client import WordPressClient
from wp_formatter import (
    WPFormatter, 
    WP_FORMAT_ALT_TXT_FIELD
)


def _extract_leading_index(name: str) -> int:
    match = re.match(r"^(\d+)", str(name))
    return int(match.group(1)) if match else -1


def _sort_images(imgs: List[str]) -> List[str]:
    return sorted(
        imgs,
        key=lambda name: (_extract_leading_index(name), str(name).lower())
    )


def _sanitize_image_filename(img_name: str, post_folder: str) -> str:
    """Sanitize image filename by replacing Unicode characters with ASCII equivalents.
    
    If the filename is changed, renames the actual file on disk.
    
    Args:
        img_name: Original image filename.
        post_folder: Path to the folder containing the image.
        
    Returns:
        Sanitized image filename.
        
    Raises:
        Exception: If file renaming fails.
    """
    sanitized_img_name = img_name
    # Various hyphens and dashes
    sanitized_img_name = sanitized_img_name.replace('\u2010', '-')  # Hyphen
    sanitized_img_name = sanitized_img_name.replace('\u2011', '-')  # Non-breaking hyphen
    sanitized_img_name = sanitized_img_name.replace('\u2012', '-')  # Figure dash
    sanitized_img_name = sanitized_img_name.replace('\u2013', '-')  # En dash
    sanitized_img_name = sanitized_img_name.replace('\u2014', '-')  # Em dash
    sanitized_img_name = sanitized_img_name.replace('\u2015', '-')  # Horizontal bar
    sanitized_img_name = sanitized_img_name.replace('\u2212', '-')  # Minus sign
    # Quotes
    sanitized_img_name = sanitized_img_name.replace('\u2018', "'")  # Left single quote
    sanitized_img_name = sanitized_img_name.replace('\u2019', "'")  # Right single quote
    sanitized_img_name = sanitized_img_name.replace('\u201c', '"')  # Left double quote
    sanitized_img_name = sanitized_img_name.replace('\u201d', '"')  # Right double quote
    # Other common characters
    sanitized_img_name = sanitized_img_name.replace('\u2026', '...')  # Ellipsis
    
    # If filename changed, rename the actual file
    if sanitized_img_name != img_name:
        old_path = os.path.join(post_folder, img_name)
        new_path = os.path.join(post_folder, sanitized_img_name)
        try:
            os.rename(old_path, new_path)
        except Exception as e:
            raise
    
    return sanitized_img_name


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

    post_types = PostTypes()
    try:
        post_type = get_post_type(notion_post)
        is_singular = post_types.is_singular(post_type)
        is_roundup = post_types.is_roundup(post_type)
    except ValueError as err:
        raise ValueError(f"[ERROR][add_images_to_wp_post] {err}") from err

    post_topic = get_post_topic_by_cat(notion_post, callback)
    is_recipes_roundup = post_topic == POST_TOPIC_RECIPES and is_roundup

    post_folder = get_post_folder(generic_input_folder, notion_post, for_pins=not is_recipes_roundup)

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

    

    wp = WordPressClient(website, callback)
    post_id = wp.get_post_id_by_slug(slug)
    callback(f"[INFO][add_images_to_wp_post] Found post ID {post_id} for slug '{slug}'.")

    heading_urls = []
    if is_recipes_roundup:
        h2_headings = wp.get_h2_headings(post_id)
        if not h2_headings:
            raise ValueError(
                f"[ERROR][add_images_to_wp_post] No H2 headings found in roundup post '{slug}', cannot insert images."
            )
        h2_count = len(h2_headings)
        if img_num > h2_count:
            raise ValueError(
                f"[ERROR][add_images_to_wp_post] More images ({img_num}) than H2 headings ({h2_count}) in roundup post '{slug}'."
            )
        
        # Extract URLs from headings and check if they belong to our website
        website_base_url = wp.settings.get("base_url", "").rstrip('/')
        for heading_text, url in h2_headings:
            if url and website_base_url and url.startswith(website_base_url):
                heading_urls.append(url)
            else:
                heading_urls.append("")

    formatter = WPFormatter()

    for idx, img_name in enumerate(imgs):
        img_name = _sanitize_image_filename(img_name, post_folder)
        img_path = os.path.join(post_folder, img_name)
        
        img_name_without_ext = os.path.splitext(img_name)[0]
        
        media = wp.upload_media(img_path, title=img_name_without_ext)
        alt_text = f"{post_title} - {img_name_without_ext}" if post_title else img_name_without_ext
        
        try:
            # Test encoding to latin-1
            test_encode = alt_text.encode('latin-1')
        except UnicodeEncodeError as e:
            callback(f"[DEBUG] alt_text FAILS latin-1 encoding: {e}")
            callback(f"[DEBUG] Problematic character at position {e.start}: {repr(alt_text[e.start:e.end])}")
            callback(f"[DEBUG] Full alt_text: {repr(alt_text)}")
            callback(f"[DEBUG] post_title: {repr(post_title)}")
            callback(f"[DEBUG] img_name: {repr(img_name)}")
            raise
        
        media[WP_FORMAT_ALT_TXT_FIELD] = alt_text
        
        # Add link URL to media object if available for this image
        if is_recipes_roundup and idx < len(heading_urls) and heading_urls[idx]:
            media['link_url'] = heading_urls[idx]
            callback(f"[INFO][add_images_to_wp_post] Image {idx+1} will link to: {heading_urls[idx]}")
        
        wp.media_for_post.append(media)
        

    callback(f"[INFO][add_images_to_wp_post] Uploaded {img_num} image(s) to WordPress for '{slug}'.")

    if post_topic == POST_TOPIC_RECIPES:
        if is_singular:
            if wp.media_for_post:
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
    
    statuses = PostStatuses()
    published_imgs_id = statuses.published_imgs_added_id
    status_name = statuses.get_status_name(published_imgs_id)
    updated_notion_post = update_post_status(notion_post, published_imgs_id, test=test)
    if updated_notion_post is None:
        raise ValueError(
            f"[ERROR][add_images_to_wp_post] Failed to update Notion post status to '{status_name}' for post '{slug}'."
        )
    callback(f"[INFO][add_images_to_wp_post] Updated Notion post status to '{status_name}' for post '{slug}'.")
    return wp_link

