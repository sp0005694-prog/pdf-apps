import streamlit as st
import pypdf
import io
import base64
import fitz  # PyMuPDF

def create_split_pdf(original_pdf, split_data):
    """Create a new PDF with horizontal splits based on user clicks"""
    output_pdf = pypdf.PdfWriter()
    
    for page_num in range(len(original_pdf.pages)):
        splits = split_data.get(page_num, [])
        original_page = original_pdf.pages[page_num]
        page_width = original_page.mediabox.width
        page_height = original_page.mediabox.height
        
        if splits:  # If splits exist for this page
            # Sort splits and add boundaries
            sorted_splits = sorted(splits)
            all_splits = [0] + sorted_splits + [page_width]
            
            # Create subpages for each segment
            for i in range(len(all_splits) - 1):
                left = all_splits[i]
                right = all_splits[i + 1]
                
                # Create new page with the segment
                new_page = pypdf.PageObject.create_blank_page(
                    width=right - left,
                    height=page_height
                )
                
                # Copy the segment from original page
                new_page.merge_transformed_page(
                    original_page,
                    (
                        1, 0, 0, 1,  # No scaling or rotation
                        -left, 0     # Translate to show only the segment
                    )
                )
                output_pdf.add_page(new_page)
        else:
            # No splits, add original page
            output_pdf.add_page(original_page)
    
    return output_pdf

def get_page_image(pdf_reader, page_num):
    """Convert PDF page to base64 image"""
    # Create a temporary PDF with just this page
    temp_pdf = pypdf.PdfWriter()
    temp_pdf.add_page(pdf_reader.pages[page_num])
    
    temp_pdf_bytes = io.BytesIO()
    temp_pdf.write(temp_pdf_bytes)
    temp_pdf_bytes.seek(0)
    
    # Convert PDF page to base64 for display
    doc = fitz.open("pdf", temp_pdf_bytes.read())
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # Good resolution
    img_data = pix.tobytes("png")
    doc.close()
    
    return base64.b64encode(img_data).decode()

