import streamlit as st
import os
from dotenv import load_dotenv
from datetime import datetime
import uuid
from PIL import Image
import io

from gemini_client import GeminiPhotoshootClient
from prompt_builder import build_photoshoot_prompt, map_platform_preset_to_aspect_ratio
from image_utils import S3ImageHandler

load_dotenv()

# Page config
st.set_page_config(
    page_title="Photoshoot Generator",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for professional tabbed styling
st.markdown("""
<style>
    /* Main container styling - minimal padding */
    .main .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
        max-width: 100%;
    }
    
    /* Remove footer but keep header and menu for deploy button */
    footer {visibility: hidden; height: 0 !important; margin: 0 !important; padding: 0 !important;}
    
    /* Remove Streamlit default top padding */
    .main {
        padding-top: 0rem !important;
    }
    
    /* Remove spacing from app viewport */
    .appview-container {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
    }
    
    /* Tab container - justify tabs evenly */
    .stTabs [data-baseweb="tab-list"] {
        display: flex;
        justify-content: space-between;
        gap: 4px;
        background-color: #f0f2f6;
        padding: 6px;
        border-radius: 8px;
        margin-top: 0.25rem;
        margin-bottom: 0.5rem;
        width: 100%;
    }
    
    /* Individual tabs - flex to fill space evenly */
    .stTabs [data-baseweb="tab-list"] button {
        flex: 1;
        min-width: 0;
        height: 48px;
        padding: 10px 12px;
        background-color: white;
        border-radius: 6px;
        font-weight: 500;
        color: #666;
        border: 1px solid #e0e0e0;
        transition: all 0.3s ease;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #f8f9fa;
        color: #333;
    }
    
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        background-color: #ff4b4b;
        color: white;
        border-color: #ff4b4b;
        font-weight: 600;
    }
    
    /* Status badges in tabs */
    .tab-badge {
        display: inline-block;
        margin-left: 6px;
        padding: 2px 6px;
        border-radius: 10px;
        font-size: 0.7rem;
        font-weight: 600;
    }
    
    .badge-required {
        color: #ff4b4b;
    }
    
    .badge-done {
        background-color: #00d26a;
        color: white;
    }
    
    /* Image preview container */
    .image-preview {
        border: 2px dashed #0f3460;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
        min-height: 150px;
    }
    
    /* Section header */
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        margin-bottom: 1rem;
        color: #e94560;
    }
    
    /* Generate button styling - minimal padding */
    .generate-section {
        position: sticky;
        bottom: 0;
        background: white;
        padding: 0.5rem;
        border-top: 2px solid #e0e0e0;
        margin-top: 0.5rem;
        margin-bottom: 0rem;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
    }
    
    /* Remove bottom spacing from last elements */
    .main .block-container > div:last-child {
        margin-bottom: 0rem !important;
        padding-bottom: 0rem !important;
    }
    
    /* Reduce spacing in Streamlit elements */
    .element-container {
        margin-bottom: 0.5rem;
    }
    
    /* Reduce title spacing - minimal */
    h1 {
        margin-bottom: 0.25rem !important;
        margin-top: 0.25rem !important;
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
    }
    
    /* Reduce caption spacing */
    .stCaption {
        margin-bottom: 0.25rem !important;
        margin-top: 0rem !important;
    }
    
    /* Reduce spacing between title and tabs */
    div[data-testid="stVerticalBlock"] > div:first-child {
        margin-bottom: 0.25rem !important;
        margin-top: 0rem !important;
    }
    
    /* Remove extra spacing from Streamlit blocks */
    section[data-testid="stAppViewContainer"] {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
    }
    
    /* Reduce spacing in all vertical blocks */
    div[data-testid="stVerticalBlock"] {
        gap: 0.25rem;
    }
    
    /* Disable typing in selectboxes - make them selection-only */
    div[data-baseweb="select"] input,
    div[data-baseweb="select"] input[type="text"],
    .stSelectbox input,
    .stSelectbox input[type="text"] {
        pointer-events: none;
        cursor: pointer;
        user-select: none;
        -webkit-user-select: none;
        -moz-user-select: none;
        -ms-user-select: none;
    }
    
    /* Ensure selectbox container is clickable but input is not */
    div[data-baseweb="select"] {
        cursor: pointer;
    }
    
    div[data-baseweb="select"] input:focus {
        outline: none;
    }
    
    /* Prevent text input in selectbox */
    div[data-baseweb="select"] input[readonly] {
        background-color: transparent;
    }
</style>
""", unsafe_allow_html=True)

# Initialize clients
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    st.error("GEMINI_API_KEY not found in .env file!")
    st.stop()

client = GeminiPhotoshootClient(GEMINI_API_KEY)
s3_handler = S3ImageHandler()

# Initialize session state for configuration
if 'additional_items' not in st.session_state:
    st.session_state.additional_items = []

# Helper function for image upload with S3
def handle_image_upload(file_obj, image_type, session_key):
    """Handle image upload to S3 and store URL in session state"""
    if file_obj is not None:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(file_obj, width=150)
        with col2:
            if st.button(f"Upload", key=f"upload_{session_key}"):
                with st.spinner("Uploading..."):
                    image_bytes = file_obj.read()
                    result = s3_handler.upload_reference_image(
                        image_bytes,
                        file_obj.name,
                        image_type
                    )
                    if result['success']:
                        st.session_state[f"{session_key}_url"] = result['public_url']
                        st.success("Uploaded successfully")
                        st.rerun()
                    else:
                        st.error(f"Upload failed: {result.get('error')}")
        
        # Show uploaded URL if exists
        if st.session_state.get(f"{session_key}_url"):
            st.caption(f"Uploaded: {st.session_state[f'{session_key}_url'][:50]}...")

def render_input_section(section_key, label, show_preservation=False):
    """Render input section with text description and image upload options"""
    
    # Text description - always shown
    text_value = st.text_area(
        f"{label} Description (Optional)",
        key=f"{section_key}_text",
        height=100,
        placeholder=f"Describe the {label.lower()} in detail..."
    )
    
    # Image upload - always shown
    uploaded_file = st.file_uploader(
        f"Upload {label} Image (Optional)",
        type=['jpg', 'jpeg', 'png'],
        key=f"{section_key}_file"
    )
    if uploaded_file:
        handle_image_upload(uploaded_file, section_key, section_key)
    
    if show_preservation:
        st.divider()
        preservation = st.selectbox(
            "Preservation Level",
            ["Strict - Exact match", "Relaxed - Allow lighting variations"],
            key=f"{section_key}_preservation"
        )
        return {
            "text": text_value,
            "image_url": st.session_state.get(f"{section_key}_url", ""),
            "preservation": "strict" if "Strict" in preservation else "relaxed"
        }
    
    return {
        "text": text_value,
        "image_url": st.session_state.get(f"{section_key}_url", "")
    }

def get_section_status(section_key):
    """Check if a section has been configured"""
    has_text = bool(st.session_state.get(f"{section_key}_text", ""))
    has_url = bool(st.session_state.get(f"{section_key}_url", ""))
    return has_text or has_url

def get_tab_label(name, section_key, is_required=False):
    """Get tab label with status indicator"""
    status = get_section_status(section_key)
    if status:
        return f"{name} ✓"
    elif is_required:
        return f"{name} *"
    return name

def determine_method(text, image_url, default="auto"):
    """Auto-determine method based on what fields are filled"""
    has_text = bool(text and text.strip())
    has_image = bool(image_url and image_url.strip())
    
    if has_text and has_image:
        return "text_and_image"
    elif has_text:
        return "text_description"
    elif has_image:
        return "image_reference"
    else:
        return default

def build_config():
    """Build the configuration dictionary from all inputs"""
    
    # Platform preset mapping
    platform_map = {
        "Instagram Portrait (4:5)": "instagram_portrait",
        "Instagram Story (9:16)": "instagram_story",
        "Instagram Square (1:1)": "instagram_square",
        "Default (2:3)": "default"
    }
    
    # Framing mapping
    framing_map = {
        "Full Body": "full_body",
        "3/4 Body": "3/4_body",
        "Waist Up": "waist_up",
        "Close Up": "close_up"
    }
    
    # Lighting mapping
    lighting_map = {
        "Soft Warm": "soft_warm",
        "Studio Clean": "studio_clean",
        "Golden Hour": "golden_hour",
        "Hard Shadows": "hard_shadows",
        "Natural": "natural"
    }
    
    config = {
        "meta": {
            "job_id": f"job_{uuid.uuid4().hex[:8]}",
            "client_id": "photoshoot_app",
            "platform_preset": platform_map.get(
                st.session_state.get("platform_preset", "Instagram Portrait (4:5)"),
                "instagram_portrait"
            )
        },
        "model_reference": {
            "method": determine_method(
                st.session_state.get("model_ref_text", ""),
                st.session_state.get("model_ref_url", ""),
                "text_description"
            ),
            "text_description": st.session_state.get("model_ref_text", ""),
            "image_url": st.session_state.get("model_ref_url", ""),
            "face_action": "keep" if st.session_state.get("model_action") == "Keep from reference" else "generate",
            "ethnicity": st.session_state.get("model_ethnicity", ""),
            "hair_color": st.session_state.get("model_hair_color", ""),
            "age": st.session_state.get("model_age", "")
        },
        "base_outfit": {
            "method": determine_method(
                st.session_state.get("outfit_text", ""),
                st.session_state.get("outfit_url", ""),
                "text_description"
            ),
            "text_description": st.session_state.get("outfit_text", ""),
            "image_url": st.session_state.get("outfit_url", ""),
            "preservation_level": "strict" if "Strict" in st.session_state.get("outfit_preservation", "Strict") else "relaxed",
            "garments_to_preserve": st.session_state.get("selected_garments", [])
            },
        "additional_items": st.session_state.get("additional_items", []),
        "jewelry": {
            "neck": {
                "enabled": st.session_state.get("jewelry_neck_enabled", False),
                "method": determine_method(
                    st.session_state.get("jewelry_neck_text", ""),
                    st.session_state.get("jewelry_neck_url", ""),
                    "none"
                ),
                "text": st.session_state.get("jewelry_neck_text", ""),
                "image_url": st.session_state.get("jewelry_neck_url", "")
            },
            "ears": {
                "enabled": st.session_state.get("jewelry_ears_enabled", False),
                "method": determine_method(
                    st.session_state.get("jewelry_ears_text", ""),
                    st.session_state.get("jewelry_ears_url", ""),
                    "none"
                ),
                "text": st.session_state.get("jewelry_ears_text", ""),
                "image_url": st.session_state.get("jewelry_ears_url", "")
            },
            "hands_wrists": {
                "enabled": st.session_state.get("jewelry_hands_enabled", False),
                "method": determine_method(
                    st.session_state.get("jewelry_hands_text", ""),
                    st.session_state.get("jewelry_hands_url", ""),
                    "none"
                ),
                "text": st.session_state.get("jewelry_hands_text", ""),
                "image_url": st.session_state.get("jewelry_hands_url", "")
            }
        },
        "environment": {
            "category": st.session_state.get("env_category", "Studio").lower().replace(" ", "_"),
            "method": determine_method(
                st.session_state.get("environment_text", ""),
                st.session_state.get("environment_url", ""),
                "auto"
            ),
            "text_description": st.session_state.get("environment_text", ""),
            "image_url": st.session_state.get("environment_url", "")
        },
        "photography": {
            "aesthetic": st.session_state.get("photo_aesthetic", "Commercial").lower(),
            "framing": framing_map.get(st.session_state.get("photo_framing", "3/4 Body"), "3/4_body"),
            "lighting": lighting_map.get(st.session_state.get("photo_lighting", "Soft Warm"), "soft_warm"),
            "pose": {
                "method": determine_method(
                    st.session_state.get("pose_text", ""),
                    st.session_state.get("pose_url", ""),
                    "auto"
                ),
                "text": st.session_state.get("pose_text", ""),
                "image_url": st.session_state.get("pose_url", ""),
                "strength": st.session_state.get("pose_strength", 0.8)
        },
            "hair": {
                "method": determine_method(
                    st.session_state.get("hair_text", ""),
                    st.session_state.get("hair_url", ""),
                    "auto"
                ),
                "text": st.session_state.get("hair_text", ""),
                "image_url": st.session_state.get("hair_url", "")
            }
        },
        "output": {
            "count": st.session_state.get("image_count", 2),
            "batch_variety": "subtle_variations" if "Subtle" in st.session_state.get("batch_variety", "Subtle Variations") else "dynamic_angles"
        }
    }
    
    return config

# Main Header
st.title("Photoshoot Generator")
st.caption("AI-Powered Fashion Photography")

# Create tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    get_tab_label("Model", "model_ref", True),
    get_tab_label("Outfit", "outfit", True),
    get_tab_label("Accessories", "accessories", False),
    get_tab_label("Jewelry", "jewelry", False),
    get_tab_label("Environment", "environment", False),
    get_tab_label("Photography", "photo", True),
    get_tab_label("Output", "output", True)
])

