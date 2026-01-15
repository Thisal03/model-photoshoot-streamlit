from typing import Dict, Any, List

def map_platform_preset_to_aspect_ratio(platform_preset: str) -> str:
    """Map platform preset to Gemini aspect ratio"""
    mapping = {
        "instagram_portrait": "4:5",
        "instagram_story": "9:16",
        "instagram_square": "1:1",
        "default": "2:3"
    }
    return mapping.get(platform_preset, mapping["default"])


def build_model_reference_prompt(model_ref: Dict[str, Any], image_mapping: Dict[str, str] = None) -> List[str]:
    """Build prompt parts for model reference"""
    parts = []
    image_mapping = image_mapping or {}
    
    # Handle text description
    if model_ref.get("text_description"):
        parts.append(f"Model appearance: {model_ref['text_description']}.")
    
    # Handle face action
    face_action = model_ref.get("face_action", "keep")
    if face_action == "keep":
        if model_ref.get("image_url") and "model_ref" in image_mapping:
            parts.append(f"CRITICAL: Extract and use the EXACT same face from {image_mapping['model_ref']}. The face features (eyes, nose, mouth, facial structure, skin tone, facial proportions) must match exactly. Also extract the body figure and proportions from {image_mapping['model_ref']}. IGNORE the background, clothing, outfit, accessories, and any other elements from the model reference image.")
        else:
            parts.append("CRITICAL: Extract and use the EXACT same face from the model reference image. The face features must match exactly. Also extract the body figure and proportions. IGNORE the background, clothing, outfit, accessories, and any other elements.")
    elif face_action == "generate":
        if model_ref.get("new_model_description"):
            parts.append(f"Generate a new model with the following characteristics: {model_ref['new_model_description']}.")
        else:
            parts.append("Generate a new model face.")
    
    # Always add instruction to use only model face and figure from model reference
    if model_ref.get("image_url") and face_action == "keep":
        parts.append("IMPORTANT: The model reference image should ONLY be used to extract the face and body figure. Do not use any other elements from that image.")
    
    return parts


def build_outfit_prompt(outfit: Dict[str, Any], image_mapping: Dict[str, str] = None) -> List[str]:
    """Build prompt parts for base outfit"""
    parts = []
    image_mapping = image_mapping or {}
    
    # Clothing instruction - IMPORTANT: Outfit image REPLACES model's clothing
    if outfit.get("image_url"):
        outfit_ref = image_mapping.get("outfit", "the outfit reference image")
        parts.append(f"CRITICAL REQUIREMENT: Extract ONLY the clothing/outfit from {outfit_ref}. IGNORE any person, model, face, body, or background in {outfit_ref}. If there is a person wearing the outfit in {outfit_ref}, extract ONLY the clothing items (shirt, dress, pants, jacket, etc.) and completely ignore the person. REPLACE the model's clothing with ONLY the extracted outfit from {outfit_ref}. Maintain the clothing design, texture, color, and details from the extracted outfit.")
    elif outfit.get("text_description"):
        parts.append("Apply the following outfit as described.")
    
    # Text description
    if outfit.get("text_description"):
        parts.append(f"Outfit: {outfit['text_description']}.")
    
    return parts


def build_additional_items_prompt(items: List[Dict[str, Any]], image_mapping: Dict[str, str] = None) -> List[str]:
    """Build prompt parts for additional clothing items"""
    parts = []
    image_mapping = image_mapping or {}
    
    if not items:
        return parts
    
    item_descriptions = []
    for idx, item in enumerate(items):
        item_type = item.get("type", "item")
        
        if item.get("text"):
            item_descriptions.append(f"{item_type}: {item['text']}")
        elif item.get("image_url"):
            item_ref = image_mapping.get(f"item_{idx}", f"the {item_type} reference image")
            item_descriptions.append(f"{item_type}: extract ONLY the {item_type} from {item_ref}, ignore any person/background/other elements")
    
    if item_descriptions:
        parts.append(f"Additional items: {'; '.join(item_descriptions)}.")
    
    return parts


