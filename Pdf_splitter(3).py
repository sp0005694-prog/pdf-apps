import streamlit as st
import pypdf
import io
import base64
import fitz  # PyMuPDF
from pypdf import PdfReader, PdfWriter, PageObject
import math

def create_split_pdf(original_pdf, split_data):
    """Create a new PDF with horizontal splits based on user clicks"""
    output_pdf = PdfWriter()
    
    for page_num in range(len(original_pdf.pages)):
        splits = split_data.get(page_num, [])
        original_page = original_pdf.pages[page_num]
        
        if splits:  # If splits exist for this page
            # Sort splits and add boundaries
            sorted_splits = sorted(splits)
            all_splits = [0] + sorted_splits + [original_page.mediabox.width]
            
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
                # We need to shift the content to the left by the left margin
                new_page.merge_transformed_page(
                    original_page,
                    ctm=(1, 0, 0, 1, -left, 0)
                )
                output_pdf.add_page(new_page)
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
    
    st.title("📄 PDF Horizontal Splitter")
    st.markdown("""
    **Instructions:**
    1. Upload a PDF file
    2. Click on the page image to add vertical split lines
    3. Use **← → buttons** to navigate between pages
    4. Download the split PDF when done
    """)
    
    # Initialize session state
    if 'split_data' not in st.session_state:
        st.session_state.split_data = {}
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 0
    if 'uploaded_pdf' not in st.session_state:
        st.session_state.uploaded_pdf = None

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
            
            with col3:
                if st.button("Next Page →") and current_page_num < total_pages - 1:
                    st.session_state.current_page += 1
                    st.rerun()
            
            # Get current page data
            if current_page_num not in st.session_state.split_data:
                st.session_state.split_data[current_page_num] = []
            
            splits = st.session_state.split_data[current_page_num]
            current_page = pdf_reader.pages[current_page_num]
            page_width = current_page.mediabox.width
            
            # Display current splits
            st.markdown(f"**Current splits on this page: {len(splits)}**")
            if splits:
                st.write(f"Split positions: {sorted([round(x, 1) for x in splits])}")
                st.write(f"This will create {len(splits) + 1} vertical segments")
            
            # Convert current page to image for display
            base64_img = get_page_image(pdf_reader, current_page_num)
            
            # Create the interactive image
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
            </style>
            """, unsafe_allow_html=True)
            
            # Create HTML for image with split lines
            split_lines_html = ""
            for split_x in splits:
                img_x = (split_x / page_width) * 100
                split_lines_html += f'<div class="split-line" style="left: {img_x}%;"></div>'
            
            # Display clickable image
            st.markdown("**Click on the image below to add vertical split lines:**")
            
            # Use a form to capture clicks
            with st.form(f"click_form_{current_page_num}"):
                # Hidden field for click coordinates
                click_x = st.number_input(
                    "X Coordinate", 
                    min_value=0.0, 
                    max_value=float(page_width), 
                    value=0.0, 
                    key=f"click_x_{current_page_num}",
                    label_visibility="collapsed"
                )
                
                # JavaScript to handle clicks and update the form
                html_code = f"""
                <div class="page-container">
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
                    const pdfX = (xPercent / 100) * {page_width};
                    
                    // Find the number input and update its value
                    const numberInput = window.parent.document.querySelector('input[type="number"][step="0.01"]');
                    if (numberInput) {{
                        numberInput.value = pdfX.toFixed(2);
                        // Trigger change event
                        const event = new Event('input', {{ bubbles: true }});
                        numberInput.dispatchEvent(event);
                    }}
                }}
                </script>
                """
                
                st.components.v1.html(html_code, height=500)
                
                col1, col2 = st.columns(2)
                with col1:
                    add_split = st.form_submit_button("➕ Add Split at Click Position")
                with col2:
                    clear_splits = st.form_submit_button("🧹 Clear Splits on This Page")
            
            # Handle form submissions
            if add_split and click_x > 0:
                if click_x not in st.session_state.split_data[current_page_num]:
                    st.session_state.split_data[current_page_num].append(click_x)
                st.rerun()
            
            if clear_splits:
                st.session_state.split_data[current_page_num] = []
                st.rerun()
            
            # Control buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Clear All Splits in Document"):
                    st.session_state.split_data = {}
                    st.rerun()
            
            # Show split summary for all pages
            st.markdown("### Split Summary")
            for page_num in range(total_pages):
                page_splits = st.session_state.split_data.get(page_num, [])
                segments = len(page_splits) + 1
                status = "✅" if page_splits else "⏳"
                current = "📍" if page_num == current_page_num else ""
                st.write(f"{status} {current} Page {page_num + 1}: {len(page_splits)} splits → {segments} segments")
            
            # Download section
            st.markdown("---")
            st.subheader("Download Split PDF")
            
            if st.button("🛠️ Generate Split PDF", type="primary"):
                with st.spinner("Creating split PDF..."):
                    try:
                        # Reset file pointer and recreate reader
                        uploaded_file.seek(0)
                        pdf_reader = PdfReader(uploaded_file)
                        
                        # Create the split PDF
                        output_pdf = create_split_pdf(pdf_reader, st.session_state.split_data)
                        
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
                            type="primary"
                        )
                        
                    except Exception as e:
                        st.error(f"❌ Error generating PDF: {str(e)}")
                        st.info("This might be due to PDF encryption or compatibility issues.")
                        
        except Exception as e:
            st.error(f"Error processing PDF: {str(e)}")
    
    else:
        st.info("📁 Please upload a PDF file to get started.")

if __name__ == "__main__":
    main()
