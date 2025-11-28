"""
Post Part Constants - Shared constants for post part names and WP heading mappings
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PostPartConfig:
    """Configuration for a post part including its WordPress heading."""
    field_name: str
    wp_heading: Optional[str] = None  # None means no heading for this part
    
    
class PostParts:
    """Post part field names and their WordPress heading mappings."""
    
    # Fields without headings
    TITLE = PostPartConfig("title", None)
    BODY = PostPartConfig("body", None)
    INTRO = PostPartConfig("intro", None)
    
    # Recipe fields with headings
    EQUIPMENT_MUST = PostPartConfig("equipment_must_haves", "Equipment: Must-haves")
    EQUIPMENT_NICE = PostPartConfig("equipment_nice_to_haves", "Equipment: Nice-to-haves")
    INGREDIENTS = PostPartConfig("ingredients", "Ingredients")
    INSTRUCTIONS = PostPartConfig("instructions", "Instructions")
    GOOD_TO_KNOW = PostPartConfig("good_to_know", "Good to Know")
    
    # Listicle/Roundup fields
    CONCLUSION = PostPartConfig("conclusion", "Conclusion")
    ITEMS = PostPartConfig("items", None)  # Items have individual numbered headings


# Legacy constants for backward compatibility
POST_PART_TITLE = PostParts.TITLE.field_name
POST_PART_BODY = PostParts.BODY.field_name
POST_PART_INTRO = PostParts.INTRO.field_name
POST_PART_CONCLUSION = PostParts.CONCLUSION.field_name
POST_PART_EQUIPMENT_MUST = PostParts.EQUIPMENT_MUST.field_name
POST_PART_EQUIPMENT_NICE = PostParts.EQUIPMENT_NICE.field_name
POST_PART_INGREDIENTS = PostParts.INGREDIENTS.field_name
POST_PART_INSTRUCTIONS = PostParts.INSTRUCTIONS.field_name
POST_PART_GOOD_TO_KNOW = PostParts.GOOD_TO_KNOW.field_name
POST_PART_ITEMS = PostParts.ITEMS.field_name