# Model Reference Tab
with tab1:
    st.markdown("### Model Reference")
    st.caption("Define the model's appearance - face, body type, and characteristics")
    
    with st.container():
        model_data = render_input_section("model_ref", "Model")
        
        # Additional model options
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            model_action = st.radio(
                "Model Face",
                ["Keep from reference", "Generate new"],
                key="model_action",
                horizontal=True
            )
        
        if model_action == "Generate new":
            with col2:
                st.text_input("Ethnicity (optional)", key="model_ethnicity")
            col3, col4 = st.columns(2)
            with col3:
                st.text_input("Hair Color (optional)", key="model_hair_color")
            with col4:
                st.text_input("Age Range (optional)", key="model_age")

# Outfit Tab
with tab2:
    st.markdown("### Base Outfit")
    st.caption("Define the main clothing items to be preserved in the photoshoot")
    
    with st.container():
        outfit_data = render_input_section("outfit", "Outfit", show_preservation=True)
        
        st.divider()
        
        # Garment selection
        st.markdown("##### Garments to Preserve")
        garment_cols = st.columns(4)
        garments = ["top", "pants", "dress", "shirt", "jacket", "skirt", "shoes", "coat"]
        selected_garments = []
        
        for i, garment in enumerate(garments):
            with garment_cols[i % 4]:
                if st.checkbox(garment.capitalize(), key=f"garment_{garment}"):
                    selected_garments.append(garment)
        
        st.session_state['selected_garments'] = selected_garments

