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
    2. Click and drag on the vertical slider bars on the image to set horizontal split positions
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
    if 'slider_positions' not in st.session_state:
        st.session_state.slider_positions = [0] * 10

    # File upload
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file is not None:
        if st.session_state.uploaded_pdf != uploaded_file:
            # Reset state for new file
            st.session_state.uploaded_pdf = uploaded_file
            st.session_state.split_data = {}
            st.session_state.current_page = 0
            st.session_state.slider_positions = [0] * 10
        
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
                st.markdown("*Click and drag vertical sliders on the image*")
            
            with col3:
                if st.button("Next Page →") and current_page_num < total_pages - 1:
                    st.session_state.current_page += 1
                    st.rerun()
            
            # Get current page data
            if current_page_num not in st.session_state.split_data:
                st.session_state.split_data[current_page_num] = [0] * 10
            
            current_splits = st.session_state.split_data[current_page_num]
            current_page = pdf_reader.pages[current_page_num]
            
            # Convert current page to image for display
            base64_img = get_page_image(pdf_reader, current_page_num)
            
            # Create interactive slider interface
            st.markdown("### Interactive Slider Interface")
            st.markdown("**Click on the slider bars and use the sliders below to adjust positions**")
            
            # Create the interactive HTML with vertical sliders
            slider_bars_html = ""
            horizontal_lines_html = ""
            
            for i in range(10):
                slider_value = current_splits[i]
                left_position = (i * 9) + 5  # Spread sliders evenly (5%, 14%, 23%, etc.)
                
                # Create slider bar
                slider_bars_html += f'''
                <div class="slider-container" id="slider{i}">
                    <div class="slider-bar" onclick="selectSlider({i})">
                        <div class="slider-track"></div>
                        <div class="slider-handle" style="top: {100 - slider_value}%;">
                            <div class="handle-label">{i+1}</div>
                        </div>
                    </div>
                </div>
                '''
                
                # Create horizontal line for active sliders
                if slider_value > 0 and slider_value < 100:
                    horizontal_lines_html += f'<div class="horizontal-line" style="top: {slider_value}%;"></div>'
            
            html_content = f'''
            <!DOCTYPE html>
            <html>
            <head>
            <style>
            .preview-container {{
                position: relative;
                display: inline-block;
                border: 2px solid #ccc;
                margin: 20px 0;
                background: white;
            }}
            .page-image {{
                max-width: 100%;
                height: auto;
                display: block;
            }}
            .slider-container {{
                position: absolute;
                top: 0;
                bottom: 0;
                width: 30px;
                cursor: pointer;
                z-index: 10;
            }}
            .slider-bar {{
                position: absolute;
                top: 10px;
                bottom: 10px;
                left: 5px;
                width: 20px;
                background: rgba(255, 68, 68, 0.3);
                border-radius: 10px;
                border: 2px solid #ff4444;
            }}
            .slider-track {{
                position: absolute;
                top: 0;
                bottom: 0;
                left: 7px;
                width: 6px;
                background: #ff4444;
                border-radius: 3px;
            }}
            .slider-handle {{
                position: absolute;
                left: -5px;
                width: 30px;
                height: 20px;
                background: #ff4444;
                border-radius: 10px;
                cursor: grab;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s;
            }}
            .slider-handle:hover {{
                background: #ff0000;
                transform: scale(1.1);
            }}
            .handle-label {{
                color: white;
                font-size: 10px;
                font-weight: bold;
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
            .slider-active {{
                background: rgba(255, 0, 0, 0.5) !important;
                border-color: #ff0000 !important;
            }}
            </style>
            </head>
            <body>
            <div class="preview-container" id="previewContainer">
                <img src="data:image/png;base64,{base64_img}" class="page-image" id="pageImage">
                {horizontal_lines_html}
                {slider_bars_html}
            </div>
            
            <script>
            let selectedSlider = null;
            
            function selectSlider(sliderIndex) {{
                selectedSlider = sliderIndex;
                // Update all slider appearances
                for (let i = 0; i < 10; i++) {{
                    const slider = document.getElementById('slider' + i);
                    if (i === sliderIndex) {{
                        slider.querySelector('.slider-bar').classList.add('slider-active');
                    }} else {{
                        slider.querySelector('.slider-bar').classList.remove('slider-active');
                    }}
                }}
                // Send selection to Streamlit
                window.parent.postMessage({{
                    type: 'streamlit:setComponentValue',
                    value: 'SELECT:' + sliderIndex
                }}, '*');
            }}
            
            // Initialize slider positions
            window.addEventListener('load', function() {{
                // Select first slider by default
                selectSlider(0);
            }});
            </script>
            </body>
            </html>
            '''
            
            # Display the interactive preview
            st.components.v1.html(html_content, height=600)
            
            # Slider controls for the selected slider
            st.markdown("### Adjust Selected Slider")
            
            # Get selected slider from session state or default to 0
            selected_slider = st.session_state.get('selected_slider', 0)
            
            col1, col2 = st.columns([1, 3])
            with col1:
                st.markdown(f"**Selected: Slider {selected_slider + 1}**")
                st.markdown(f"Current position: **{current_splits[selected_slider]}%** from top")
            
            with col2:
                # Slider to control the selected slider's position
                new_value = st.slider(
                    f"Position for Slider {selected_slider + 1}",
                    min_value=0,
                    max_value=100,
                    value=current_splits[selected_slider],
                    key=f"slider_control_{current_page_num}",
                    help="Adjust the vertical position of the selected slider"
                )
                
                # Update the slider position if changed
                if new_value != current_splits[selected_slider]:
                    updated_splits = current_splits.copy()
                    updated_splits[selected_slider] = new_value
                    st.session_state.split_data[current_page_num] = updated_splits
                    st.session_state.slider_positions[selected_slider] = new_value
                    st.rerun()
            
            # Handle slider selection from JavaScript
            js_data = st.components.v1.html("", height=0)
            if js_data and js_data.startswith('SELECT:'):
                try:
                    slider_index = int(js_data.split(':')[1])
                    st.session_state.selected_slider = slider_index
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
            
            # Quick position buttons
            st.markdown("### Quick Positions")
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                if st.button("25%", use_container_width=True) and selected_slider is not None:
                    updated_splits = current_splits.copy()
                    updated_splits[selected_slider] = 25
                    st.session_state.split_data[current_page_num] = updated_splits
                    st.rerun()
            with col2:
                if st.button("50%", use_container_width=True) and selected_slider is not None:
                    updated_splits = current_splits.copy()
                    updated_splits[selected_slider] = 50
                    st.session_state.split_data[current_page_num] = updated_splits
                    st.rerun()
            with col3:
                if st.button("75%", use_container_width=True) and selected_slider is not None:
                    updated_splits = current_splits.copy()
                    updated_splits[selected_slider] = 75
                    st.session_state.split_data[current_page_num] = updated_splits
                    st.rerun()
            with col4:
                if st.button("Reset", use_container_width=True) and selected_slider is not None:
                    updated_splits = current_splits.copy()
                    updated_splits[selected_slider] = 0
                    st.session_state.split_data[current_page_num] = updated_splits
                    st.rerun()
            with col5:
                if st.button("Clear All", use_container_width=True):
                    st.session_state.split_data[current_page_num] = [0] * 10
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
                            active_splits = [s for s in splits if 0 < s < 100 and s != 0]
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
