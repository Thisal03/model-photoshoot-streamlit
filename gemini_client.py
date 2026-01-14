import os
import requests
import base64
from typing import List, Dict, Any, Optional, Tuple
from image_utils import url_to_base64
from prompt_builder import map_platform_preset_to_aspect_ratio


class GeminiPhotoshootClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent"
    
    def _add_image_part(self, parts: List[Dict], image_url: str) -> None:
        """Helper to add an image part from URL"""
        if image_url:
            try:
                base64_data = url_to_base64(image_url)
                parts.append({
                    "inlineData": {
                        "mimeType": "image/jpeg",
                        "data": base64_data
                    }
                })
            except Exception as e:
                print(f"Warning: Failed to load image from {image_url}: {e}")
    
    def prepare_image_parts(self, config: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
        """
        Prepare image parts for Gemini API from URLs in the new config structure.
        Collects images from all sections with explicit labels.
        
        Returns:
            Tuple of (image_parts_list, image_mapping_dict)
            image_mapping_dict maps image labels to their descriptions for prompt building
        """
        parts = []
        image_mapping = {}  # Maps image label to description
        
        # Model reference image
        model_ref = config.get("model_reference", {})
        if model_ref.get("image_url"):
            parts.append({"text": "REFERENCE IMAGE 1 - MODEL: This image shows the model reference. Use the model's face and appearance from this image."})
            self._add_image_part(parts, model_ref["image_url"])
            image_mapping["model_ref"] = "the model reference image (Image 1)"
        
        # Base outfit image - IMPORTANT: This replaces the model's outfit
        outfit = config.get("base_outfit", {})
        if outfit.get("image_url"):
            parts.append({"text": "REFERENCE IMAGE - OUTFIT: This image shows the outfit/clothing to be worn. REPLACE the model's clothing with the outfit from this image."})
            self._add_image_part(parts, outfit["image_url"])
            image_mapping["outfit"] = "the outfit image (which replaces the model's clothing)"
        
        # Additional items images
        additional_items = config.get("additional_items", [])
        item_counter = 0
        for idx, item in enumerate(additional_items):
            if item.get("image_url"):
                item_type = item.get("type", "item")
                item_counter += 1
                parts.append({"text": f"REFERENCE IMAGE - ADDITIONAL ITEM ({item_type.upper()}): This image shows a {item_type} to add to the outfit."})
                self._add_image_part(parts, item["image_url"])
                image_mapping[f"item_{idx}"] = f"the {item_type} reference image"
        
        # Jewelry images - each with explicit location mapping
        jewelry = config.get("jewelry", {})
        
        # Neck jewelry
        neck = jewelry.get("neck", {})
        if neck.get("enabled") and neck.get("image_url"):
            parts.append({"text": "REFERENCE IMAGE - NECK JEWELRY: This image shows the necklace/jewelry to wear around the neck. Apply this jewelry to the neck area."})
            self._add_image_part(parts, neck["image_url"])
            image_mapping["jewelry_neck"] = "the neck jewelry reference image"
        
        # Ear jewelry
        ears = jewelry.get("ears", {})
        if ears.get("enabled") and ears.get("image_url"):
            parts.append({"text": "REFERENCE IMAGE - EAR JEWELRY: This image shows the earrings/jewelry to wear on the ears. Apply this jewelry to the ears."})
            self._add_image_part(parts, ears["image_url"])
            image_mapping["jewelry_ears"] = "the ear jewelry reference image"
        
        # Hands/wrists jewelry
        hands = jewelry.get("hands_wrists", {})
        if hands.get("enabled") and hands.get("image_url"):
            parts.append({"text": "REFERENCE IMAGE - HAND/WRIST JEWELRY: This image shows the rings/bracelets to wear on hands and wrists. Apply this jewelry to the hands and wrists."})
            self._add_image_part(parts, hands["image_url"])
            image_mapping["jewelry_hands"] = "the hand/wrist jewelry reference image"
        
        # Environment/background image
        environment = config.get("environment", {})
        if environment.get("image_url"):
            parts.append({"text": "REFERENCE IMAGE - BACKGROUND: This image shows the background/environment to use for the photoshoot."})
            self._add_image_part(parts, environment["image_url"])
            image_mapping["environment"] = "the background/environment reference image"
        
        # Photography references
        photography = config.get("photography", {})
        
        # Pose reference image
        pose = photography.get("pose", {})
        if pose.get("image_url"):
            parts.append({"text": "REFERENCE IMAGE - POSE: This image shows the pose to mimic. Use the pose and body positioning from this image."})
            self._add_image_part(parts, pose["image_url"])
            image_mapping["pose"] = "the pose reference image"
        
        # Hair reference image
        hair = photography.get("hair", {})
        if hair.get("image_url"):
            parts.append({"text": "REFERENCE IMAGE - HAIRSTYLE: This image shows the hairstyle to apply. Use the hairstyle from this image."})
            self._add_image_part(parts, hair["image_url"])
            image_mapping["hair"] = "the hairstyle reference image"
        
        return parts, image_mapping
    
    def prepare_image_parts_legacy(self, config: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
        """
        Prepare image parts from old config structure (backward compatibility).
        Returns same format as prepare_image_parts for consistency.
        """
        parts = []
        image_mapping = {}
        
        # Primary clothing reference (required)
        primary_ref = config.get("input_assets", {}).get("primary_clothing_reference", {})
        primary_url = primary_ref.get("url")
        
        if primary_url:
            parts.append({"text": "REFERENCE IMAGE - PRIMARY CLOTHING: This is the main clothing reference image."})
            self._add_image_part(parts, primary_url)
            image_mapping["primary_clothing"] = "the primary clothing reference image"
        
        # Auxiliary references
        aux_refs = config.get("input_assets", {}).get("auxiliary_references", {})
        
        # Pose reference
        if aux_refs.get("pose_ref_url"):
            parts.append({"text": "REFERENCE IMAGE - POSE: This image shows the pose to mimic."})
            self._add_image_part(parts, aux_refs["pose_ref_url"])
            image_mapping["pose"] = "the pose reference image"
        
        # Accessory reference
        if aux_refs.get("accessory_ref_url"):
            parts.append({"text": "REFERENCE IMAGE - ACCESSORY: This image shows an accessory to add."})
            self._add_image_part(parts, aux_refs["accessory_ref_url"])
            image_mapping["accessory"] = "the accessory reference image"
        
        # Background reference
        if aux_refs.get("background_ref_url"):
            parts.append({"text": "REFERENCE IMAGE - BACKGROUND: This image shows the background to use."})
            self._add_image_part(parts, aux_refs["background_ref_url"])
            image_mapping["background"] = "the background reference image"
        
        return parts, image_mapping
    
    def generate_image(
        self,
        prompt: str,
        image_parts: List[Dict[str, Any]],
        aspect_ratio: str,
        batch_index: Optional[int] = None,
        batch_variety: Optional[str] = None
    ) -> Tuple[bytes, str]:
        """
        Generate image using Gemini API
        
        Args:
            prompt: The text prompt for image generation
            image_parts: List of image parts (from prepare_image_parts) - now includes descriptive text before each image
            aspect_ratio: Target aspect ratio (e.g., "4:5", "9:16")
            batch_index: Index for batch generation (for variations)
            batch_variety: Type of variety ("subtle_variations" or "dynamic_angles")
        
        Returns:
            Tuple of (image_bytes, mime_type)
        """
        
        # Add variation for batch generation
        final_prompt = prompt
        if batch_index is not None and batch_variety == "dynamic_angles":
            variations = [
                "Slightly different camera angle",
                "Different pose variation",
                "Alternative composition",
                "Varied perspective",
                "Different lighting angle",
                "Alternative framing",
                "Shifted viewpoint",
                "New angle approach",
                "Fresh perspective",
                "Different positioning"
            ]
            variation_text = variations[batch_index % len(variations)]
            final_prompt = f"{variation_text}. {prompt}"
        elif batch_index is not None and batch_variety == "subtle_variations":
            # Subtle variations - minor changes
            variations = [
                "Slight variation in expression",
                "Minor pose adjustment",
                "Subtle lighting change",
                "Small composition shift",
                "Gentle variation"
            ]
            variation_text = variations[batch_index % len(variations)]
            final_prompt = f"{variation_text}. {prompt}"
        
        # Build request parts: text prompt first, then interleaved text+image parts
        parts = [{"text": final_prompt}] + image_parts
        
        request_body = {
            "contents": [{
                "role": "user",
                "parts": parts
            }],
            "generationConfig": {
                "responseModalities": ["IMAGE"],
                "imageConfig": {
                    "aspectRatio": aspect_ratio
                }
            }
        }
        
        # Call Gemini API
        response = requests.post(
            self.base_url,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key
            },
            json=request_body,
            timeout=300
        )
        
        response.raise_for_status()
        response_data = response.json()
        
        # Extract image from response
        if not response_data.get("candidates") or not response_data["candidates"][0]:
            raise ValueError("Invalid response format: no candidates found")
        
        candidate = response_data["candidates"][0]
        if not candidate.get("content") or not candidate["content"].get("parts"):
            raise ValueError("Invalid response format: no content parts found")
        
        # Find image part
        image_part = None
        for part in candidate["content"]["parts"]:
            if part.get("inlineData") and part["inlineData"].get("mimeType", "").startswith("image/"):
                image_part = part
                break
        
        if not image_part or not image_part.get("inlineData") or not image_part["inlineData"].get("data"):
            raise ValueError("No image data found in Gemini response")
        
        # Decode base64 image
        base64_data = image_part["inlineData"]["data"]
        mime_type = image_part["inlineData"]["mimeType"]
        image_bytes = base64.b64decode(base64_data)
        
        return image_bytes, mime_type
