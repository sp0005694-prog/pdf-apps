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
        
        if splits:  # If splits exist for this page
            # Filter out splits at 0% and 100%, sort the rest
            valid_splits = [s for s in splits if 0 < s < 100]
            valid_splits.sort()
            
            if valid_splits:
                # Convert percentages to actual coordinates
                split_coords = [(s / 100) * page_width for s in valid_splits]
                all_splits = [0] + split_coords + [page_width]
                
                # Create subpages for each segment
                for i in range(len(all_splits) - 1):
                    left = all_splits[i]
                    right = all_splits[i + 1]
                    width = right - left
                    
                    # Create a new blank page with the segment width
                    new_page = PageObject.create_blank_page(
                        width=width,
                        height=original_page.mediabox.height
                    )
                    
                    # Merge the original page segment onto the new page
                    new_page.merge_transformed_page(
                        original_page,
                        ctm=(1, 0, 0, 1, -left, 0)
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
    
    st.title("📄 PDF Horizontal Splitter with Sliders")
    st.markdown("""
    **Instructions:**
    1. Upload a PDF file
    2. Drag the vertical sliders to set split positions
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
                st.markdown("*Drag sliders below to set split positions*")
            
            with col3:
                if st.button("Next Page →") and current_page_num < total_pages - 1:
                    st.session_state.current_page += 1
                    st.rerun()
            
            # Get current page data
            if current_page_num not in st.session_state.split_data:
                st.session_state.split_data[current_page_num] = [0] * 10  # 10 sliders, all at 0%
            
            current_splits = st.session_state.split_data[current_page_num]
            current_page = pdf_reader.pages[current_page_num]
            page_width = current_page.mediabox.width
            
            # Convert current page to image for display
            base64_img = get_page_image(pdf_reader, current_page_num)
            
            # Display the page image with visual split lines
            st.markdown("### Page Preview with Split Lines")
            
            # Create HTML for image with split lines
            split_lines_html = ""
            for i, split_percent in enumerate(current_splits):
                if split_percent > 0 and split_percent < 100:  # Only show lines that are not at edges
                    color = "#ff4444" if st.session_state.slider_defaults[i] != split_percent else "#cccccc"
                    split_lines_html += f'''
                    <div class="split-line" style="left: {split_percent}%; background-color: {color};">
                        <div class="split-label">{i+1}</div>
                    </div>
                    '''
            
            st.markdown(f"""
            <style>
            .split-line {{
                position: absolute;
                top: 0;
                bottom: 0;
                width: 3px;
                background-color: #ff4444;
                pointer-events: none;
                z-index: 10;
            }}
            .split-label {{
                position: absolute;
                top: 5px;
                left: -10px;
                background: #ff4444;
                color: white;
                padding: 2px 6px;
                border-radius: 3px;
                font-size: 12px;
                font-weight: bold;
            }}
            .page-container {{
                position: relative;
                display: inline-block;
                border: 2px solid #ccc;
                margin: 10px 0;
                background: white;
            }}
            .slider-active {{
                border-left: 3px solid #ff4444;
                border-right: 3px solid #ff4444;
            }}
            </style>
            
            <div class="page-container">
                <img src="data:image/png;base64,{base64_img}" 
                     style="max-width: 100%; height: auto; display: block;">
                {split_lines_html}
            </div>
            """, unsafe_allow_html=True)
            
            # Sliders for split positions
            st.markdown("### Split Position Sliders")
            st.markdown("**Drag sliders to set vertical split lines. Only moved sliders will create splits.**")
            
            # Create 10 sliders
            new_splits = []
            slider_changed = False
            
            cols = st.columns(2)
            for i in range(10):
                with cols[i % 2]:
                    slider_key = f"slider_{current_page_num}_{i}"
                    default_value = current_splits[i] if i < len(current_splits) else 0
                    
                    # Create slider
                    new_value = st.slider(
                        f"Split Line {i+1}",
                        min_value=0,
                        max_value=100,
                        value=default_value,
                        key=slider_key,
                        help=f"Set position for split line {i+1} (0-100%)"
                    )
                    
                    new_splits.append(new_value)
                    
                    # Check if slider was moved from default
                    if new_value != st.session_state.slider_defaults[i]:
                        slider_changed = True
            
            # Update splits if any slider changed
            if slider_changed:
                st.session_state.split_data[current_page_num] = new_splits
                # Update defaults to track which sliders were actually moved
                for i in range(10):
                    if new_splits[i] != st.session_state.slider_defaults[i]:
                        st.session_state.slider_defaults[i] = new_splits[i]
            
            # Display active splits
            active_splits = [s for s in new_splits if 0 < s < 100 and s != st.session_state.slider_defaults[new_splits.index(s)]]
            st.markdown(f"**Active splits on this page: {len(active_splits)}**")
            if active_splits:
                st.write(f"Split positions: {sorted(active_splits)}%")
                st.write(f"This will create {len(active_splits) + 1} vertical segments")
            
            # Control buttons
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("🧹 Reset This Page's Splits"):
                    st.session_state.split_data[current_page_num] = [0] * 10
                    st.session_state.slider_defaults = [0] * 10
                    st.rerun()
            
            with col2:
                if st.button("🗑️ Clear All Pages' Splits"):
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
                st.write(f"{status} {current} Page {page_num + 1}: {len(active_splits)} splits → {segments} segments")
            
            # Download section
            st.markdown("---")
            st.subheader("Download Split PDF")
            
            if st.button("🛠️ Generate Split PDF", type="primary", use_container_width=True):
                with st.spinner("Creating split PDF..."):
                    try:
                        # Reset file pointer and recreate reader
                        uploaded_file.seek(0)
                        pdf_reader = PdfReader(uploaded_file)
                        
                        # Prepare split data (only include active splits)
                        processed_split_data = {}
                        for page_num, splits in st.session_state.split_data.items():
                            # Only include splits that are not at 0% or 100% and were actually moved
                            active_splits = []
                            for i, split_val in enumerate(splits):
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
                        
                        st.success(f"✅ PDF split successfully!")
                        st.info(f"Original: {total_original_pages} pages → New: {total_new_pages} pages")
                        
                        # Download button
                        st.download_button(
                            label="📥 Download Split PDF",
                            data=output_buffer.getvalue(),
                            file_name="split_document.pdf",
                            mime="application/pdf",
                            type="primary",
                            use_container_width=True
                        )
                        
                    except Exception as e:
                        st.error(f"❌ Error generating PDF: {str(e)}")
                        st.info("If the PDF is encrypted, please provide the password.")
                        
        except Exception as e:
            st.error(f"Error processing PDF: {str(e)}")
    
    else:
        st.info("📁 Please upload a PDF file to get started.")

if __name__ == "__main__":
    main()