# Accessories Tab
with tab3:
    st.markdown("### Additional Items")
    st.caption("Add optional layers like jackets, shoes, bags, etc.")
    
    with st.container():
        # Display existing items
        if st.session_state.additional_items:
            st.markdown("##### Added Items")
            for i, item in enumerate(st.session_state.additional_items):
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.text(f"{item['type']}")
                with col2:
                    st.caption(item.get('text', '')[:30] + "..." if item.get('text') else "Image reference")
                with col3:
                    if st.button("Remove", key=f"remove_item_{i}"):
                        st.session_state.additional_items.pop(i)
                        st.rerun()
        
        st.divider()
        
        # Add new item
        st.markdown("##### Add New Item")
        col1, col2 = st.columns([1, 2])
        
        with col1:
            item_type = st.selectbox(
                "Item Type",
                ["Jacket", "Shoes", "Bag", "Hat", "Scarf", "Belt", "Sunglasses", "Watch", "Other"],
                key="new_item_type"
            )
        
        # Show all input options
        new_item_text = st.text_area(
            "Item Description (Optional)",
            key="new_item_text",
            height=80,
            placeholder=f"Describe the {item_type.lower()}..."
        )
        
        item_file = st.file_uploader(
            "Upload Item Image (Optional)",
            type=['jpg', 'jpeg', 'png'],
            key="new_item_file"
        )
        if item_file:
            handle_image_upload(item_file, "item", "new_item")
        
        new_item_url = st.session_state.get("new_item_url", "")
        
        if st.button("Add Item", type="secondary"):
            new_item = {
                "type": item_type.lower(),
                "text": new_item_text,
                "image_url": new_item_url
            }
            st.session_state.additional_items.append(new_item)
            st.success(f"Added {item_type}")
            st.rerun()

