import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'WordPress')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ConfigKeeper')))

import html
import json

from config_utils import *
from wp_client import WordPressClient
from wp_formatter import WPFormatter
from post_part_constants import *
from notion_api import (
    get_post_type,
)

def create_wp_post(notion_post: dict, website: str, post_parts: dict, post_slug: str, categories: str, callback=print, test=False):

    callback(f"\n[INFO][create_wp_post] Creating post on WordPress site: {website}")

    if not website or website.strip() == "":
        raise ValueError("[ERROR][create_wp_post] website cannot be None or empty")

    if not notion_post or len(notion_post) == 0:
        raise ValueError("[ERROR][create_wp_post] notion_post cannot be None or empty")

    if not post_parts or len(post_parts) == 0:
        raise ValueError("[ERROR][create_wp_post] post_parts cannot be None or empty")
    
    if not post_slug or post_slug.strip() == "":
        raise ValueError("[ERROR][create_wp_post] post_slug cannot be None or empty")

    post_type = get_post_type(notion_post)
    if not post_type or post_type.strip() == "":
        raise ValueError("[ERROR][create_wp_post] post_type cannot be None or empty")

    is_singular = PostTypes().is_singular(post_type)
    post_topic = get_post_topic_from_cats(categories)

    # Format content based on post type
    callback(f"[INFO][create_wp_post] Formatting post content...")
    formatter = WPFormatter()
    
    if post_topic == POST_TOPIC_RECIPES and is_singular:
        # Single recipe post
        post_content = formatter.generate_recipe(post_parts)
    elif not is_singular:
        # Roundup/listicle post
        post_content = formatter.generate_listicle(
            intro=post_parts.get(POST_PART_INTRO, ""),
            conclusion=post_parts.get(POST_PART_CONCLUSION, ""),
            items=post_parts.get(POST_PART_ITEMS, [])
        )
    else:
        raise ValueError(f"[ERROR][create_wp_post] Unsupported post type/topic combination: '{post_type}' / '{post_topic}'")
    
    callback(f"[INFO][create_wp_post] Content formatted ({len(post_content)} chars)")

    # Extract title from post_parts
    post_title = post_parts.get(POST_PART_TITLE, "")
    
    if test:
        callback(f"\n[TEST MODE][create_wp_post] Post Title:\n{post_title}\n")
        callback(f"\n[TEST MODE][create_wp_post] Post Content:\n{post_content}\n")
        return {
            "link": "https://example.com/test-post",
            "id": 123,
            "slug": post_slug
        }
    
    wp = WordPressClient(website, callback)
    wp_post = wp.create_post(
        title=post_title,
        content=post_content,
        featured_image_path="",
        category_name=categories, #FIX - our categories come in aform "Main / Secondary" and need to be  parsed - get_page_property(post, POST_WP_CATEGORY_PROP),
        slug=post_slug
    )
    if not wp_post:
        raise ValueError(f"[ERROR][create_wp_post] Failed to create post on WordPress: {post_title}")
    
    return wp_post