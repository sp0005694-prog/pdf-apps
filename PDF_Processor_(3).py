import streamlit as st
import fitz  # PyMuPDF
from PIL import Image, ImageDraw
import numpy as np
import io
import zipfile
from pathlib import Path
import tempfile
import os
import time

# Try to import reportlab for PDF creation
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.utils import ImageReader
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Try to import python-docx, but make it optional
try:
    from docx import Document
    from docx.shared import Inches, Pt, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.section import WD_ORIENT
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

st.set_page_config(page_title="PDF Image Processor 1.3", layout="wide")

st.title("🔄 PDF Image Processor 1.3")
st.markdown("**High-Quality Visual Logo Selection + Freeform Polygon + Both-Direction Cropping**")

if not REPORTLAB_AVAILABLE:
    st.sidebar.warning("⚠️ PDF export requires: `pip install reportlab`")
if not DOCX_AVAILABLE:
    st.sidebar.warning("⚠️ Word export requires: `pip install python-docx`")

def get_all_page_images(pdf_file):
    """Extract all pages as images for logo setup - HIGH QUALITY"""
    try:
        pdf_data = pdf_file.getvalue()
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        page_images = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            # Increase DPI for better quality (300 DPI instead of default 72)
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom = ~144 DPI, 3x = ~216 DPI, 4x = ~288 DPI
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to RGB if needed
            if pix.n < 4:  # grayscale or RGB
                img_data = pix.tobytes("ppm")
            else:  # CMYK or other
                img_data = pix.tobytes("png")
                
            pil_image = Image.open(io.BytesIO(img_data))
            page_images.append(pil_image)
        
        doc.close()
        return page_images
    except Exception as e:
        st.error(f"Error extracting PDF pages: {str(e)}")
        return []