def build_jewelry_prompt(jewelry: Dict[str, Any], image_mapping: Dict[str, str] = None) -> List[str]:
    """Build prompt parts for jewelry configuration"""
    parts = []
    jewelry_items = []
    image_mapping = image_mapping or {}
    
    # Neck jewelry
    neck = jewelry.get("neck", {})
    if neck.get("enabled"):
        method = neck.get("method", "none")
        if method == "text_description" and neck.get("text"):
            jewelry_items.append(f"neck: {neck['text']}")
        elif method == "image_reference":
            neck_ref = image_mapping.get("jewelry_neck", "the neck jewelry reference image")
            jewelry_items.append(f"neck: extract ONLY the jewelry from {neck_ref}, ignore any person/background/other elements, apply to neck area")
        elif method == "text_and_image" and neck.get("text"):
            neck_ref = image_mapping.get("jewelry_neck", "the neck jewelry reference image")
            jewelry_items.append(f"neck: {neck['text']} (extract jewelry from {neck_ref}, ignore person/background)")
    
    # Ear jewelry
    ears = jewelry.get("ears", {})
    if ears.get("enabled"):
        method = ears.get("method", "none")
        if method == "text_description" and ears.get("text"):
            jewelry_items.append(f"ears: {ears['text']}")
        elif method == "image_reference":
            ears_ref = image_mapping.get("jewelry_ears", "the ear jewelry reference image")
            jewelry_items.append(f"ears: extract ONLY the jewelry from {ears_ref}, ignore any person/background/other elements, apply to ears")
        elif method == "text_and_image" and ears.get("text"):
            ears_ref = image_mapping.get("jewelry_ears", "the ear jewelry reference image")
            jewelry_items.append(f"ears: {ears['text']} (extract jewelry from {ears_ref}, ignore person/background)")
    
    # Hands/wrists jewelry
    hands = jewelry.get("hands_wrists", {})
    if hands.get("enabled"):
        method = hands.get("method", "none")
        if method == "text_description" and hands.get("text"):
            jewelry_items.append(f"hands/wrists: {hands['text']}")
        elif method == "image_reference":
            hands_ref = image_mapping.get("jewelry_hands", "the hand/wrist jewelry reference image")
            jewelry_items.append(f"hands/wrists: extract ONLY the jewelry from {hands_ref}, ignore any person/background/other elements, apply to hands and wrists")
        elif method == "text_and_image" and hands.get("text"):
            hands_ref = image_mapping.get("jewelry_hands", "the hand/wrist jewelry reference image")
            jewelry_items.append(f"hands/wrists: {hands['text']} (extract jewelry from {hands_ref}, ignore person/background)")
    
    if jewelry_items:
        parts.append(f"Jewelry and accessories: {', '.join(jewelry_items)}.")
    
    return parts


def build_environment_prompt(environment: Dict[str, Any], image_mapping: Dict[str, str] = None) -> List[str]:
    """Build prompt parts for environment/background"""
    parts = []
    image_mapping = image_mapping or {}
    
    # Category
    category = environment.get("category", "studio")
    category_descriptions = {
        "studio": "professional studio setting",
        "indoor_lifestyle": "indoor lifestyle environment",
        "outdoor_urban": "outdoor urban environment",
        "outdoor_nature": "outdoor natural environment"
    }
    parts.append(f"Environment: {category_descriptions.get(category, category)}.")
    
    # Method-specific description
    method = environment.get("method", "auto")
    if method == "text_description" and environment.get("text_description"):
        parts.append(f"Background details: {environment['text_description']}.")
    elif method == "reference_image" and environment.get("image_url"):
        env_ref = image_mapping.get("environment", "the background/environment reference image")
        parts.append(f"CRITICAL: Extract ONLY the background/environment/scene from {env_ref}. IGNORE any person, model, face, body, clothing, or foreground elements. Use ONLY the background, environment setting, and scene from {env_ref}.")
    
    return parts


def build_photography_prompt(photography: Dict[str, Any], image_mapping: Dict[str, str] = None) -> List[str]:
    """Build prompt parts for photography settings"""
    parts = []
    image_mapping = image_mapping or {}
    
    # Main photography settings
    photo_settings = []
    
    if photography.get("aesthetic"):
        photo_settings.append(f"aesthetic: {photography['aesthetic']}")
    
    if photography.get("framing"):
        framing_desc = photography['framing'].replace("_", " ")
        photo_settings.append(f"framing: {framing_desc}")
    
    if photography.get("lighting"):
        lighting_desc = photography['lighting'].replace("_", " ")
        photo_settings.append(f"lighting: {lighting_desc}")
    
    if photo_settings:
        parts.append(f"Photography style: {', '.join(photo_settings)}.")
    
    # Shadows
    shadows = photography.get("shadows", "").strip()
    if shadows and shadows != "None - No specific shadow requirements":
        # If it's a dropdown option, clean it up
        if shadows.startswith("None - "):
            shadow_desc = shadows.replace("None - ", "")
        else:
            shadow_desc = shadows
        parts.append(f"Shadows: {shadow_desc}.")
    
    # Pose
    pose = photography.get("pose", {})
    pose_method = pose.get("method", "auto")
    
    if pose_method == "text_description" and pose.get("text"):
        parts.append(f"Pose: {pose['text']}.")
    elif pose_method == "reference_image" and pose.get("image_url"):
        strength = pose.get("strength", 0.8)
        pose_ref = image_mapping.get("pose", "the pose reference image")
        parts.append(f"CRITICAL: Extract ONLY the body pose, positioning, and stance from {pose_ref}. IGNORE the face, clothing, outfit, background, and other elements. Use ONLY the body positioning and pose from {pose_ref} with {int(strength * 100)}% similarity.")
    
    # Hair
    hair = photography.get("hair", {})
    hair_method = hair.get("method", "auto")
    
    if hair_method == "text_description" and hair.get("text"):
        parts.append(f"Hair styling: {hair['text']}.")
    elif hair_method == "reference_image" and hair.get("image_url"):
        hair_ref = image_mapping.get("hair", "the hairstyle reference image")
        parts.append(f"CRITICAL: Extract ONLY the hairstyle, hair texture, and hair styling from {hair_ref}. IGNORE the face features, body, clothing, background, and other elements. Use ONLY the hairstyle and hair appearance from {hair_ref}.")
    elif hair_method == "keep_original":
        parts.append("Keep the original hairstyle from the reference.")
    
    return parts