# Jewelry Tab
with tab4:
    st.markdown("### Jewelry & Accessories")
    st.caption("Configure jewelry for each body location")
    
    jewelry_locations = [
        ("Neck", "jewelry_neck", "Necklaces, chains, pendants"),
        ("Ears", "jewelry_ears", "Earrings, ear cuffs"),
        ("Hands/Wrists", "jewelry_hands", "Rings, bracelets, watches")
    ]
    
    for location_name, location_key, description in jewelry_locations:
        with st.expander(f"{location_name} - {description}", expanded=False):
            enable_key = f"{location_key}_enabled"
            
            col1, col2 = st.columns([1, 3])
            with col1:
                enabled = st.checkbox("Enable", key=enable_key, value=False)
            
            if enabled:
                # Show all input options
                st.text_input(
                    f"{location_name} Description (Optional)",
                    key=f"{location_key}_text",
                    placeholder=f"e.g., Gold chain necklace with pendant"
                )
                
                jewelry_file = st.file_uploader(
                    f"Upload {location_name} Reference (Optional)",
                    type=['jpg', 'jpeg', 'png'],
                    key=f"{location_key}_file"
                )
                if jewelry_file:
                    handle_image_upload(jewelry_file, location_key, location_key)

# Environment Tab
with tab5:
    st.markdown("### Environment & Background")
    st.caption("Set the scene for your photoshoot")
    
    with st.container():
        col1, col2 = st.columns(2)
        
        with col1:
            env_category = st.selectbox(
                "Environment Category",
                ["Studio", "Indoor Lifestyle", "Outdoor Urban", "Outdoor Nature"],
                key="env_category"
            )
        
        # Show all input options
        st.text_area(
            "Background Description (Optional)",
            key="environment_text",
            height=100,
            placeholder="Describe the background/environment in detail...\ne.g., Abstract curved peach and warm beige walls with soft shadows"
        )
        
        bg_file = st.file_uploader(
            "Upload Background Reference (Optional)",
            type=['jpg', 'jpeg', 'png'],
            key="environment_file"
        )
        if bg_file:
            handle_image_upload(bg_file, "background", "environment")