def create_grid_overlay(image, grid_size=50):
    """Create a visible grid overlay image with coordinates"""
    try:
        # Create a semi-transparent overlay
        overlay = Image.new('RGBA', image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Colors for better visibility
        grid_color = (0, 100, 255, 180)  # Blue with good opacity
        text_color = (0, 0, 0, 255)      # Solid black for text
        center_color = (255, 0, 0, 220)  # Solid red for center lines
        
        # Draw vertical lines
        for x in range(0, image.width, grid_size):
            draw.line([(x, 0), (x, image.height)], fill=grid_color, width=2)
            # Add coordinate text at top (with background for readability)
            text = str(x)
            bbox = draw.textbbox((0, 0), text)
            text_width = bbox[2] - bbox[0]
            draw.rectangle([x, 0, x + text_width + 4, 15], fill=(255, 255, 255, 200))
            draw.text((x + 2, 2), text, fill=text_color)
        
        # Draw horizontal lines
        for y in range(0, image.height, grid_size):
            draw.line([(0, y), (image.width, y)], fill=grid_color, width=2)
            # Add coordinate text at left (with background for readability)
            text = str(y)
            bbox = draw.textbbox((0, 0), text)
            text_width = bbox[2] - bbox[0]
            draw.rectangle([0, y, text_width + 4, y + 15], fill=(255, 255, 255, 200))
            draw.text((2, y + 2), text, fill=text_color)
        
        # Draw prominent center lines
        center_x = image.width // 2
        center_y = image.height // 2
        draw.line([(center_x, 0), (center_x, image.height)], fill=center_color, width=3)
        draw.line([(0, center_y), (image.width, center_y)], fill=center_color, width=3)
        
        # Add center coordinates with background
        center_text = f"Center: ({center_x}, {center_y})"
        bbox = draw.textbbox((0, 0), center_text)
        text_width = bbox[2] - bbox[0]
        draw.rectangle([center_x + 5, center_y + 5, center_x + text_width + 10, center_y + 20], 
                      fill=(255, 255, 255, 230))
        draw.text((center_x + 7, center_y + 7), center_text, fill=(255, 0, 0, 255))
        
        return overlay
    except Exception as e:
        st.error(f"Error creating grid overlay: {str(e)}")
        return Image.new('RGBA', image.size, (255, 255, 255, 0))

# ... [Keep all the other functions the same until process_pdf_with_logos] ...

def process_pdf_with_logos(pdf_file, logo_states, white_threshold, removal_method, cropping_method, main_progress, sub_progress, time_tracker):
    """Process all pages with logo removal and cropping with HIGH QUALITY"""
    processed_images = []
    
    pdf_data = pdf_file.getvalue()
    doc = fitz.open(stream=pdf_data, filetype="pdf")
    total_pages = len(doc)
    
    start_time = time.time()
    
    for page_num in range(total_pages):
        # Update main progress
        main_progress.progress((page_num) / total_pages, text=f"🔄 Processing page {page_num + 1}/{total_pages}")
        
        page = doc[page_num]
        # HIGH QUALITY: Use higher DPI for extraction
        mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to RGB if needed
        if pix.n < 4:
            img_data = pix.tobytes("ppm")
        else:
            img_data = pix.tobytes("png")
            
        pil_image = Image.open(io.BytesIO(img_data))
        
        # Step 1: Logo Removal (all 6 logos)
        sub_progress.progress(0.2, text=f"Removing logos...")
        for i in range(1, 7):
            if logo_states[f'logo{i}_enabled'] and logo_states[f'logo{i}_coords']:
                logo_type = logo_states.get(f'logo{i}_type', 'rectangle')
                pil_image = remove_logo_precise(pil_image, logo_states[f'logo{i}_coords'], logo_type, removal_method)
        
        # Step 2: Cropping
        sub_progress.progress(0.6, text=f"Cropping image...")
        if cropping_method == "vertical":
            pil_image = crop_vertical_only(pil_image, white_threshold)
        elif cropping_method == "horizontal":
            pil_image = crop_horizontal_only(pil_image, white_threshold)
        elif cropping_method == "both":
            pil_image = crop_both_fixed(pil_image, white_threshold)
        # else "none" - no cropping
        
        # Step 3: Finalize
        sub_progress.progress(1.0, text=f"Finalizing page {page_num + 1}...")
        processed_images.append(pil_image)
        
        # Estimate time remaining
        elapsed_time = time.time() - start_time
        pages_processed = page_num + 1
        time_per_page = elapsed_time / pages_processed
        remaining_pages = total_pages - pages_processed
        estimated_remaining = time_per_page * remaining_pages
        
        time_tracker.text(f"⏱️ Estimated time remaining: {estimated_remaining:.1f}s")
        
        # Reset sub-progress for next page
        if page_num < total_pages - 1:
            sub_progress.progress(0.0, text="Ready for next page...")
    
    doc.close()
    return processed_images

def create_pdf_from_images(images):
    """Create PDF from images using ReportLab - HIGH QUALITY"""
    if not REPORTLAB_AVAILABLE:
        raise ImportError("ReportLab is not installed. Please install with: pip install reportlab")
    
    try:
        if not images:
            return io.BytesIO().getvalue()
            
        buffer = io.BytesIO()
        
        # Process first image to create canvas
        first_img = images[0]
        first_img_width, first_img_height = first_img.size
        
        # Ensure minimum dimensions
        first_img_width = max(first_img_width, 1)
        first_img_height = max(first_img_height, 1)
        
        c = canvas.Canvas(buffer, pagesize=(first_img_width, first_img_height))
        
        # Add first image
        img_buffer = io.BytesIO()
        # HIGH QUALITY: Save with maximum quality
        first_img.save(img_buffer, format='PNG', optimize=False, quality=100)
        img_buffer.seek(0)
        pil_image = ImageReader(img_buffer)
        c.drawImage(pil_image, 0, 0, width=first_img_width, height=first_img_height)
        
        # Add remaining images
        for i in range(1, len(images)):
            img = images[i]
            img_width, img_height = img.size
            
            # Ensure minimum dimensions
            img_width = max(img_width, 1)
            img_height = max(img_height, 1)
            
            c.showPage()
            c.setPageSize((img_width, img_height))
            
            img_buffer = io.BytesIO()
            # HIGH QUALITY: Save with maximum quality
            img.save(img_buffer, format='PNG', optimize=False, quality=100)
            img_buffer.seek(0)
            pil_image = ImageReader(img_buffer)
            c.drawImage(pil_image, 0, 0, width=img_width, height=img_height)
        
        c.save()
        buffer.seek(0)
        return buffer.getvalue()
        
    except Exception as e:
        raise Exception(f"PDF creation failed: {str(e)}")

# Add quality settings to the sidebar
if uploaded_pdf:
    st.sidebar.success("✅ PDF uploaded successfully!")
    
    # Extract all pages for logo setup
    if st.session_state.all_page_images is None:
        with st.spinner("Loading PDF pages for logo setup..."):
            st.session_state.all_page_images = get_all_page_images(uploaded_pdf)
    
    # Step 1: Logo Setup
    st.sidebar.subheader("2. Logo Setup")
    setup_logo = st.sidebar.radio("Logo Removal:", ["No Logo Removal", "6-Logo Setup"])
    
    # Step 2: Processing Settings
    st.sidebar.subheader("3. Processing Settings")
    
    # QUALITY SETTINGS
    st.sidebar.subheader("🎯 Quality Settings")
    quality_level = st.sidebar.selectbox(
        "Image Quality:",
        ["standard", "high", "maximum"],
        format_func=lambda x: {
            "standard": "Standard (Faster)",
            "high": "High Quality", 
            "maximum": "Maximum Quality (Slower)"
        }[x],
        index=1  # Default to high quality
    )
    
    white_threshold = st.sidebar.slider("White Threshold", 200, 254, 245)
    
    removal_method = st.sidebar.selectbox("Logo Removal Method", 
                                        ["white", "smart"],
                                        format_func=lambda x: "White Fill" if x == "white" else "Smart Background Fill",
                                        help="Note: Smart fill works best with rectangle logos")
    
    # Both-direction cropping as default
    cropping_method = st.sidebar.selectbox(
        "Cropping Method:",
        ["both", "vertical", "horizontal", "none"],
        format_func=lambda x: {
            "both": "Both Directions (Default)",
            "vertical": "Vertical Only (top/bottom)", 
            "horizontal": "Horizontal Only (left/right)",
            "none": "No Cropping"
        }[x],
        index=0  # Default to "both"
    )

# Update the download section to use high quality
with cols[col_index]:
    # ZIP download - HIGH QUALITY
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for i, img in enumerate(st.session_state.processed_images):
            img_bytes = io.BytesIO()
            # HIGH QUALITY: Save with maximum quality
            img.save(img_bytes, format='PNG', optimize=False, quality=100)
            zip_file.writestr(f"page_{i+1:03d}.png", img_bytes.getvalue())
    
    st.download_button(
        label="💾 Download as ZIP (High Quality Images)",
        data=zip_buffer.getvalue(),
        file_name="processed_pages.zip",
        mime="application/zip",
        use_container_width=True
    )