def build_quality_boost() -> str:
    """Return quality enhancement prompt"""
    return (
        "realistic head to body ratio, ultra-detailed, highly realistic, "
        "professional photography, 8k uhd, cinematic lighting, soft natural light, "
        "sharp focus, perfect skin texture, lifelike eyes, accurate facial proportions, "
        "volumetric depth, subtle shadows, realistic skin tones, detailed hair strands, "
        "fine pores, depth of field, masterpiece, award-winning portrait style"
    )


def build_photoshoot_prompt(config: Dict[str, Any], image_mapping: Dict[str, str] = None) -> str:
    """Build comprehensive prompt from the new structured JSON config
    
    Args:
        config: Configuration dictionary
        image_mapping: Dictionary mapping image labels to descriptions (from prepare_image_parts)
    """
    parts = []
    image_mapping = image_mapping or {}
    
    # Check if batch generation (multiple outputs)
    output_count = config.get("output", {}).get("count", 1)
    if output_count > 1:
        parts.append("CRITICAL CONSISTENCY REQUIREMENT: When generating multiple images, the model's face, body figure, outfit, all clothing items, jewelry, and accessories must remain EXACTLY THE SAME across all generated images. Only camera angles, poses, lighting variations, and composition can differ between images. All core elements must be identical.")
    
    # Model reference
    if config.get("model_reference"):
        parts.extend(build_model_reference_prompt(config["model_reference"], image_mapping))
    
    # Base outfit
    if config.get("base_outfit"):
        parts.extend(build_outfit_prompt(config["base_outfit"], image_mapping))
    
    # Additional items (layered clothing)
    if config.get("additional_items"):
        parts.extend(build_additional_items_prompt(config["additional_items"], image_mapping))
    
    # Jewelry
    if config.get("jewelry"):
        parts.extend(build_jewelry_prompt(config["jewelry"], image_mapping))
    
    # Environment
    if config.get("environment"):
        parts.extend(build_environment_prompt(config["environment"], image_mapping))
    
    # Photography settings
    if config.get("photography"):
        parts.extend(build_photography_prompt(config["photography"], image_mapping))
    
    # Quality boost
    parts.append(build_quality_boost())
    
    return " ".join(parts)


