import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ConfigKeeper')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'WordPress')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'NotionAutomator')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'NotionUtils')))

import html
import json
import random
from chatgpt_api import *
from chatgpt_settings import *
from settings import *
from ai_txt_gen_settings import *
from ai_gen_config import *
from notion_config import (
    POST_WP_CATEGORY_PROP,
    POST_SLUG_PROP,
    NOTION_BLOCK_HEADING_1,
    NOTION_BLOCK_HEADING_2,
    NOTION_BLOCK_HEADING_3,
    NOTION_BLOCK_PARAGRAPH,
    NOTION_BLOCK_BULLETED_LIST_ITEM,
    NOTION_BLOCK_NUMBERED_LIST_ITEM,
    NOTION_BLOCK_TYPE,
    NOTION_BLOCK_TXT,
)
from notion_api import get_post_images_for_blog_url, get_page_property
from notion_recipe_parser import NotionRecipeParser
from config_utils import *
from wp_config import WEBSITE_NADYA_COOKS_TASTY
from wp_client import WordPressClient
from wp_formatter import (
    WPFormatter,
    WP_FORMAT_ITEM_TITLE_KEY,
    WP_FORMAT_ITEM_BODY_KEY,
    WP_FORMAT_ITEM_LINK_KEY,
)
from post_part_constants import *
# Import PostParts for .field_name access
from post_part_constants import PostParts

CTA_TXT = "cta_text"
CTA_ANCHOR = "cta_anchor"

