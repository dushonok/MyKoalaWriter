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

def create_wp_post(notion_post, website, post_parts: dict, post_slug, categories, callback=print, test=False):

    callback(f"\n[INFO][post_generate] Creating post on WordPress site: {website}")
    
    post_type = get_post_type(post)
    is_singular = PostTypes().is_singular(post_type)
    post_topic = get_post_topic_from_cats(categories)

    # Extract title from post_parts
    post_title = post_parts.get(POST_PART_TITLE, "")
    
    # Format content based on post type
    callback(f"[INFO][create_wp_post] Formatting post content...")
    formatter = WPFormatter()
    
    if post_topic == POST_TOPIC_RECIPES and is_singular:
        # Single recipe post
        post_content = formatter.generate_recipe(
            intro=post_parts.get(POST_PART_INTRO, ""),
            equipment_must_haves=post_parts.get(POST_PART_EQUIPMENT_MUST, []),
            equipment_nice_to_haves=post_parts.get(POST_PART_EQUIPMENT_NICE, []),
            ingredients=post_parts.get(POST_PART_INGREDIENTS, []),
            instructions=post_parts.get(POST_PART_INSTRUCTIONS, []),
            good_to_know=post_parts.get(POST_PART_GOOD_TO_KNOW, "")
        )
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
        raise ValueError(f"[ERROR][create_wp_post] Failed to create post on WordPress for URL: {post_url}")
    
    return wp_post