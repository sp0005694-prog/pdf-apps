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
            
            # Page navigation
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if st.button("← Previous Page") and st.session_state.current_page > 0:
                    st.session_state.current_page -= 1
                    st.rerun()
            
            with col2:
                st.markdown(f"**Page {st.session_state.current_page + 1} of {total_pages}**")
                st.markdown("*Use arrow keys ← → to navigate*")
            
            with col3:
                if st.button("Next Page →") and st.session_state.current_page < total_pages - 1:
                    st.session_state.current_page += 1
                    st.rerun()
            
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
            
            # Display current splits
            st.markdown(f"**Current splits on this page: {len(splits)}**")
            if splits:
                st.write(f"Split positions (X-coordinates): {sorted([round(x, 1) for x in splits])}")
            
            # Convert current page to image for display
            base64_img = get_page_image(pdf_reader, current_page_num)
            
            # Create a custom component for click handling
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
                # Convert PDF coordinate to image coordinate (assuming image width ~600px)
                img_x = (split_x / page_width) * 100
                split_lines_html += f'<div class="split-line" style="left: {img_x}%;"></div>'
            
            # Use columns for better layout
            col_left, col_right = st.columns([2, 1])
            
            with col_left:
                st.markdown('<div class="click-instruction">Click on the image below to add vertical split lines</div>', unsafe_allow_html=True)
                
                # Create the interactive image component
                html_code = f"""
                <div class="page-container" id="pageContainer">
                    <img src="data:image/png;base64,{base64_img}" 
                         style="max-width: 100%; height: auto; display: block;" 
                         onclick="handleClick(event)" 
                         id="pageImage">
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
                    
                    // Send data back to Streamlit
                    window.parent.postMessage({{
                        type: 'streamlit:setComponentValue',
                        value: pdfX.toFixed(2)
                    }}, '*');
                }}
                
                // Arrow key navigation
                document.addEventListener('keydown', function(event) {{
                    if (event.key === 'ArrowLeft') {{
                        window.parent.postMessage({{
                            type: 'streamlit:setComponentValue',
                            value: 'NAV_PREV'
                        }}, '*');
                    }} else if (event.key === 'ArrowRight') {{
                        window.parent.postMessage({{
                            type: 'streamlit:setComponentValue',
                            value: 'NAV_NEXT'
                        }}, '*');
                    }}
                }});
                
                // Focus handling for arrow keys
                window.addEventListener('load', function() {{
                    const img = document.getElementById('pageImage');
                    if (img) {{
                        img.focus();
                    }}
                }});
                </script>
                """
                
                # Use components.v1.html for the interactive part
                result = st.components.v1.html(html_code, height=500, scrolling=False)
                
                # Handle the result from JavaScript
                if result is not None:
                    if result == 'NAV_PREV' and st.session_state.current_page > 0:
                        st.session_state.current_page -= 1
                        st.rerun()
                    elif result == 'NAV_NEXT' and st.session_state.current_page < total_pages - 1:
                        st.session_state.current_page += 1
                        st.rerun()
                    else:
                        try:
                            # It's a click coordinate
                            new_split = float(result)
                            if new_split >= 0 and new_split <= page_width:
                                if new_split not in st.session_state.split_data[current_page_num]:
                                    st.session_state.split_data[current_page_num].append(new_split)
                                    st.rerun()
                        except ValueError:
                            pass
            
            with col_right:
                st.markdown("### Controls")
                
                # Split management
                if st.button("🧹 Clear Splits on This Page", use_container_width=True):
                    st.session_state.split_data[current_page_num] = []
                    st.rerun()
                
                if st.button("🗑️ Clear All Splits", use_container_width=True):
                    st.session_state.split_data = {}
                    st.rerun()
                
                st.markdown("---")
                st.markdown("### Page Summary")
                for page_num in range(total_pages):
                    splits_count = len(st.session_state.split_data.get(page_num, []))
                    status = "✅" if splits_count > 0 else "⏳"
                    st.write(f"{status} Page {page_num + 1}: {splits_count} splits")
            
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