class PostWriter:
    AI_TXT_GEN_PROMPTS_BY_TOPIC = {
        POST_TOPIC_RECIPES: {
            "title": AI_TXT_GEN_TITLE_PROMPT_RECIPE,
            "post": AI_TXT_GEN_POST_PROMPT_RECIPE,
        },
    }
    AI_TXT_SYS_PROMPT_STYLE_BY_TOPIC = {
        POST_TOPIC_RECIPES: "Your style is humorous, friendly, engaging, and informative. Your tone is warm, approachable, and humorous, making readers feel like they are having a conversation with a knowledgeable friend who cracks family-friendly jokes all the time.",
        POST_TOPIC_OUTFITS: "yOR STYLE IS INFORMATIVE AND TRENDY. YOUR TONE IS FRIENDLY, APPROACHABLE, AND FASHION-FORWARD, MAKING READERS FEEL INSPIRED TO EXPLORE NEW STYLES AND EXPRESS THEMSELVES THROUGH CLOTHING. YOU also have a deep understanding of the domain the outfits are for (e.g., hiking, fishing, etc.) AND INCORPORATE THAT KNOWLEDGE INTO YOUR WRITING.",
    }
    
    # CTA templates with anchor text and CTA text
    CTA_LIST = [
        {CTA_TXT: "Want to get the whole recipe?",CTA_ANCHOR: "Check it out here", },
        {CTA_TXT: "Curious about the details?", CTA_ANCHOR: "Read the full article"},
        {CTA_TXT: "Ready to try it yourself?", CTA_ANCHOR: "Get the recipe"},
        {CTA_TXT: "Interested in finding out more?", CTA_ANCHOR: "See the full recipe"},
        {CTA_TXT: "Sound interesting?", CTA_ANCHOR: "See the full recipe"},
        {CTA_TXT: "Looking for more information?", CTA_ANCHOR: "View the full post"},
        {CTA_TXT: "Want to cook it?", CTA_ANCHOR: "Here's the full recipe"},
    ]

    def __init__(self, test: bool = False, callback=print):
        self.test = test
        self.callback = callback
        self.website = ""
        self.post_title = ""
        self.post_topic = ""
        self.post_type = ""

    def __get_verbosity_by_topic__(self) -> int:
        if self._is_recipe():
            return CHATGPT_VERBOSITY_HIGH
        
        return CHATGPT_VERBOSITY_MEDIUM

    def _get_sys_prompt_base(self):
        return f"yOU ARE A PROFESSIONAL {self.post_topic} WRITER AND COPYWRITER.{self.AI_TXT_SYS_PROMPT_STYLE_BY_TOPIC[self.post_topic]}  You write in a clear and concise manner, making complex topics easy to understand. You have a knack for storytelling and can weave narratives that captivate readers.You are also skilled at SEO writing, ensuring that your content is optimized for search engines while still being enjoyable to read."


    def write_post(self) -> dict:
        """Generate post content and return structured post parts.
        
        Returns:
            dict: Post parts with keys like 'title', 'intro', 'ingredients', etc.
        """
        self.callback("[PostWriter.write_post] Starting post generation...")

        if self.website == "" or self.post_title == "" or self.post_topic == "" or self.post_type == "":
            raise ValueError(f"[ERROR][PostWriter.write_post] website, post_title, post_topic, and post_type must be set before calling write_post()")

        self.post_title = self.post_title.strip()
        self.post_topic = self.post_topic.strip()
        self.post_type = self.post_type.strip() # single item or roundup

        # depending on the type of the post, we either use AI to generate the post from scratch or we pull the already generated data from Notion

        if self.post_title == "" or self.post_topic == "" or self.post_type == "":
            raise ValueError(f"[ERROR][PostWriter.write_post] post_title, post_topic, and post_type must be set before calling write_post()")
        if self.test:
            self.callback("[PostWriter.write_post] Running in TEST mode, returning mock data")

        self.callback(f"[PostWriter.write_post] Post type: {self.post_type}")
        post_parts =  ""
        if self._if_using_our_recipe():
            self.callback(f"[PostWriter.write_post] Using OUR recipe generation method")
            post_parts = self._get_single_recipe_post_using_ours(self.notion_url)
        else:
            self.callback(f"[PostWriter.write_post] Using AI to generate post parts")

            post_parts = self._get_single_recipe_post() if self._get_is_post_type_singular() else self._get_roundup_post()

        return post_parts

    def _get_single_recipe_post(self) -> dict:
        """Generate post title and recipe parts using AI.
        
        Returns:
            dict: Post parts including title, intro, equipment, ingredients, instructions, good_to_know
        """
        self.callback("[PostWriter._get_single_recipe_post] Generating single post with AI...")
        prompt_config = AIPromptConfig(
            system_prompt="",
            user_prompt="",
            response_format={
                POST_PART_INTRO: {
                    "type": "string",
                    "description": "A 50-word bold, attention-grabbing opening that sets the stage with a relatable problem or desire. Split into 3-4 short paragraphs, each 1-2 sentences."
                },
                POST_PART_EQUIPMENT_MUST: {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Essential tools needed for the recipe"
                },
                POST_PART_EQUIPMENT_NICE: {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tools that make the process easier"
                },
                POST_PART_INGREDIENTS: {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of ingredients with quantities (quantities come before ingredients) and any extra tips or notes where needed - each ingredient on a new line"
                },
                POST_PART_INSTRUCTIONS: {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Step-by-step instructions that guide the reader through the entire cooking process - each instruction on a new line"
                },
                POST_PART_GOOD_TO_KNOW: {
                    "type": "string",
                    "description": "Additional tips, practical advice, or helpful information related to the recipe"
                }
            },
            ai_model=CHATGPT_MODEL,
            verbosity=self.__get_verbosity_by_topic__()
        )

        self.callback("[PostWriter._get_single_recipe_post] Preparing prompts...")
        prompt_config = self._get_single_recipe_post_body_prompts(prompt_config)

        self.callback(f"\n[PostWriter._get_single_recipe_post] Writing the post body...\n")
        
        if self.test:
            self.callback("[TEST][PostWriter._get_single_recipe_post] Using mock body")
            intro = "This is a test intro about the recipe. It's designed to hook you in."
            equipment_must_haves = ["Large pot", "Sharp knife", "Cutting board"]
            equipment_nice_to_haves = ["Food processor", "Kitchen scale"]
            ingredients = ["2 cups flour", "1 cup sugar", "3 eggs", "1 tsp vanilla extract"]
            instructions = ["Mix dry ingredients", "Add wet ingredients", "Bake at 350F for 30 minutes", "Let cool before serving"]
            good_to_know = "This recipe can be made ahead and frozen for up to 3 months."
        else:
            self.callback("[PostWriter._get_single_recipe_post] Calling OpenAI API for post body...")
            post_txt = send_prompt_to_openai(prompt_config, self.test)

            if post_txt["error"] != "":
                raise OpenAIAPIError(f"OpenAI API error: {post_txt['error']} '{post_txt['message']}'")

            # Parse the JSON response
            content = post_txt['message']
            self.callback(f"[PostWriter._get_single_recipe_post] Unescaping and parsing JSON response...")
            
            # Unescape HTML entities that may be present
            content = html.unescape(content)
            
            try:
                data = json.loads(content)
                intro = self._split_into_paragraphs(data.get(POST_PART_INTRO, ""))
                equipment_must_haves = data.get(POST_PART_EQUIPMENT_MUST, [])
                equipment_nice_to_haves = data.get(POST_PART_EQUIPMENT_NICE, [])
                ingredients = data.get(POST_PART_INGREDIENTS, [])
                instructions = data.get(POST_PART_INSTRUCTIONS, [])
                good_to_know = self._split_into_paragraphs(data.get(POST_PART_GOOD_TO_KNOW, ""))
            except json.JSONDecodeError as e:
                self.callback(f"[PostWriter._get_single_recipe_post] JSON parse error: {e}\nJSON:\n{content}")
                raise ValueError(f"Failed to parse AI response as JSON: {e}")
        
        self.callback(f"[PostWriter._get_single_recipe_post] Recipe parts generated")

        # Generate title based on recipe content
        # Create temporary body representation for title generation
        temp_body = f"Intro: {intro}\nIngredients: {', '.join(ingredients[:5])}...\nInstructions: {len(instructions)} steps"
        title = self._generate_title_with_ai(prompt_config, temp_body)

        return {
            POST_PART_TITLE: title,
            POST_PART_INTRO: intro,
            POST_PART_EQUIPMENT_MUST: equipment_must_haves,
            POST_PART_EQUIPMENT_NICE: equipment_nice_to_haves,
            POST_PART_INGREDIENTS: ingredients,
            POST_PART_INSTRUCTIONS: instructions,
            POST_PART_GOOD_TO_KNOW: good_to_know
        }

    def _get_roundup_post(self) -> dict:
        """Generate roundup post parts from saved items.
        
        Returns:
            dict: Post parts including title, intro, conclusion, and items list
        """
        # roundup_items structure: List of dicts with keys:
        # - "Image Title": Title of the Item
        # - "Image Description": Item URL
        # - "Notes": Summary of the post located at the URL
        self.callback("[PostWriter._get_roundup_post] Generating roundup post from saved items...")
        self.callback(f"[PostWriter._get_roundup_post] Fetching items from Notion URL...")
        roundup_items = get_post_images_for_blog_url(self.notion_url)
        if not roundup_items or len(roundup_items) == 0:
            raise ValueError(f"[ERROR][_get_roundup_post_body_prompts] No roundup items found for post '{self.notion_url}'")

        self.callback(f"[PostWriter._get_roundup_post] Found {len(roundup_items)} roundup items")
        post_items = []
        for item in roundup_items:
            title = (item.get(BLOG_POST_IMAGES_TITLE_PROP) or "").strip()
            body_text = (item.get(BLOG_POST_IMAGES_NOTES_PROP) or "").strip()
            body_text = self._split_into_paragraphs(body_text)
            
            # Get URL and append CTA link
            url = (item.get(BLOG_POST_IMAGES_DESCRIPTION_PROP) or "").strip()
            if url:
                body_text = self._append_cta(body_text, url)
            
            post_items.append({WP_FORMAT_ITEM_TITLE_KEY: title, WP_FORMAT_ITEM_BODY_KEY: body_text, WP_FORMAT_ITEM_LINK_KEY: url})

        self.callback(f"[PostWriter._get_roundup_post] Processed {len(post_items)} items for listicle")
        body_str = "\n\n".join(
            f"{idx + 1}. {entry['title']}\n{entry['body']}"
            for idx, entry in enumerate(post_items)
        )
        
        self.callback("[PostWriter._get_roundup_post] Generating title, intro, and conclusion with AI...")
        title, intro, conclusion = self._generate_title_intro_conclusion_with_ai(body_str)

        self.callback(f"[PostWriter._get_roundup_post] Roundup parts generated with {len(post_items)} items")

        return {
            POST_PART_TITLE: title,
            POST_PART_INTRO: intro,
            POST_PART_CONCLUSION: conclusion,
            POST_PART_ITEMS: post_items
        }

    def _get_single_recipe_post_using_ours(self, post_url):
        """Generate a WordPress post from a Notion recipe page URL.
        
        Args:
            post_url: The Notion page URL containing the recipe
            
        Returns:
            None (creates post on WordPress)
        """
        # Parse recipe from Notion page
        parser = NotionRecipeParser(self.callback)
        recipe_data = parser.parse_recipe_from_url(post_url)
        
        post = recipe_data['post']
        title = recipe_data['title']
        website = recipe_data['website']
        post_parts = recipe_data['post_parts']


        sections = self._update_add_missing_post_parts(post_parts)

        wp_post_parts = self._get_make_wp_code(post_elements, sections)
        # print(f"\n[DEBUG] post_parts = {wp_post_parts}")
        # # TEST:
        # post_parts = POST_PARTS_TEST

        categories = get_page_property(post, POST_WP_CATEGORY_PROP)
        
        wp = WordPressClient(website, self.callback)
        wp_post = wp.create_post(
            title=title,
            content=wp_post_parts,
            featured_image_path="",
            category_name=categories,
            slug=get_page_property(post, POST_SLUG_PROP)
        )
        if not wp_post:
            raise ValueError(f"[ERROR][generate_post_using_our] Failed to create post on WordPress for URL: {post_url}")

    def _is_recipe(self) -> bool:
        return self.post_topic == POST_TOPIC_RECIPES
        
    def _if_using_our_recipe(self) -> bool:
        """Determine if using OUR (Our Unique Recipe) generation method.
        
        Returns:
            bool: True if using OUR, False otherwise
        """
        # For now, we assume we always use OUR for single recipe posts
        return self.website == WEBSITE_NADYA_COOKS_TASTY and self._get_is_post_type_singular() and self._is_recipe()


    def _generate_title_with_ai(self, prompt_config: AIPromptConfig, post_body: str) -> str:
        """Generate post title using AI based on post body.
        
        Args:
            prompt_config: AI prompt configuration
            post_body: The body text of the post
            
        Returns:
            str: Generated title
        """
        self.callback("[PostWriter._generate_title_with_ai] Preparing title generation prompts...")
        prompt_config.system_prompt = self._get_sys_prompt_base() + self._get_post_prompt("title")
        prompt_config.user_prompt = f"""
            Generate a catchy and SEO-friendly blog post title for the following blog post about '{self.post_title}'. 
            The title should be engaging and encourage readers to click on the article. It should also include relevant keywords that would help improve the post's search engine ranking.
            Take into account {self._get_single_plural_subj()}.
            Post text:
                {post_body}
        """
        prompt_config.response_format = ""

        self.callback(f"\n[PostWriter._generate_title_with_ai] Writing the post title...\n")

        if self.test:
            self.callback("[PostWriter._generate_title_with_ai] TEST mode: Using mock title")
            return f"[TEST] The Ultimate Guide to {self.post_title}: Everything You Need to Know"
        
        self.callback("[PostWriter._generate_title_with_ai] Calling OpenAI API for title...")
        post_title = send_prompt_to_openai(prompt_config, self.test)

        if post_title["error"] != "":
            raise OpenAIAPIError(f"OpenAI API error: {post_title['error']} '{post_title['message']}'")
        
        self.callback(f"[PostWriter._generate_title_with_ai] Title generated: {post_title['message']}")
        return post_title['message']

    def _generate_title_intro_conclusion_with_ai(self, post_body: str) -> tuple[str, str, str]:
        """Generate post title, intro, and conclusion using AI in a single request.
        
        Args:
            post_body: The body text of the post
            
        Returns:
            tuple: (title, intro, conclusion)
        """
        self.callback("[PostWriter._generate_title_intro_conclusion_with_ai] Preparing combined generation prompts...")
        
        prompt_config = AIPromptConfig(
            system_prompt=self._get_sys_prompt_base(),
            user_prompt=f"""
                Generate the following for a blog post about '{self.post_title}'. Take into account {self._get_single_plural_subj()}.
                
                Post body content:
                {post_body}
                
                Please provide:
                1. A catchy and SEO-friendly blog post title (engaging and keyword-rich)
                2. A 50-word introduction paragraph that hooks the reader
                3. A 50-word conclusion paragraph that wraps up the post
            """,
            response_format={
                POST_PART_TITLE: {
                    "type": "string",
                    "description": "Catchy and SEO-friendly blog post title"
                },
                POST_PART_INTRO: {
                    "type": "string",
                    "description": "50-word introduction paragraph"
                },
                POST_PART_CONCLUSION: {
                    "type": "string",
                    "description": "50-word conclusion paragraph"
                }
            },
            ai_model=CHATGPT_MODEL,
            verbosity=self.__get_verbosity_by_topic__()
        )

        self.callback("[PostWriter._generate_title_intro_conclusion_with_ai] Calling OpenAI API...")

        if self.test:
            self.callback("[PostWriter._generate_title_intro_conclusion_with_ai] TEST mode: Using mock data")
            title = f"[TEST] The Ultimate Guide to {self.post_title}: Everything You Need to Know"
            intro = f"[TEST] Welcome to our comprehensive guide about {self.post_title}. In this article, we'll explore everything you need to know, from the basics to advanced tips. Whether you're a beginner or an expert, you'll find valuable insights here. Let's dive in and discover what makes this topic so fascinating and important!"
            conclusion = f"[TEST] We hope this guide about {self.post_title} has been helpful and informative. Remember to apply these tips in your own practice. Stay tuned for more great content, and don't hesitate to share your experiences with us. Thank you for reading!"
            return title, intro, conclusion
        
        response = send_prompt_to_openai(prompt_config, self.test)

        if response["error"] != "":
            raise OpenAIAPIError(f"OpenAI API error: {response['error']} '{response['message']}'")
        
        # Parse the JSON response
        content = response['message']
        self.callback(f"[PostWriter._generate_title_intro_conclusion_with_ai] Unescaping and parsing JSON response...")
        
        # Unescape HTML entities that may be present
        content = html.unescape(content)
        
        try:
            data = json.loads(content)
            title = data.get(POST_PART_TITLE, "")
            intro = self._split_into_paragraphs(data.get(POST_PART_INTRO, ""))
            conclusion = self._split_into_paragraphs(data.get(POST_PART_CONCLUSION, ""))
        except json.JSONDecodeError as e:
            self.callback(f"[PostWriter._generate_title_intro_conclusion_with_ai] JSON parse error: {e}\nJSON:\n{content}")
            raise ValueError(f"Failed to parse AI response as JSON: {e}")
        
        self.callback(f"[PostWriter._generate_title_intro_conclusion_with_ai] Generated - Title: {len(title)} chars, Intro: {len(intro)} chars, Conclusion: {len(conclusion)} chars")
        
        return title, intro, conclusion

    def _is_escaped(self, text: str) -> bool:
        return text != html.unescape(text)

    def _split_into_paragraphs(self, text: str, sentences_per_paragraph: int = 2) -> str:
        """Split text into paragraphs with specified number of sentences each.
        
        Args:
            text: The text to split into paragraphs
            sentences_per_paragraph: Number of sentences per paragraph (default: 2)
            
        Returns:
            Text formatted with paragraph breaks
        """
        if not text or not text.strip():
            return text
        
        # Split by sentence-ending punctuation followed by space
        import re
        sentences = re.split(r'([.!?]+\s+)', text)
        
        # Reconstruct sentences with their punctuation
        reconstructed = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                reconstructed.append(sentences[i] + sentences[i + 1].rstrip())
        
        # Handle last sentence if it doesn't have trailing punctuation marker
        if len(sentences) % 2 == 1 and sentences[-1].strip():
            reconstructed.append(sentences[-1].strip())
        
        # Group sentences into paragraphs
        paragraphs = []
        for i in range(0, len(reconstructed), sentences_per_paragraph):
            paragraph = ' '.join(reconstructed[i:i + sentences_per_paragraph])
            if paragraph.strip():
                paragraphs.append(paragraph.strip())
        
        return '\n'.join(paragraphs)

    def _get_post_prompt(self, prompt_type) -> str:
        prompt = self.AI_TXT_GEN_PROMPTS_BY_TOPIC.get(self.post_topic, {}).get(prompt_type, "")
        if not prompt:
            raise ValueError(f"[ERROR][_get_post_prompt] No '{prompt_type}' prompt found for post topic '{self.post_topic}'")
        return prompt

    def _get_single_recipe_post_body_prompts(self, prompt_config: AIPromptConfig):
        prompt_config.system_prompt = self._get_sys_prompt_base() + self._get_post_prompt("post")
        prompt_config.user_prompt = f"""
        Write a detailed {self.post_topic} blog post about '{self.post_title}'. Make sure to follow the structure and style guidelines provided.
        The post should be engaging, informative, and easy to read. Ensure the content is original and provides value to the readers.
        Take into account {self._get_single_plural_subj()}.
        """

        return prompt_config

    def _get_single_plural_subj(self) -> str:
        if self.post_topic not in POST_TOPIC_AI_PROMPT_NOUNS:
            raise ValueError(
                f"[ERROR][_get_single_plural_subj] Post topic '{self.post_topic}' "
                "does not have a corresponding mapping in POST_TOPIC_AI_PROMPT_NOUNS."
            )
        return (
            "a single item and not plurals"
            if self._get_is_post_type_singular()
            else POST_TOPIC_AI_PROMPT_NOUNS[self.post_topic]
        )

    def _get_is_post_type_singular(self) -> bool:
        return PostTypes().is_singular(self.post_type)
    
    def _get_cta_with_link(self, url: str) -> str:
        """Generate a CTA with link HTML.
        
        Args:
            url: The URL to link to
            
        Returns:
            HTML string with CTA and link
        """
        cta_template = random.choice(self.CTA_LIST)
        anchor_text = cta_template[CTA_ANCHOR]
        cta_text = cta_template[CTA_TXT]
        
        return f'{cta_text} <a href="{url}" target="_blank" rel="noopener">{anchor_text}</a>.'
    
    def _append_cta(self, body_text: str, url: str) -> str:
        """Append CTA with link to body text.
        
        Args:
            body_text: The body text to append CTA to
            url: The URL to link to
            
        Returns:
            Body text with CTA appended
        """
        if not body_text or not url:
            return body_text
        
        cta_html = self._get_cta_with_link(url)
        
        # Append CTA on a new line
        return f"{body_text}\n{cta_html}"

    def _get_generate_post_parts(self, post_elements, test=False):
        """Generate enhanced post parts from Notion elements using AI.
        
        Args:
            post_elements: List of Notion block elements
            test: Whether to use test mode (default: False)
            
        Returns:
            str: WordPress HTML content
        """
        ##### Test
        if test == True:
            self.callback(f"[get_generate_post_parts] Running in TEST mode!")
            
        # Merge the text from remaining elements
        merged_text = '\n'.join(element['text'] 
                               for element in post_elements 
                               if 'text' in element)
        merged_text = merged_text.strip()

        sys_prompt = "You are a skilled recipe copy writer who specializes in writing engaging recipe posts. You know how to write a captivating intro that makes the reader want to read the whole recipe.\n"
        user_prompt = f"write a 50-word intro, a section about a low fodmap portion, what you need to know: a section with additional useful info or facts about the reicpe (ingredients or instructions), and a 100-word outro for the recipe '{merged_text}'\n"
        user_prompt += f"Add new lines to the text to improve readability.\n" 
        user_prompt += "Do not add Intro or its synonyms as a heading, Do not add Outro or its synonyms as a heading, Do not add Low FODMAP or its synonyms as a heading, Do not add 'what you need to know' or its synonyms as a heading\n"

        response_format = {
            PostParts.INTRO.field_name: {
                "type": "string",
                "description": "The intro of the recipe"
            },
            PostParts.EQUIPMENT.field_name: {
                "type": "string",
                "description": "The equipment required for the recipe"
            },        
            PostParts.LOW_FODMAP_PORTION.field_name: {
                "type": "string",
                "description": "The Low fodmap portion section"
            },
            PostParts.GOOD_TO_KNOW.field_name: {
                "type": "string",
                "description": "what you need to know: extra useful informatoin about the recipe"
            },
            PostParts.CONCLUSION.field_name: {
                "type": "string",
                "description": "conclusion for recipe"
            }
        }

        res = {}
        if test:
            sections = {
                PostParts.INTRO.field_name: "Intro",
                PostParts.EQUIPMENT.field_name: "- Eq",
                PostParts.LOW_FODMAP_PORTION.field_name: "LF portion",
                PostParts.GOOD_TO_KNOW.field_name: "to know",
                PostParts.CONCLUSION.field_name: "conc"
            }
            res['error'] = ''
            res['message'] = sections
        else:
            res = send_prompt_to_openai(sys_prompt, user_prompt, response_format)
            if res["error"] != "":
                raise OpenAIAPIError(f"OpenAI API error: {res['error']} '{res['message']}'")
            
            # Unescape HTML symbols and convert to JSON
            sections_json = html.unescape(res["message"])
            sections = json.loads(sections_json)
            SECTION_NUMBER = 5
            if len(sections) != SECTION_NUMBER:
                raise ValueError(f"Expected {SECTION_NUMBER} sections but got {len(sections)}")

        return self._get_make_wp_code(post_elements, sections)

    def _update_add_missing_post_parts(self, post_elements):
        """Generate enhanced post parts from Notion elements using AI.
        
        Args:
            post_elements: List of Notion block elements
            
        Returns:
            str: WordPress HTML content
        """
        ##### Test
        if self.test == True:
            self.callback(f"[get_generate_post_parts] Running in TEST mode!")
            
        # Merge the text from remaining elements
        merged_text = '\n'.join(element['text'] 
                               for element in post_elements 
                               if 'text' in element)
        merged_text = merged_text.strip()

        sys_prompt = "You are a skilled recipe copy writer who specializes in writing engaging recipe posts. You know how to write a captivating intro that makes the reader want to read the whole recipe.\n"
        user_prompt = f"write a 50-word intro, a section about a low fodmap portion, what you need to know: a section with additional useful info or facts about the reicpe (ingredients or instructions), and a 100-word outro for the recipe '{merged_text}'\n"
        user_prompt += f"Add new lines to the text to improve readability.\n" 
        user_prompt += "Do not add Intro or its synonyms as a heading, Do not add Outro or its synonyms as a heading, Do not add Low FODMAP or its synonyms as a heading, Do not add 'what you need to know' or its synonyms as a heading\n"

        response_format = {
            PostParts.INTRO.field_name: {
                "type": "string",
                "description": "The intro of the recipe"
            },
            PostParts.EQUIPMENT.field_name: {
                "type": "string",
                "description": "The equipment required for the recipe"
            },        
            PostParts.LOW_FODMAP_PORTION.field_name: {
                "type": "string",
                "description": "The Low fodmap portion section"
            },
            PostParts.GOOD_TO_KNOW.field_name: {
                "type": "string",
                "description": "what you need to know: extra useful informatoin about the recipe"
            },
            PostParts.CONCLUSION.field_name: {
                "type": "string",
                "description": "conclusion for recipe"
            }
        }

        res = {}
        if self.test:
            sections = {
                PostParts.INTRO.field_name: "Intro",
                PostParts.EQUIPMENT.field_name: "- Eq",
                PostParts.LOW_FODMAP_PORTION.field_name: "LF portion",
                PostParts.GOOD_TO_KNOW.field_name: "to know",
                PostParts.CONCLUSION.field_name: "conc"
            }
            res['error'] = ''
            res['message'] = sections
        else:
            res = send_prompt_to_openai(sys_prompt, user_prompt, response_format)
            if res["error"] != "":
                raise OpenAIAPIError(f"OpenAI API error: {res['error']} '{res['message']}'")
            
            # Unescape HTML symbols and convert to JSON
            sections_json = html.unescape(res["message"])
            sections = json.loads(sections_json)
            SECTION_NUMBER = 5
            if len(sections) != SECTION_NUMBER:
                raise ValueError(f"Expected {SECTION_NUMBER} sections but got {len(sections)}")

        return sections

    def _get_make_wp_code(self, post_elements, sections):
        """Convert Notion elements and AI-generated sections to WordPress HTML.
        
        Args:
            post_elements: List of Notion block elements
            sections: Dict with AI-generated sections (intro, equipment, etc.)
            
        Returns:
            str: WordPress HTML content
        """
        formatter = WPFormatter()
        parts = []
        
        # Add intro
        parts.extend(formatter._text_to_paragraphs(sections["intro"]))
        
        # Add equipment section
        parts.append(formatter.h2("Equipment"))
        parts.extend(formatter._text_to_paragraphs(sections["equipment"]))
        
        # Convert Notion elements to WordPress blocks
        i = 0
        while i < len(post_elements):
            element = post_elements[i]
            
            if element[NOTION_BLOCK_TYPE] == NOTION_BLOCK_HEADING_1 or element[NOTION_BLOCK_TYPE] == NOTION_BLOCK_HEADING_2:
                parts.append(formatter.h2(element[NOTION_BLOCK_TXT]))
            elif element[NOTION_BLOCK_TYPE] == NOTION_BLOCK_HEADING_3:
                parts.append(formatter.h3(element[NOTION_BLOCK_TXT]))
            elif element[NOTION_BLOCK_TYPE] == NOTION_BLOCK_BULLETED_LIST_ITEM:
                # Collect consecutive bulleted items
                list_items = []
                while i < len(post_elements) and post_elements[i][NOTION_BLOCK_TYPE] == NOTION_BLOCK_BULLETED_LIST_ITEM:
                    list_items.append(post_elements[i][NOTION_BLOCK_TXT])
                    i += 1
                parts.append(formatter.unordered_list(list_items))
                continue  # Skip the i increment at the end
            elif element[NOTION_BLOCK_TYPE] == NOTION_BLOCK_NUMBERED_LIST_ITEM:
                # Collect consecutive numbered items
                list_items = []
                while i < len(post_elements) and post_elements[i][NOTION_BLOCK_TYPE] == NOTION_BLOCK_NUMBERED_LIST_ITEM:
                    list_items.append(post_elements[i][NOTION_BLOCK_TXT])
                    i += 1
                parts.append(formatter.ordered_list(list_items))
                continue  # Skip the i increment at the end
            elif element[NOTION_BLOCK_TYPE] == NOTION_BLOCK_PARAGRAPH:
                parts.append(formatter._wrap_paragraph(element[NOTION_BLOCK_TXT]))
            
            i += 1
        
        # Add remaining sections
        parts.append(formatter.h2(PostParts.LOW_FODMAP_PORTION.wp_heading))
        parts.extend(formatter._text_to_paragraphs(sections[PostParts.LOW_FODMAP_PORTION.field_name]))
        
        parts.append(formatter.h2(PostParts.GOOD_TO_KNOW.wp_heading))
        parts.extend(formatter._text_to_paragraphs(sections[PostParts.GOOD_TO_KNOW.field_name]))
        
        parts.append(formatter.h2(PostParts.CONCLUSION.wp_heading))
        parts.extend(formatter._text_to_paragraphs(sections[PostParts.CONCLUSION.field_name]))
        
        return '\n\n'.join(parts)
    