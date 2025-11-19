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
st.markdown("**High Quality + Single Column Word + Smart Page Splitting**")

if not REPORTLAB_AVAILABLE:
    st.sidebar.warning("⚠️ PDF export requires: `pip install reportlab`")
if not DOCX_AVAILABLE:
    st.sidebar.warning("⚠️ Word export requires: `pip install python-docx`")

def get_all_page_images(pdf_file, dpi=300):
    """Extract all pages as high-quality images"""
    try:
        pdf_data = pdf_file.getvalue()
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        page_images = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            # Use high DPI for better quality
            mat = fitz.Matrix(dpi/72, dpi/72)  # Scale for high resolution
            pix = page.get_pixmap(matrix=mat)
            
            # Use PNG format to preserve quality
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

def draw_polygon_preview(draw, points, color, label):
    """Draw polygon with label and vertex markers"""
    try:
        if len(points) < 2:
            return
        
        # Draw polygon outline
        if len(points) >= 3:
            draw.polygon(points, outline=color, width=3)
        
        # Draw connecting lines
        for i in range(len(points)):
            start_point = points[i]
            end_point = points[(i + 1) % len(points)]
            draw.line([start_point, end_point], fill=color, width=2)
        
        # Draw vertex points and numbers
        for i, (x, y) in enumerate(points):
            # Draw vertex circle
            draw.ellipse([x-4, y-4, x+4, y+4], fill=color, outline=(255, 255, 255), width=1)
            # Draw vertex number
            draw.text((x+6, y-10), str(i+1), fill=color)
        
        # Draw label at first point
        if points:
            label_x, label_y = points[0]
            draw.text((label_x, label_y-25), label, fill=color)
    except Exception as e:
        st.error(f"Error drawing polygon preview: {str(e)}")

