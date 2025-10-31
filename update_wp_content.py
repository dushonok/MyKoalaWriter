import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ConfigKeeper')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'WordPress')))

from wp_client import WordPressClient

def add_images_to_wp_post(website: str, notion_post: object, generic_input_folder: str, imgs: list, callback=print, test=False) -> str:
    # Update post content via surgical edit
    res = wp.update_post_content(postID, _modify_content)
    callback(f"[INFO][add_images_to_wp_post] Inserted images into post content for post '{slug}'")

    featured_img = imgs[0]
    callback(f"[INFO][add_images_to_wp_post] Adding images to post '{slug}' including featured image: {featured_img}")
    featured_img_path = os.path.join(get_post_folder(generic_input_folder, post), featured_img)

    wp = WordPressClient(website, callback)
    postID = wp.get_post_id_by_slug(slug)
    if postID is None:
        callback(f"[ERROR][add_images_to_wp_post] Could not find post ID for post slug '{slug}'")
        return None
    callback(f"[INFO][add_images_to_wp_post] Found post ID {postID} for post slug '{slug}'")

    media = wp.upload_media(featured_img_path, title=featured_img)
    wp.set_featured_image(postID, media['id'])
    callback(f"[INFO][add_images_to_wp_post] Set featured image for post '{slug}'")

    # Exclude the featured image from the list
    remaining_imgs = [img for img in imgs if img != featured_img]
    if not remaining_imgs:
        callback(f"[INFO][add_images_to_wp_post] No additional images to insert into post content for post '{slug}'")
        return None

    # Upload images and prepare block JSON
    uploaded_imgs = []
    for img in remaining_imgs:
        media = wp.upload_media(os.path.join(get_post_folder(generic_input_folder, post), img), title=img)
        uploaded_imgs.append(media['source_url'])

    alt_text = f"{slug.replace('-', ' ').replace('_', ' ')} pin image"

    # Update post content via surgical edit
    modify_content_func = None
    if post_topic == POST_TOPIC_RECIPES
        if post_type == POST_POST_TYPE_SINGLE_ITEM_ID:
            modify_content_func = _modify_content_single_recipe
        elif post_type == POST_POST_TYPE_ROUNDUP_ID:
            modify_content_func = _modify_content_roundup
    else:
        callback(f"[⚠️ WARNING][add_images_to_wp_post] Post topic '{post_topic}' not specifically handled, inserting images at the end of the post '{slug}'")
        def _modify_content_generic(content: str) -> str:
            updated = content
            for img_url in uploaded_imgs:
                img_block = _make_image_block(img_url, alt_text)
                updated += "\n" + img_block
            return updated
        modify_content_func = _modify_content_generic

    wp_post = wp.update_post_content(postID, modify_content_func)
    wp_link = wp_post.get('link')
    if wp_link is None:
        raise ValueError(f"[ERROR][add_wp_img] WordPress post was not updated with images!")
    callback(f"[INFO][add_images_to_wp_post] Inserted images into post content for post '{slug}'")
    return wp_link

def _make_image_block(url: str, alt: str) -> str:
    """Return a Gutenberg image block string."""
    return (
        f'<!-- wp:image {{"id":0,"sizeSlug":"full","linkDestination":"none"}} -->\n'
        f'<figure class="wp-block-image size-full">'
        f'<img src="{url}" alt="{alt}"/></figure>\n'
        f'<!-- /wp:image -->'
    )

def _modify_content_single_recipe(content: str) -> str:
    # up to 4 images? not counting the featured image
    # Before Ingredients, before Preparations or Instructions, before Notes or Final Words, at end of post if enough images

    IMG_NUMBER_TO_INSERT = 4
    available_img_num = len(uploaded_imgs)  # featured image is already excluded
    if available_img_num < 1:
        return content  # nothing to insert
    updated = content

    # Insert image at the end of the post if we have enough images
    if uploaded_imgs and available_img_num >= IMG_NUMBER_TO_INSERT:
        img_block_end = _make_image_block(uploaded_imgs[available_img_num-1], alt_text)
        updated += "\n" + img_block_end
        available_img_num -= 1

    # Insert image after "Ingredients" heading if present and if there is a second image
    pattern = rf'({re.escape(INGREDIENTS_WP_BLOCK_CODE_GOOD)})'
    if re.search(pattern, updated, re.IGNORECASE):
        img_block_ingredients = _make_image_block(uploaded_imgs[0], alt_text) + "\n"
        updated = re.sub(pattern, r'\1' + img_block_ingredients, updated, count=1, flags=re.IGNORECASE)
        available_img_num -= 1
    else:
        # Try searching for INGREDIENTS_WP_BLOCK_CODE_BAD and replace with INGREDIENTS_WP_BLOCK_CODE_GOOD, then search again
        pattern_bad = rf'({re.escape(INGREDIENTS_WP_BLOCK_CODE_BAD)})'
        if re.search(pattern_bad, updated, re.IGNORECASE):
            updated = re.sub(pattern_bad, INGREDIENTS_WP_BLOCK_CODE_GOOD, updated, count=1, flags=re.IGNORECASE)
            # Now try again to insert after the good heading
            pattern_good = rf'({re.escape(INGREDIENTS_WP_BLOCK_CODE_GOOD)})'
            if re.search(pattern_good, updated, re.IGNORECASE):
                img_block_ingredients = _make_image_block(uploaded_imgs[1], alt_text) + "\n"
                updated = re.sub(pattern_good, r'\1' + img_block_ingredients, updated, count=1, flags=re.IGNORECASE)
                available_img_num -= 1
            else:
                callback(f"[⚠️ WARNING][_modify_content_single_recipe] Neither 'Ingredients' heading variant found in post '{slug}', skipping 1st image insertion.")
        else:
            callback(f"[INFO][_modify_content_single_recipe] 'Ingredients' heading not found in post '{slug}', skipping 1st image insertion.")

    # second spot
    pattern_prep_instr = rf'({re.escape(PREPARATIONS_WP_BLOCK_CODE)}|{re.escape(INSTRUCTIONS_WP_BLOCK_CODE)})'
    if re.search(pattern_prep_instr, updated, re.IGNORECASE) and available_img_num >= 1:
        img_block_prep_instr = _make_image_block(uploaded_imgs[1], alt_text) + "\n"
        updated = re.sub(pattern_prep_instr, r'\1' + img_block_prep_instr, updated, count=1, flags=re.IGNORECASE)
        available_img_num -= 1
    else:
        callback(f"[INFO][_modify_content_single_recipe] 'Preparations' or 'Instructions' heading not found in post '{slug}', skipping 2nd image insertion.")

    # third spot
    pattern_notes_final = rf'({re.escape(NOTES_WP_BLOCK_CODE)}|{re.escape(FINAL_WORDS_WP_BLOCK_CODE)})'
    if re.search(pattern_notes_final, updated, re.IGNORECASE) and available_img_num >= 1:
        img_block_notes_final = _make_image_block(uploaded_imgs[2], alt_text) + "\n"
        updated = re.sub(pattern_notes_final, r'\1' + img_block_notes_final, updated, count=1, flags=re.IGNORECASE)
        available_img_num -= 1
    else:
        callback(f"[INFO][_modify_content_single_recipe] 'Notes' or 'Final Words' heading not found in post '{slug}', skipping 3rd image insertion.")    

    return updated

def _modify_content_roundup(content: str) -> str:
    pass