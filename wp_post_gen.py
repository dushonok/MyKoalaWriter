import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'WordPress')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ConfigKeeper')))

import html
import json

from config_utils import *
from wp_client import WordPressClient

def create_wp_post(notion_post, website, post_title, post_content, post_slug, categories, callback=print):

    print(f"\n[INFO][post_generate] Creating post on WordPress site: {website}")
    
    wp = WordPressClient(website, callback)
    wp_post = wp.create_post(
        title=post_title,
        content=post_content,
        featured_image_path="",
        category_name=categories, #FIX - our categories come in aform "Main / Secondary" and need to be  parsed - get_page_property(post, POST_WP_CATEGORY_PROP),
        slug=post_slug
    )
    if not wp_post:
        raise ValueError(f"[ERROR][post_generate] Failed to create post on WordPress for URL: {post_url}")
    
    return wp_post