def visual_logo_selection(image, logo_states):
    """Visual logo selection with interactive coordinate selection"""
    try:
        st.subheader("🎯 Logo Area Setup (6 Boxes: 4 Rectangle + 2 Polygon)")
        
        # Page selection for visual reference
        if 'all_page_images' in st.session_state:
            page_options = list(range(1, len(st.session_state.all_page_images) + 1))
            selected_page = st.selectbox(
                "Select Page for Visual Reference:",
                page_options,
                index=0,
                help="Select which page to use for setting logo coordinates. Coordinates will apply to ALL pages."
            )
            
            # Update image to selected page
            image = st.session_state.all_page_images[selected_page - 1]
            st.info(f"📄 Using Page {selected_page} for reference. Logo coordinates will apply to all {len(st.session_state.all_page_images)} pages.")
        
        # Grid settings
        st.subheader("🗺️ Grid Settings")
        grid_col1, grid_col2, grid_col3 = st.columns(3)
        with grid_col1:
            show_grid = st.toggle("Show Grid Overlay", value=True, help="Display grid lines for easier coordinate selection")
        with grid_col2:
            grid_size = st.slider("Grid Size (pixels)", min_value=25, max_value=200, value=50, 
                                 help="Distance between grid lines")
        with grid_col3:
            grid_opacity = st.slider("Grid Opacity", min_value=50, max_value=100, value=80,
                                    help="Grid visibility level") / 100.0
        
        # Create display image with optional grid
        display_img = image.copy().convert('RGBA')
        if show_grid:
            grid_overlay = create_grid_overlay(image, grid_size)
            # Adjust opacity
            if grid_opacity < 1.0:
                grid_overlay = grid_overlay.convert('RGBA')
                data = np.array(grid_overlay)
                data[..., 3] = (data[..., 3] * grid_opacity).astype(np.uint8)
                grid_overlay = Image.fromarray(data)
            
            display_img = Image.alpha_composite(display_img, grid_overlay)
        
        # Display the reference image
        st.image(display_img, caption="Reference Image with Grid - Click buttons below to set logo areas", use_column_width=True)
        
        # Interactive Point Selection
        st.subheader("🎯 Interactive Area Selection")
        st.info("**Click the buttons below to set logo areas at common positions**")
        
        point_cols = st.columns(4)
        click_points = {}
        
        with point_cols[0]:
            if st.button("📍 Top-Left Area", use_container_width=True):
                click_points = {"x1": 10, "y1": 10, "x2": 110, "y2": 60}
        with point_cols[1]:
            if st.button("📍 Top-Right Area", use_container_width=True):
                click_points = {"x1": image.width-120, "y1": 10, "x2": image.width-20, "y2": 60}
        with point_cols[2]:
            if st.button("📍 Bottom-Left Area", use_container_width=True):
                click_points = {"x1": 10, "y1": image.height-70, "x2": 110, "y2": image.height-20}
        with point_cols[3]:
            if st.button("📍 Bottom-Right Area", use_container_width=True):
                click_points = {"x1": image.width-120, "y1": image.height-70, "x2": image.width-20, "y2": image.height-20}
        
        # Apply clicked points to Logo 1
        if click_points and not st.session_state.get('logo1_coords'):
            st.session_state.logo1_x1 = click_points["x1"]
            st.session_state.logo1_y1 = click_points["y1"]
            st.session_state.logo1_x2 = click_points["x2"]
            st.session_state.logo1_y2 = click_points["y2"]
            st.session_state.logo1_enabled = True
            st.success("✅ Logo 1 area set! Adjust coordinates below or set other logos.")
        
        # Coordinate Boxes Section
        st.subheader("📐 Coordinate Controls")
        
        # Create 6 columns for logo toggles (4 rectangle + 2 polygon)
        toggle_cols = st.columns(6)
        logo_enabled = {}
        logo_types = {}
        
        # Rectangle logos (1-4)
        for i in range(1, 5):
            with toggle_cols[i-1]:
                logo_enabled[i] = st.toggle(f"Logo {i} (Rect)", 
                                          value=logo_states[f'logo{i}_enabled'],
                                          key=f"logo{i}_toggle")
                logo_types[i] = "rectangle"
        
        # Polygon logos (5-6)
        for i in range(5, 7):
            with toggle_cols[i-1]:
                logo_enabled[i] = st.toggle(f"Logo {i} (Polygon)", 
                                          value=logo_states[f'logo{i}_enabled'],
                                          key=f"logo{i}_toggle")
                logo_types[i] = "polygon"
        
        # Logo coordinate inputs
        logo_coords = {}
        colors = ["red", "blue", "green", "orange", "purple", "brown"]
        
        for i in range(1, 7):
            if logo_enabled[i]:
                if logo_types[i] == "rectangle":
                    with st.expander(f"🎯 Logo {i} - Rectangle ({colors[i-1].title()})", expanded=True):
                        cols = st.columns(4)
                        
                        with cols[0]:
                            x1 = st.number_input(f"Left (X1)", 
                                               min_value=0, max_value=image.width,
                                               value=logo_states[f'logo{i}_coords'][0] if logo_states[f'logo{i}_coords'] else 50 + (i-1)*30,
                                               key=f"logo{i}_x1")
                        with cols[1]:
                            y1 = st.number_input(f"Top (Y1)", 
                                               min_value=0, max_value=image.height,
                                               value=logo_states[f'logo{i}_coords'][1] if logo_states[f'logo{i}_coords'] else 50 + (i-1)*40,
                                               key=f"logo{i}_y1")
                        with cols[2]:
                            x2 = st.number_input(f"Right (X2)", 
                                               min_value=0, max_value=image.width,
                                               value=logo_states[f'logo{i}_coords'][2] if logo_states[f'logo{i}_coords'] else 150 + (i-1)*30,
                                               key=f"logo{i}_x2")
                        with cols[3]:
                            y2 = st.number_input(f"Bottom (Y2)", 
                                               min_value=0, max_value=image.height,
                                               value=logo_states[f'logo{i}_coords'][3] if logo_states[f'logo{i}_coords'] else 100 + (i-1)*40,
                                               key=f"logo{i}_y2")
                        
                        # Ensure valid coordinates
                        if x2 <= x1:
                            x2 = x1 + 10
                        if y2 <= y1:
                            y2 = y1 + 10
                        
                        logo_coords[i] = (x1, y1, x2, y2)
                        
                        # Show coordinate summary
                        st.success(f"Logo {i}: ({x1}, {y1}) to ({x2}, {y2}) | Size: {x2-x1}×{y2-y1} pixels")
                
                else:  # polygon
                    with st.expander(f"🔷 Logo {i} - Freeform Polygon ({colors[i-1].title()})", expanded=True):
                        # Polygon points configuration
                        num_points = st.slider(f"Number of Polygon Points", 
                                             min_value=3, max_value=8, value=4,
                                             key=f"polygon{i}_points")
                        
                        st.info(f"Configure {num_points} points for the polygon:")
                        
                        # Dynamic point inputs
                        polygon_points = []
                        point_cols = st.columns(2)
                        
                        for point_idx in range(num_points):
                            col_idx = point_idx % 2
                            with point_cols[col_idx]:
                                st.markdown(f"**Point {point_idx + 1}**")
                                x = st.number_input(f"X{point_idx + 1}", 
                                                  min_value=0, max_value=image.width,
                                                  value=100 + point_idx * 20,
                                                  key=f"polygon{i}_point{point_idx}_x")
                                y = st.number_input(f"Y{point_idx + 1}", 
                                                  min_value=0, max_value=image.height,
                                                  value=100 + point_idx * 15,
                                                  key=f"polygon{i}_point{point_idx}_y")
                                polygon_points.append((x, y))
                        
                        logo_coords[i] = tuple(polygon_points)
                        
                        # Show polygon summary
                        points_str = " → ".join([f"({x},{y})" for x, y in polygon_points])
                        st.success(f"Logo {i}: {num_points}-sided polygon | Points: {points_str}")
        
        # Real-time Preview Section
        st.subheader("👁️ Live Preview")
        
        # Create preview image with grid
        preview_img = image.copy().convert('RGBA')
        if show_grid:
            grid_overlay = create_grid_overlay(image, grid_size)
            # Adjust opacity
            if grid_opacity < 1.0:
                grid_overlay = grid_overlay.convert('RGBA')
                data = np.array(grid_overlay)
                data[..., 3] = (data[..., 3] * grid_opacity).astype(np.uint8)
                grid_overlay = Image.fromarray(data)
            
            preview_img = Image.alpha_composite(preview_img, grid_overlay)
        
        draw = ImageDraw.Draw(preview_img)
        
        active_logos = []
        for i in range(1, 7):
            if logo_enabled[i] and logo_coords.get(i):
                if logo_types[i] == "rectangle":
                    x1, y1, x2, y2 = logo_coords[i]
                    # Draw rectangle box with thick border
                    draw.rectangle([x1, y1, x2, y2], outline=colors[i-1], width=4)
                    # Add label with background
                    label = f"LOGO {i}"
                    bbox = draw.textbbox((0, 0), label)
                    text_width = bbox[2] - bbox[0]
                    draw.rectangle([x1, y1-30, x1 + text_width + 6, y1-10], fill=(255, 255, 255, 200))
                    draw.text((x1+3, y1-28), label, fill=colors[i-1])
                    # Add size info with background
                    size_text = f"{x2-x1}×{y2-y1}"
                    bbox = draw.textbbox((0, 0), size_text)
                    text_width = bbox[2] - bbox[0]
                    draw.rectangle([x1, y2+2, x1 + text_width + 6, y2+22], fill=(255, 255, 255, 200))
                    draw.text((x1+3, y2+4), size_text, fill=colors[i-1])
                    active_logos.append(f"Logo {i} (Rect)")
                    
                else:  # polygon
                    points = logo_coords[i]
                    if len(points) >= 3:
                        draw_polygon_preview(draw, points, colors[i-1], f"LOGO {i}")
                        active_logos.append(f"Logo {i} (Polygon)")
        
        st.image(preview_img, caption="🔴 Logo 1 | 🔵 Logo 2 | 🟢 Logo 3 | 🟠 Logo 4 | 🟣 Logo 5 | 🟤 Logo 6", use_column_width=True)
        
        # Quick Actions
        if any(logo_enabled.values()):
            st.subheader("⚡ Quick Actions")
            action_cols = st.columns(3)
            
            with action_cols[0]:
                if st.button("📋 Copy Logo 1 to Others", use_container_width=True):
                    if logo_enabled[1] and logo_coords.get(1) and logo_types[1] == "rectangle":
                        base_x1, base_y1, base_x2, base_y2 = logo_coords[1]
                        for i in range(2, 5):  # Only copy to other rectangles
                            if logo_enabled[i] and logo_types[i] == "rectangle":
                                offset = (i-1) * 20
                                st.session_state[f'logo{i}_x1'] = base_x1 + offset
                                st.session_state[f'logo{i}_y1'] = base_y1 + offset
                                st.session_state[f'logo{i}_x2'] = base_x2 + offset
                                st.session_state[f'logo{i}_y2'] = base_y2 + offset
                        st.rerun()
            
            with action_cols[1]:
                if st.button("🔄 Reset All Positions", use_container_width=True):
                    for i in range(1, 7):
                        if logo_enabled[i]:
                            if logo_types[i] == "rectangle":
                                st.session_state[f'logo{i}_x1'] = 50 + (i-1)*30
                                st.session_state[f'logo{i}_y1'] = 50 + (i-1)*40
                                st.session_state[f'logo{i}_x2'] = 150 + (i-1)*30
                                st.session_state[f'logo{i}_y2'] = 100 + (i-1)*40
                            else:  # polygon
                                # Reset polygon points to default positions
                                num_points = st.session_state.get(f'polygon{i}_points', 4)
                                for point_idx in range(num_points):
                                    st.session_state[f'polygon{i}_point{point_idx}_x'] = 100 + point_idx * 20
                                    st.session_state[f'polygon{i}_point{point_idx}_y'] = 100 + point_idx * 15
                    st.rerun()
            
            with action_cols[2]:
    if st.button("🎯 Auto-Space Logos", use_container_width=True):
        img_w, img_h = image.width, image.height
        logo_width, logo_height = 100, 50
        spacing_x = (img_w - (4 * logo_width)) // 5
        spacing_y = (img_h - logo_height) // 2
        
        for i in range(1, 5):  # Only auto-space rectangles
            if logo_enabled[i] and logo_types[i] == "rectangle":
                x1 = spacing_x + (i-1) * (logo_width + spacing_x)
                y1 = spacing_y
                st.session_state[f'logo{i}_x1'] = x1
                st.session_state[f'logo{i}_y1'] = y1
                st.session_state[f'logo{i}_x2'] = x1 + logo_width
                st.session_state[f'logo{i}_y2'] = y1 + logo_height
        st.rerun()