def main():
    st.set_page_config(page_title="PDF Horizontal Splitter", layout="wide")
    
    st.title("📄 PDF Horizontal Splitter")
    st.markdown("""
    **Instructions:**
    1. Upload a PDF file
    2. Click on the page image to add vertical split lines
    3. Use **← → arrow keys** to navigate between pages
    4. Download the split PDF when done
    """)
    
    # Initialize session state
    if 'split_data' not in st.session_state:
        st.session_state.split_data = {}
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 0
    if 'uploaded_pdf' not in st.session_state:
        st.session_state.uploaded_pdf = None
    if 'page_width' not in st.session_state:
        st.session_state.page_width = 0
    if 'click_coord' not in st.session_state:
        st.session_state.click_coord = None
    if 'navigation' not in st.session_state:
        st.session_state.navigation = None

    # Handle navigation and clicks from form submissions
    if st.session_state.navigation == 'prev' and st.session_state.current_page > 0:
        st.session_state.current_page -= 1
        st.session_state.navigation = None
        st.rerun()
    elif st.session_state.navigation == 'next':
        st.session_state.current_page += 1
        st.session_state.navigation = None
        st.rerun()
    
    # Handle click coordinates
    if st.session_state.click_coord is not None:
        current_page_num = st.session_state.current_page
        if current_page_num not in st.session_state.split_data:
            st.session_state.split_data[current_page_num] = []
        
        new_split = st.session_state.click_coord
        page_width = st.session_state.page_width
        
        if 0 <= new_split <= page_width and new_split not in st.session_state.split_data[current_page_num]:
            st.session_state.split_data[current_page_num].append(new_split)
        
        st.session_state.click_coord = None
        st.rerun()

    # File upload
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file is not None:
        if st.session_state.uploaded_pdf != uploaded_file:
            # Reset state for new file
            st.session_state.uploaded_pdf = uploaded_file
            st.session_state.split_data = {}
            st.session_state.current_page = 0
        
        try:
            # Read PDF
            uploaded_file.seek(0)
            pdf_reader = pypdf.PdfReader(uploaded_file)
            total_pages = len(pdf_reader.pages)
            
            if total_pages == 0:
                st.error("The uploaded PDF appears to be empty.")
                return
            
            # Ensure current page is within bounds
            if st.session_state.current_page >= total_pages:
                st.session_state.current_page = total_pages - 1
            
            # Get current page data
            current_page_num = st.session_state.current_page
            if current_page_num not in st.session_state.split_data:
                st.session_state.split_data[current_page_num] = []
            
            splits = st.session_state.split_data[current_page_num]
            
            # Get page dimensions
            current_page = pdf_reader.pages[current_page_num]
            page_width = current_page.mediabox.width
            page_height = current_page.mediabox.height
            st.session_state.page_width = page_width
            
            # Page navigation
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if st.button("← Previous Page", key="prev_btn") and st.session_state.current_page > 0:
                    st.session_state.navigation = 'prev'
                    st.rerun()
            
            with col2:
                st.markdown(f"**Page {st.session_state.current_page + 1} of {total_pages}**")
                st.markdown("*Use buttons or arrow keys in the image below*")
            
            with col3:
                if st.button("Next Page →", key="next_btn") and st.session_state.current_page < total_pages - 1:
                    st.session_state.navigation = 'next'
                    st.rerun()
            
            # Display current splits
            st.markdown(f"**Current splits on this page: {len(splits)}**")
            if splits:
                st.write(f"Split positions (X-coordinates): {sorted([round(x, 1) for x in splits])}")
            
            # Convert current page to image for display
            base64_img = get_page_image(pdf_reader, current_page_num)
            
            # Create the interactive image component
            st.markdown("""
            <style>
            .split-line {
                position: absolute;
                top: 0;
                bottom: 0;
                width: 3px;
                background-color: #ff0000;
                pointer-events: none;
                z-index: 10;
            }
            .page-container {
                position: relative;
                display: inline-block;
                cursor: crosshair;
                border: 2px solid #ccc;
                margin: 10px 0;
            }
            .click-instruction {
                color: #666;
                font-style: italic;
                margin-bottom: 10px;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Create HTML for image with split lines
            split_lines_html = ""
            for split_x in splits:
                # Convert PDF coordinate to image coordinate
                img_x = (split_x / page_width) * 100
                split_lines_html += f'<div class="split-line" style="left: {img_x}%;"></div>'
            
            st.markdown('<div class="click-instruction">Click on the image below to add vertical split lines. Use arrow keys in the image area to navigate.</div>', unsafe_allow_html=True)
            
            # Create forms for handling clicks and navigation
            with st.form("click_form", clear_on_submit=True):
                # Hidden input for coordinates
                click_x = st.number_input("Click X Coordinate", min_value=0.0, max_value=float(page_width), value=0.0, format="%.2f", key="click_input", label_visibility="collapsed")
                submitted_click = st.form_submit_button("Add Split at Click Position", use_container_width=True)
                if submitted_click and click_x > 0:
                    st.session_state.click_coord = click_x
                    st.rerun()
            
            with st.form("nav_form", clear_on_submit=True):
                # Hidden navigation
                nav_action = st.selectbox("Navigation", ["stay", "prev", "next"], index=0, key="nav_select", label_visibility="collapsed")
                submitted_nav = st.form_submit_button("Apply Navigation", use_container_width=True)
                if submitted_nav and nav_action in ["prev", "next"]:
                    st.session_state.navigation = nav_action
                    st.rerun()
            
            # Display the image with JavaScript for interaction
            html_code = f"""
            <div class="page-container" id="pageContainer">
                <img src="data:image/png;base64,{base64_img}" 
                     style="max-width: 100%; height: auto; display: block;" 
                     onclick="handleClick(event)" 
                     id="pageImage"
                     tabindex="0">
                {split_lines_html}
            </div>
            
            <script>
            function handleClick(event) {{
                const img = event.currentTarget;
                const rect = img.getBoundingClientRect();
                const clickX = event.clientX - rect.left;
                const imgWidth = rect.width;
                const xPercent = (clickX / imgWidth) * 100;
                
                // Convert to PDF coordinates
                const pdfX = (xPercent / 100) * {page_width};
                
                // Update the hidden input field
                const clickInput = window.parent.document.querySelector('input[type="number"]');
                if (clickInput) {{
                    clickInput.value = pdfX.toFixed(2);
                    // Trigger change event
                    const event = new Event('input', {{ bubbles: true }});
                    clickInput.dispatchEvent(event);
                }}
                
                // Show feedback
                alert(`Split line added at X = ${{pdfX.toFixed(1)}}`);
            }}
            
            // Arrow key navigation
            document.addEventListener('keydown', function(event) {{
                const img = document.getElementById('pageImage');
                if (img && document.activeElement === img) {{
                    if (event.key === 'ArrowLeft') {{
                        // Update navigation select
                        const navSelect = window.parent.document.querySelector('select');
                        if (navSelect) {{
                            navSelect.value = 'prev';
                            const event = new Event('change', {{ bubbles: true }});
                            navSelect.dispatchEvent(event);
                        }}
                    }} else if (event.key === 'ArrowRight') {{
                        // Update navigation select
                        const navSelect = window.parent.document.querySelector('select');
                        if (navSelect) {{
                            navSelect.value = 'next';
                            const event = new Event('change', {{ bubbles: true }});
                            navSelect.dispatchEvent(event);
                        }}
                    }}
                }}
            }});
            
            // Focus the image for keyboard events
            window.addEventListener('load', function() {{
                const img = document.getElementById('pageImage');
                if (img) {{
                    img.focus();
                }}
            }});
            </script>
            """
            
            # Display the interactive component
            st.components.v1.html(html_code, height=500)
            
            # Control buttons
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("🧹 Clear Splits on This Page", use_container_width=True):
                    st.session_state.split_data[current_page_num] = []
                    st.rerun()
            
            with col_b:
                if st.button("🗑️ Clear All Splits", use_container_width=True):
                    st.session_state.split_data = {}
                    st.rerun()
            
            # Page summary
            st.markdown("### Page Summary")
            for page_num in range(total_pages):
                splits_count = len(st.session_state.split_data.get(page_num, []))
                status = "✅" if splits_count > 0 else "⏳"
                current_indicator = "📍" if page_num == current_page_num else ""
                st.write(f"{status} {current_indicator} Page {page_num + 1}: {splits_count} splits")
            
            # Download section
            st.markdown("---")
            st.subheader("Download Split PDF")
            
            if st.button("🛠️ Generate Split PDF", type="primary"):
                with st.spinner("Creating split PDF..."):
                    try:
                        uploaded_file.seek(0)
                        pdf_reader = pypdf.PdfReader(uploaded_file)
                        output_pdf = create_split_pdf(pdf_reader, st.session_state.split_data)
                        
                        # Save to bytes
                        output_buffer = io.BytesIO()
                        output_pdf.write(output_buffer)
                        output_buffer.seek(0)
                        
                        st.success("✅ PDF split successfully!")
                        
                        # Download button
                        st.download_button(
                            label="📥 Download Split PDF",
                            data=output_buffer,
                            file_name="split_document.pdf",
                            mime="application/pdf",
                            type="primary"
                        )
                    except Exception as e:
                        st.error(f"❌ Error generating PDF: {str(e)}")
                        
        except Exception as e:
            st.error(f"Error processing PDF: {str(e)}")
    
    else:
        st.info("📁 Please upload a PDF file to get started.")
        st.markdown("""
        **Features:**
        - 🖱️ Click on the PDF page to add vertical split lines
        - ⌨️ Use arrow keys (← →) for navigation  
        - 📄 Each page can have different split configurations
        - 💾 Download the final split PDF
        """)

if __name__ == "__main__":
    main()
