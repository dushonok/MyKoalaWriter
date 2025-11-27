import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ConfigKeeper')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'WordPress')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'NotionAutomator')))

import html
import json
import random
from chatgpt_api import *
from chatgpt_settings import *
from settings import *
from ai_txt_gen_settings import *
from ai_gen_config import *
from notion_config import *
from notion_api import get_post_images_for_blog_url
from wp_formatter import (
    WPFormatter,
    WP_FORMAT_ITEM_TITLE_KEY,
    WP_FORMAT_ITEM_BODY_KEY,

)

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

    def __get_verbosity_by_topic__(self) -> int:
        if self.post_topic == POST_TOPIC_RECIPES:
            return CHATGPT_VERBOSITY_HIGH
        else:
            return CHATGPT_VERBOSITY_MEDIUM

    def _get_sys_prompt_base(self):
        return f"yOU ARE A PROFESSIONAL {self.post_topic} WRITER AND COPYWRITER.{self.AI_TXT_SYS_PROMPT_STYLE_BY_TOPIC[self.post_topic]}  You write in a clear and concise manner, making complex topics easy to understand. You have a knack for storytelling and can weave narratives that captivate readers.You are also skilled at SEO writing, ensuring that your content is optimized for search engines while still being enjoyable to read."


    def write_post(self):
        self.callback("[PostWriter.write_post] Starting post generation...")
        self.post_title = self.post_title.strip()
        self.post_topic = self.post_topic.strip()
        self.post_type = self.post_type.strip() # single item or roundup

        # depending on the type of the post, we either use AI to generate the post from scratch or we pull the already generated data from Notion

        if self.post_title == "" or self.post_topic == "" or self.post_type == "":
            raise ValueError(f"[ERROR][PostWriter.write_post] post_title, post_topic, and post_type must be set before calling write_post()")
        if self.test:
            self.callback("[PostWriter.write_post] Running in TEST mode, returning mock data")

        self.callback(f"[PostWriter.write_post] Post type: {self.post_type}")
        title, body = self._get_single_post() if self._get_is_post_type_singular() else self._get_roundup_post()

        return title, body

    def _get_single_post(self) -> tuple[str, str]:
        """Generate post title and body using AI.
        
        Returns:
            tuple: (title, post_body)
        """
        self.callback("[PostWriter._get_single_post] Generating single post with AI...")
        prompt_config = AIPromptConfig(
            system_prompt="",
            user_prompt="",
            response_format={
                "intro": {
                    "type": "string",
                    "description": "A 50-word bold, attention-grabbing opening that sets the stage with a relatable problem or desire. Split into 3-4 short paragraphs, each 1-2 sentences."
                },
                "equipment_must_haves": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Essential tools needed for the recipe"
                },
                "equipment_nice_to_haves": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tools that make the process easier"
                },
                "ingredients": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of ingredients with quantities (quantities come before ingredients) and any extra tips or notes where needed - each ingredient on a new line"
                },
                "instructions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Step-by-step instructions that guide the reader through the entire cooking process - each instruction on a new line"
                },
                "good_to_know": {
                    "type": "string",
                    "description": "Additional tips, practical advice, or helpful information related to the recipe"
                }
            },
            ai_model=CHATGPT_MODEL,
            verbosity=self.__get_verbosity_by_topic__()
        )

        self.callback("[PostWriter._get_single_post] Preparing prompts...")
        prompt_config = self._get_single_post_body_prompts(prompt_config)

        self.callback(f"\n[PostWriter._get_single_post] Writing the post body...\n")
        
        if self.test:
            self.callback("[TEST][PostWriter._get_single_post] Using mock body")
            intro = "This is a test intro about the recipe. It's designed to hook you in."
            equipment_must_haves = ["Large pot", "Sharp knife", "Cutting board"]
            equipment_nice_to_haves = ["Food processor", "Kitchen scale"]
            ingredients = ["2 cups flour", "1 cup sugar", "3 eggs", "1 tsp vanilla extract"]
            instructions = ["Mix dry ingredients", "Add wet ingredients", "Bake at 350F for 30 minutes", "Let cool before serving"]
            good_to_know = "This recipe can be made ahead and frozen for up to 3 months."
        else:
            self.callback("[PostWriter._get_single_post] Calling OpenAI API for post body...")
            post_txt = send_prompt_to_openai(prompt_config, self.test)

            if post_txt["error"] != "":
                raise OpenAIAPIError(f"OpenAI API error: {post_txt['error']} '{post_txt['message']}'")

            # Parse the JSON response
            content = post_txt['message']
            self.callback(f"[PostWriter._get_single_post] Unescaping and parsing JSON response...")
            
            # Unescape HTML entities that may be present
            content = html.unescape(content)
            
            try:
                data = json.loads(content)
                intro = self._split_into_paragraphs(data.get("intro", ""))
                equipment_must_haves = data.get("equipment_must_haves", [])
                equipment_nice_to_haves = data.get("equipment_nice_to_haves", [])
                ingredients = data.get("ingredients", [])
                instructions = data.get("instructions", [])
                good_to_know = self._split_into_paragraphs(data.get("good_to_know", ""))
            except json.JSONDecodeError as e:
                self.callback(f"[PostWriter._get_single_post] JSON parse error: {e}\nJSON:\n{content}")
                raise ValueError(f"Failed to parse AI response as JSON: {e}")
        
        self.callback(f"[PostWriter._get_single_post] Post body parts generated. Formatting into final body...")
        body = WPFormatter().generate_recipe(intro, equipment_must_haves, equipment_nice_to_haves, ingredients, instructions, good_to_know)
        self.callback(f"[PostWriter._get_single_post] Recipe formatted ({len(body)} chars)")
        

        title = self._generate_title_with_ai(prompt_config, body)

        return title, body

    def _get_roundup_post(self) -> tuple[str, str]:
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
            
            post_items.append({WP_FORMAT_ITEM_TITLE_KEY: title, WP_FORMAT_ITEM_BODY_KEY: body_text})

        self.callback(f"[PostWriter._get_roundup_post] Processed {len(post_items)} items for listicle")
        body_str = "\n\n".join(
            f"{idx + 1}. {entry['title']}\n{entry['body']}"
            for idx, entry in enumerate(post_items)
        )
        
        self.callback("[PostWriter._get_roundup_post] Generating title, intro, and conclusion with AI...")
        title, intro, conclusion = self._generate_title_intro_conclusion_with_ai(body_str)

        self.callback("[PostWriter._get_roundup_post] Formatting listicle with WPFormatter...")
        formatted_body = WPFormatter().generate_listicle(intro, conclusion, post_items)
        self.callback(f"[PostWriter._get_roundup_post] Listicle formatted ({len(formatted_body)} chars)")

        return title, formatted_body

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
                "title": {
                    "type": "string",
                    "description": "Catchy and SEO-friendly blog post title"
                },
                "intro": {
                    "type": "string",
                    "description": "50-word introduction paragraph"
                },
                "conclusion": {
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
            title = data.get("title", "")
            intro = self._split_into_paragraphs(data.get("intro", ""))
            conclusion = self._split_into_paragraphs(data.get("conclusion", ""))
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

    def _get_single_post_body_prompts(self, prompt_config: AIPromptConfig):
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
        return self.post_type == POST_POST_TYPE_SINGLE_VAL
    
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
    