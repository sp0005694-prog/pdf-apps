import streamlit as st
import pypdf
import io
import base64
import fitz  # PyMuPDF
from pypdf import PdfReader, PdfWriter, PageObject

def create_split_pdf(original_pdf, split_data):
    """Create a new PDF with horizontal splits based on slider positions"""
    output_pdf = PdfWriter()
    
    for page_num in range(len(original_pdf.pages)):
        splits = split_data.get(page_num, [])
        original_page = original_pdf.pages[page_num]
        page_width = original_page.mediabox.width
        page_height = original_page.mediabox.height
        
        if splits:  # If splits exist for this page
            # Filter out splits at 0% and 100%, sort the rest
            valid_splits = [s for s in splits if 0 < s < 100]
            valid_splits.sort()
            
            if valid_splits:
                # Convert percentages to actual coordinates (for height)
                split_coords = [(s / 100) * page_height for s in valid_splits]
                all_splits = [0] + split_coords + [page_height]
                
                # Create subpages for each horizontal segment
                for i in range(len(all_splits) - 1):
                    top = all_splits[i]
                    bottom = all_splits[i + 1]
                    height = bottom - top
                    
                    # Create a new blank page with the segment height
                    new_page = PageObject.create_blank_page(
                        width=page_width,
                        height=height
                    )
                    
                    # Merge the original page segment onto the new page
                    new_page.merge_transformed_page(
                        original_page,
                        ctm=(1, 0, 0, 1, 0, -top)  # Shift vertically
                    )
                    output_pdf.add_page(new_page)
            else:
                # No valid splits, add original page
                output_pdf.add_page(original_page)
        else:
            # No splits, add original page
            output_pdf.add_page(original_page)
    
    return output_pdf

def get_page_image(pdf_reader, page_num):
    """Convert PDF page to base64 image"""
    # Create a temporary PDF with just this page
    temp_pdf = PdfWriter()
    temp_pdf.add_page(pdf_reader.pages[page_num])
    
    temp_pdf_bytes = io.BytesIO()
    temp_pdf.write(temp_pdf_bytes)
    temp_pdf_bytes.seek(0)
    
    # Convert PDF page to base64 for display
    doc = fitz.open("pdf", temp_pdf_bytes.read())
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
    img_data = pix.tobytes("png")
    doc.close()
    
    return base64.b64encode(img_data).decode()

