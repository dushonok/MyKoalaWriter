import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ConfigKeeper')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'WordPress')))

from wp_client import WordPressClient
from post_part_constants import *

def add_images_to_wp_post(website: str, notion_post: object, generic_input_folder: str, imgs: list, callback=print, test=False) -> str:
    img_num = len(imgs)
    if img_num == 0:
        callback(f"[INFO][add_images_to_wp_post] No images to add for post '{notion_post}'")
        return None

    wp = WordPressClient(website, callback)
    postID = wp.get_post_id_by_slug(slug)
    if postID is None:
        callback(f"[ERROR][add_images_to_wp_post] Could not find post ID for post slug '{slug}'")
        return None
    callback(f"[INFO][add_images_to_wp_post] Found post ID {postID} for post slug '{slug}'")

    # Upload images and prepare block JSON
    for img in imgs:
        media = wp.upload_media(os.path.join(get_post_folder(generic_input_folder, post), img), title=img)
        wp.media_for_post.append(media['source_url'])
    callback(f"[INFO][add_images_to_wp_post] Uploaded images to WordPress for post '{slug}'")

    featured_img = wp.media_for_post[img_num-1]
    wp.set_featured_image_from_media(postID, featured_img)
    callback(f"[INFO][add_images_to_wp_post] Set featured image for post '{slug}'")
    
    alt_text = f"{slug.replace('-', ' ').replace('_', ' ')} pin image"

    # Update post content via surgical edit
    modify_content_func = None
    post_type = get_post_type(post)
    post_topic = get_post_topic_by_cat(post, callback)

    if post_topic == POST_TOPIC_RECIPES:
        if PostTypes().is_singular(post_type):
            modify_content_func = wp_formatter.add_imgs_to_recipe
        elif PostTypes().is_roundup(post_type):
            modify_content_func = wp_formatter.add_imgs_to_roundup
        else:
            raise ValueError(f"[ERROR][add_images_to_wp_post] Unsupported post type '{post_type}' for post topic '{post_topic}'")
    else:
        callback(f"[⚠️ WARNING][add_images_to_wp_post] Post topic '{post_topic}' not specifically handled, inserting images at the end of the post '{slug}'")
        modify_content_func = wp_formatter.add_imgs_generic

    # Update post content via surgical edit
    wp_post = wp.update_post_content(postID, modify_content_func)
    wp_link = wp_post.get('link')
    if wp_link is None:
        raise ValueError(f"[ERROR][add_wp_img] WordPress post was not updated_content with images!")
    callback(f"[INFO][add_images_to_wp_post] Inserted images into post content for post '{slug}'")
    return wp_link