# Photography Tab
with tab6:
    st.markdown("### Photography Settings")
    st.caption("Configure the visual style and camera settings")
    
    with st.container():
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("##### Aesthetic")
            aesthetic = st.selectbox(
                "Style",
                ["Editorial", "Commercial", "Lifestyle", "High Fashion", "Casual"],
                key="photo_aesthetic",
                label_visibility="collapsed"
            )
        
        with col2:
            st.markdown("##### Framing")
            framing = st.selectbox(
                "Frame",
                ["Full Body", "3/4 Body", "Waist Up", "Close Up"],
                key="photo_framing",
                label_visibility="collapsed"
            )
        
        with col3:
            st.markdown("##### Lighting")
            lighting = st.selectbox(
                "Light",
                ["Soft Warm", "Studio Clean", "Golden Hour", "Hard Shadows", "Natural"],
                key="photo_lighting",
                label_visibility="collapsed"
            )
        
        st.divider()
        
        # Pose settings
        st.markdown("##### Pose")
        st.text_input(
            "Pose Description (Optional)",
            key="pose_text",
            placeholder="e.g., Walking motion, hands in pockets"
        )
        
        col1, col2 = st.columns([2, 1])
        with col1:
            pose_file = st.file_uploader(
                "Upload Pose Reference (Optional)",
                type=['jpg', 'jpeg', 'png'],
                key="pose_file"
            )
            if pose_file:
                handle_image_upload(pose_file, "pose", "pose")
        with col2:
            st.slider("Mimicry Strength", 0.0, 1.0, 0.8, key="pose_strength")
        
        st.divider()
        
        # Hair styling
        st.markdown("##### Hair Styling")
        st.text_input(
            "Hair Description (Optional)",
            key="hair_text",
            placeholder="e.g., Sleek bun, loose waves"
        )
        
        hair_file = st.file_uploader(
            "Upload Hair Reference (Optional)",
            type=['jpg', 'jpeg', 'png'],
            key="hair_file"
        )
        if hair_file:
            handle_image_upload(hair_file, "hair", "hair")