def main():
    st.set_page_config(page_title="PDF Horizontal Splitter", layout="wide")
    
    st.title("📄 PDF Horizontal Splitter with Vertical Sliders")
    st.markdown("""
    **Instructions:**
    1. Upload a PDF file
    2. Drag the **vertical sliders** on the preview image to set **horizontal split** positions
    3. Only moved sliders will create splits
    4. Use page navigation to set splits for each page
    5. Download the split PDF when done
    """)
    
    # Initialize session state
    if 'split_data' not in st.session_state:
        st.session_state.split_data = {}
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 0
    if 'uploaded_pdf' not in st.session_state:
        st.session_state.uploaded_pdf = None
    if 'slider_defaults' not in st.session_state:
        st.session_state.slider_defaults = [0] * 10  # Track which sliders were moved

    # File upload
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file is not None:
        if st.session_state.uploaded_pdf != uploaded_file:
            # Reset state for new file
            st.session_state.uploaded_pdf = uploaded_file
            st.session_state.split_data = {}
            st.session_state.current_page = 0
            st.session_state.slider_defaults = [0] * 10
        
        try:
            # Read PDF
            uploaded_file.seek(0)
            pdf_reader = PdfReader(uploaded_file)
            total_pages = len(pdf_reader.pages)
            
            if total_pages == 0:
                st.error("The uploaded PDF appears to be empty.")
                return
            
            # Ensure current page is within bounds
            if st.session_state.current_page >= total_pages:
                st.session_state.current_page = total_pages - 1
            
            current_page_num = st.session_state.current_page
            
            # Page navigation
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if st.button("← Previous Page") and current_page_num > 0:
                    st.session_state.current_page -= 1
                    st.rerun()
            
            with col2:
                st.markdown(f"**Page {current_page_num + 1} of {total_pages}**")
                st.markdown("*Drag vertical sliders on the image to set horizontal split positions*")
            
            with col3:
                if st.button("Next Page →") and current_page_num < total_pages - 1:
                    st.session_state.current_page += 1
                    st.rerun()
            
            # Get current page data
            if current_page_num not in st.session_state.split_data:
                st.session_state.split_data[current_page_num] = [0] * 10  # 10 sliders, all at 0%
            
            current_splits = st.session_state.split_data[current_page_num]
            current_page = pdf_reader.pages[current_page_num]
            page_height = current_page.mediabox.height
            
            # Convert current page to image for display
            base64_img = get_page_image(pdf_reader, current_page_num)
            
            # Display the page image with interactive vertical sliders
            st.markdown("### Page Preview with Vertical Sliders")
            
            # Create HTML for image with vertical slider bars
            slider_bars_html = ""
            for i, split_percent in enumerate(current_splits):
                if split_percent > 0 and split_percent < 100:  # Only show sliders that are not at edges
                    is_active = st.session_state.slider_defaults[i] != split_percent
                    color = "#ff4444" if is_active else "#888888"
                    slider_bars_html += f'''
                    <div class="slider-bar" id="slider{i}" style="left: {(i * 10) + 5}%; background-color: {color};">
                        <div class="slider-handle" onclick="event.stopPropagation()">
                            <input type="range" min="0" max="100" value="{split_percent}" 
                                   oninput="updateSlider({i}, this.value)" 
                                   orient="vertical"
                                   style="height: 100%; width: 20px;">
                        </div>
                        <div class="slider-label">{i+1}</div>
                    </div>
                    '''
                else:
                    # Show inactive slider positions
                    slider_bars_html += f'''
                    <div class="slider-bar inactive" id="slider{i}" style="left: {(i * 10) + 5}%;">
                        <div class="slider-handle" onclick="event.stopPropagation()">
                            <input type="range" min="0" max="100" value="{split_percent}" 
                                   oninput="updateSlider({i}, this.value)" 
                                   orient="vertical"
                                   style="height: 100%; width: 20px;">
                        </div>
                        <div class="slider-label">{i+1}</div>
                    </div>
                    '''
            
            st.markdown(f"""
            <style>
            .slider-bar {{
                position: absolute;
                top: 0;
                bottom: 0;
                width: 20px;
                background-color: rgba(255, 68, 68, 0.3);
                cursor: pointer;
                z-index: 10;
                display: flex;
                flex-direction: column;
                align-items: center;
            }}
            .slider-bar.inactive {{
                background-color: rgba(136, 136, 136, 0.2);
            }}
            .slider-handle {{
                flex: 1;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .slider-label {{
                background: #333;
                color: white;
                padding: 2px 6px;
                border-radius: 3px;
                font-size: 10px;
                font-weight: bold;
                margin-bottom: 5px;
            }}
            .page-container {{
                position: relative;
                display: inline-block;
                border: 2px solid #ccc;
                margin: 10px 0;
                background: white;
                min-height: 400px;
            }}
            .horizontal-line {{
                position: absolute;
                left: 0;
                right: 0;
                height: 2px;
                background-color: #ff4444;
                pointer-events: none;
                z-index: 5;
            }}
            input[type="range"][orient="vertical"] {{
                writing-mode: bt-lr;
                -webkit-appearance: slider-vertical;
                width: 20px;
                height: 100%;
                padding: 0 5px;
            }}
            </style>
            
            <div class="page-container" id="pageContainer">
                <img src="data:image/png;base64,{base64_img}" 
                     style="max-width: 100%; height: auto; display: block;">
                
                <!-- Horizontal split lines -->
                {' '.join([f'<div class="horizontal-line" style="top: {s}%;"></div>' 
                          for s in current_splits if 0 < s < 100 and st.session_state.slider_defaults[current_splits.index(s)] != s])}
                
                <!-- Vertical slider bars -->
                {slider_bars_html}
            </div>
            
            <script>
            function updateSlider(sliderIndex, value) {{
                // Update the horizontal line position
                const horizontalLine = document.querySelectorAll('.horizontal-line')[sliderIndex];
                if (horizontalLine) {{
                    horizontalLine.style.top = value + '%';
                }}
                
                // Update slider bar color based on activity
                const sliderBar = document.getElementById('slider' + sliderIndex);
                if (sliderBar) {{
                    if (value > 0 && value < 100) {{
                        sliderBar.style.backgroundColor = 'rgba(255, 68, 68, 0.5)';
                    }} else {{
                        sliderBar.style.backgroundColor = 'rgba(136, 136, 136, 0.2)';
                    }}
                }}
                
                // Send updated value to Streamlit
                window.parent.postMessage({{
                    type: 'streamlit:setComponentValue',
                    value: sliderIndex + ':' + value
                }}, '*');
            }}
            </script>
            """, unsafe_allow_html=True)
            
            # Handle slider updates from JavaScript
            slider_update = st.components.v1.html("", height=0)
            if slider_update:
                try:
                    if ':' in slider_update:
                        slider_index, value = slider_update.split(':')
                        slider_index = int(slider_index)
                        value = float(value)
                        
                        # Update the specific slider value
                        current_splits = st.session_state.split_data[current_page_num].copy()
                        current_splits[slider_index] = value
                        st.session_state.split_data[current_page_num] = current_splits
                        
                        # Mark slider as active if moved from default
                        if value != 0:
                            st.session_state.slider_defaults[slider_index] = value
                        
                        st.rerun()
                except:
                    pass
            
            # Display active splits information
            active_splits = [s for s in current_splits if 0 < s < 100 and s != 0]
            st.markdown(f"**Active horizontal splits on this page: {len(active_splits)}**")
            if active_splits:
                st.write(f"Split positions (from top): {sorted(active_splits)}%")
                st.write(f"This will create {len(active_splits) + 1} horizontal segments")
                st.info("💡 **Horizontal splitting**: Each horizontal band becomes a separate page")
            
            # Control buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🧹 Reset This Page's Splits", use_container_width=True):
                    st.session_state.split_data[current_page_num] = [0] * 10
                    st.session_state.slider_defaults = [0] * 10
                    st.rerun()
            
            with col2:
                if st.button("🗑️ Clear All Pages' Splits", use_container_width=True):
                    st.session_state.split_data = {}
                    st.session_state.slider_defaults = [0] * 10
                    st.rerun()
            
            # Show split summary for all pages
            st.markdown("### Split Summary")
            for page_num in range(total_pages):
                page_splits = st.session_state.split_data.get(page_num, [0] * 10)
                active_splits = [s for s in page_splits if 0 < s < 100 and s != 0]
                segments = len(active_splits) + 1
                status = "✅" if active_splits else "⏳"
                current = "📍" if page_num == current_page_num else ""
                st.write(f"{status} {current} Page {page_num + 1}: {len(active_splits)} splits → {segments} horizontal segments")
            
            # Download section
            st.markdown("---")
            st.subheader("Download Horizontally Split PDF")
            
            if st.button("🛠️ Generate Horizontally Split PDF", type="primary", use_container_width=True):
                with st.spinner("Creating horizontally split PDF..."):
                    try:
                        # Reset file pointer and recreate reader
                        uploaded_file.seek(0)
                        pdf_reader = PdfReader(uploaded_file)
                        
                        # Prepare split data (only include active splits)
                        processed_split_data = {}
                        for page_num, splits in st.session_state.split_data.items():
                            # Only include splits that are not at 0% or 100% and were actually moved
                            active_splits = []
                            for split_val in splits:
                                if 0 < split_val < 100 and split_val != 0:
                                    active_splits.append(split_val)
                            processed_split_data[page_num] = active_splits
                        
                        # Create the split PDF
                        output_pdf = create_split_pdf(pdf_reader, processed_split_data)
                        
                        # Save to bytes
                        output_buffer = io.BytesIO()
                        output_pdf.write(output_buffer)
                        output_buffer.seek(0)
                        
                        # Show success message
                        total_original_pages = len(pdf_reader.pages)
                        total_new_pages = len(output_pdf.pages)
                        
                        st.success(f"✅ PDF horizontally split successfully!")
                        st.info(f"Original: {total_original_pages} pages → New: {total_new_pages} pages")
                        
                        # Download button
                        st.download_button(
                            label="📥 Download Horizontally Split PDF",
                            data=output_buffer.getvalue(),
                            file_name="horizontally_split_document.pdf",
                            mime="application/pdf",
                            type="primary",
                            use_container_width=True
                        )
                        
                    except Exception as e:
                        st.error(f"❌ Error generating PDF: {str(e)}")
                        
        except Exception as e:
            st.error(f"Error processing PDF: {str(e)}")
    
    else:
        st.info("📁 Please upload a PDF file to get started.")

if __name__ == "__main__":
    main()