# Legacy support - handle old config format
def build_photoshoot_prompt_legacy(config: Dict[str, Any]) -> str:
    """Build prompt from old config structure (for backward compatibility)"""
    parts = []
    
    # CRITICAL: Clothing preservation instructions
    if config.get("subject", {}).get("clothing_lock"):
        clothing_lock = config["subject"]["clothing_lock"]
        clothing_instruction = "CRITICAL REQUIREMENT: You must preserve the exact clothing from the primary reference image. "
        
        if clothing_lock.get("validation_description"):
            clothing_instruction += f"The clothing consists of: {clothing_lock['validation_description']}. "
        
        if clothing_lock.get("garments_to_preserve") and len(clothing_lock["garments_to_preserve"]) > 0:
            garments = ", ".join(clothing_lock["garments_to_preserve"])
            clothing_instruction += f"Specifically preserve these garments: {garments}. "
        
        preservation_level = clothing_lock.get("preservation_level", "strict")
        if preservation_level == "strict":
            clothing_instruction += "Maintain exact texture, wrinkles, and details. "
        elif preservation_level == "relaxed":
            clothing_instruction += "Preserve the clothing design but allow natural lighting integration. "
        
        parts.append(clothing_instruction)
    
    # Model identity
    if config.get("subject", {}).get("model_identity"):
        model_identity = config["subject"]["model_identity"]
        method = model_identity.get("method")
        
        if method == "keep_reference_face":
            parts.append("Keep the model's face from the primary reference image exactly as shown.")
        elif method == "generate_new" and model_identity.get("new_model_description"):
            desc = model_identity["new_model_description"]
            desc_parts = []
            if desc.get("ethnicity"):
                desc_parts.append(f"ethnicity: {desc['ethnicity']}")
            if desc.get("hair_color"):
                desc_parts.append(f"hair color: {desc['hair_color']}")
            if desc.get("age_vibe"):
                desc_parts.append(f"age: {desc['age_vibe']}")
            if desc_parts:
                parts.append(f"Generate a new model with the following characteristics: {', '.join(desc_parts)}.")
    
    # Pose
    if config.get("subject", {}).get("pose"):
        pose = config["subject"]["pose"]
        pose_method = pose.get("method")
        
        if pose_method == "text_description" and pose.get("text_prompt"):
            parts.append(f"Pose: {pose['text_prompt']}.")
        elif pose_method == "reference_image":
            strength = pose.get("mimicry_strength", 0.8)
            parts.append(f"Use the pose from the reference image with {int(strength * 100)}% similarity.")
    
    # Styling - Hair
    if config.get("subject", {}).get("styling", {}).get("hair"):
        hair = config["subject"]["styling"]["hair"]
        hair_method = hair.get("method")
        
        if hair_method == "text_description" and hair.get("text_prompt"):
            parts.append(f"Hair styling: {hair['text_prompt']}.")
        elif hair_method == "reference_image":
            parts.append("Use the hairstyle from the reference image.")
        elif hair_method == "none":
            parts.append("No hair styling changes needed.")
    
    # Styling - Jewelry and Accessories
    if config.get("subject", {}).get("styling", {}).get("jewelry_and_accessories"):
        jewelry = config["subject"]["styling"]["jewelry_and_accessories"]
        jewelry_parts = []
        
        if jewelry.get("neck"):
            neck = jewelry["neck"]
            if neck.get("method") == "text_description" and neck.get("text_prompt"):
                jewelry_parts.append(f"neck: {neck['text_prompt']}")
            elif neck.get("method") == "reference_image":
                jewelry_parts.append("neck: use reference image")
            elif neck.get("method") == "none":
                jewelry_parts.append("neck: remove all jewelry")
        
        if jewelry.get("ears"):
            ears = jewelry["ears"]
            if ears.get("method") == "text_description" and ears.get("text_prompt"):
                jewelry_parts.append(f"ears: {ears['text_prompt']}")
            elif ears.get("method") == "reference_image":
                jewelry_parts.append("ears: use reference image")
            elif ears.get("method") == "none":
                jewelry_parts.append("ears: remove all jewelry")
        
        if jewelry.get("hands_wrists"):
            hands = jewelry["hands_wrists"]
            if hands.get("method") == "text_description" and hands.get("text_prompt"):
                jewelry_parts.append(f"hands/wrists: {hands['text_prompt']}")
            elif hands.get("method") == "reference_image" and hands.get("use_auxiliary_ref"):
                jewelry_parts.append("hands/wrists: use reference image")
            elif hands.get("method") == "none":
                jewelry_parts.append("hands/wrists: remove all accessories")
        
        if jewelry_parts:
            parts.append(f"Jewelry and accessories: {', '.join(jewelry_parts)}.")
    
    # Environment
    if config.get("environment"):
        env = config["environment"]
        if env.get("category"):
            parts.append(f"Environment category: {env['category']}.")
        
        if env.get("details"):
            details = env["details"]
            if details.get("method") == "text_description" and details.get("text_prompt"):
                parts.append(f"Background: {details['text_prompt']}.")
            elif details.get("method") == "reference_image" and details.get("use_auxiliary_ref"):
                parts.append("Use the background from the reference image.")
    
    # Photography direction
    if config.get("photography_direction"):
        photo = config["photography_direction"]
        photo_parts = []
        
        if photo.get("aesthetic_preset"):
            photo_parts.append(f"aesthetic: {photo['aesthetic_preset']}")
        if photo.get("framing"):
            photo_parts.append(f"framing: {photo['framing']}")
        if photo.get("lighting_mood"):
            photo_parts.append(f"lighting: {photo['lighting_mood']}")
        
        if photo_parts:
            parts.append(f"Photography style: {', '.join(photo_parts)}.")
    
    # Quality boost
    parts.append(build_quality_boost())
    
    return " ".join(parts)