# Output Tab
with tab7:
    st.markdown("### Output Settings")
    st.caption("Configure the final output parameters")
    
    with st.container():
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### Platform Preset")
            platform = st.selectbox(
                "Platform",
                ["Instagram Portrait (4:5)", "Instagram Story (9:16)", "Instagram Square (1:1)", "Default (2:3)"],
                key="platform_preset",
                label_visibility="collapsed"
            )
        
        with col2:
            st.markdown("##### Number of Images")
            image_count = st.number_input(
                "Count",
                min_value=1,
                max_value=10,
                value=2,
                key="image_count",
                label_visibility="collapsed"
            )
        
        st.divider()
        
        st.markdown("##### Batch Variety")
        batch_variety = st.radio(
            "Variety",
            ["Subtle Variations", "Dynamic Angles"],
            key="batch_variety",
            horizontal=True,
            label_visibility="collapsed"
        )
        
        st.divider()
        
        # Configuration preview
        with st.expander("Full Configuration Preview (JSON)"):
            config = build_config()
            st.json(config)

# Generate Section - Fixed at bottom
st.divider()
st.markdown("### Ready to Generate?")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    generate_clicked = st.button(
        "Generate Photoshoot",
        type="primary",
        use_container_width=True,
        key="generate_button"
    )

# Handle generation
if generate_clicked:
    config = build_config()
    
    # Validate required fields
    has_model_ref = bool(config["model_reference"]["text_description"] or config["model_reference"]["image_url"])
    has_outfit = bool(config["base_outfit"]["text_description"] or config["base_outfit"]["image_url"])
    
    if not has_model_ref and not has_outfit:
        st.error("Please provide at least a model reference or outfit reference to generate.")
        st.stop()
    
    # Prepare image parts (returns both image_parts and image_mapping)
    with st.spinner("Preparing images..."):
        try:
            image_parts, image_mapping = client.prepare_image_parts(config)
        except Exception as e:
            st.error(f"Failed to prepare images: {str(e)}")
            st.stop()
    
    # Build prompt with image mapping
    prompt = build_photoshoot_prompt(config, image_mapping)
    
    # Get aspect ratio
    aspect_ratio = map_platform_preset_to_aspect_ratio(config["meta"]["platform_preset"])
    
    # Generate images
    image_count = config["output"]["count"]
    batch_variety = config["output"]["batch_variety"]
    
    generated_images = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(image_count):
        status_text.text(f"Generating image {i + 1} of {image_count}...")
        progress_bar.progress((i + 1) / image_count)
        
        try:
            image_bytes, mime_type = client.generate_image(
                prompt,
                image_parts,
                aspect_ratio,
                batch_index=i,
                batch_variety=batch_variety
            )
            
            with st.spinner(f"Uploading image {i + 1} to S3..."):
                upload_result = s3_handler.upload_generated_image(
                    image_bytes,
                    mime_type
                )
            
            if upload_result['success']:
                generated_images.append({
                    "s3_url": upload_result['public_url'],
                    "s3_key": upload_result['s3_key'],
                    "bytes": image_bytes,
                    "index": i + 1,
                    "mime_type": mime_type
                })
            else:
                st.error(f"Failed to upload image {i + 1}: {upload_result.get('error')}")
                
        except Exception as e:
            st.error(f"Error generating image {i + 1}: {str(e)}")
    
    progress_bar.empty()
    status_text.empty()
    
    # Display results
    if generated_images:
        st.success(f"Successfully generated {len(generated_images)} images!")
        
        st.markdown("### Generated Images")
        cols = st.columns(min(len(generated_images), 3))
        
        for idx, img_data in enumerate(generated_images):
            with cols[idx % 3]:
                image = Image.open(io.BytesIO(img_data["bytes"]))
                st.image(image, caption=f"Image {img_data['index']}", use_container_width=True)
                
                st.download_button(
                    label=f"Download",
                    data=img_data["bytes"],
                    file_name=f"photoshoot_{img_data['index']}.png",
                    mime=img_data["mime_type"],
                    key=f"download_{idx}"
                )
                
                st.caption(f"S3: {img_data['s3_url'][:40]}...")
        
        with st.expander("All S3 URLs"):
            for img_data in generated_images:
                st.code(img_data['s3_url'], language=None)
