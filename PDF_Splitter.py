import streamlit as st
import PyPDF2
import io
from PIL import Image
import base64
import tempfile
import os

def create_split_pdf(original_pdf, split_data):
    """Create a new PDF with horizontal splits based on user clicks"""
    output_pdf = PyPDF2.PdfWriter()
    
    for page_num, splits in enumerate(split_data):
        if splits:  # If splits exist for this page
            original_page = original_pdf.pages[page_num]
            page_width = original_page.mediabox.width
            page_height = original_page.mediabox.height
            
            # Sort splits and add boundaries
            sorted_splits = sorted(splits)
            all_splits = [0] + sorted_splits + [page_width]
            
            # Create subpages for each segment
            for i in range(len(all_splits) - 1):
                left = all_splits[i]
                right = all_splits[i + 1]
                
                # Create new page with the segment
                new_page = PyPDF2.PageObject.create_blank_page(
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
            output_pdf.add_page(original_pdf.pages[page_num])
    
    return output_pdf

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
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
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
            
            with col3:
                if st.button("Next Page →") and st.session_state.current_page < total_pages - 1:
                    st.session_state.current_page += 1
                    st.rerun()
            
            # Get current page data
            current_page_num = st.session_state.current_page
            if current_page_num not in st.session_state.split_data:
                st.session_state.split_data[current_page_num] = []
            
            splits = st.session_state.split_data[current_page_num]
            
            # Display current splits
            st.markdown(f"**Current splits on this page: {len(splits)}**")
            if splits:
                st.write(f"Split positions (X-coordinates): {sorted(splits)}")
            
            # Convert current page to image for display
            current_page = pdf_reader.pages[current_page_num]
            
            # Create a temporary PDF with just this page
            temp_pdf = PyPDF2.PdfWriter()
            temp_pdf.add_page(current_page)
            
            temp_pdf_bytes = io.BytesIO()
            temp_pdf.write(temp_pdf_bytes)
            temp_pdf_bytes.seek(0)
            
            # Convert PDF page to base64 for display
            import fitz  # PyMuPDF
            doc = fitz.open("pdf", temp_pdf_bytes.read())
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Higher resolution
            img_data = pix.tobytes("png")
            doc.close()
            
            base64_img = base64.b64encode(img_data).decode()
            page_width = current_page.mediabox.width
            page_height = current_page.mediabox.height
            
            # Display clickable image with split lines
            st.markdown("""
            <style>
            .split-line {
                position: absolute;
                top: 0;
                bottom: 0;
                width: 2px;
                background-color: red;
                pointer-events: none;
            }
            .page-container {
                position: relative;
                display: inline-block;
                cursor: crosshair;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Create HTML for image with split lines
            split_lines_html = ""
            for split_x in splits:
                # Convert PDF coordinate to image coordinate
                img_x = (split_x / page_width) * 100
                split_lines_html += f'<div class="split-line" style="left: {img_x}%;"></div>'
            
            html_code = f"""
            <div class="page-container" id="pageContainer">
                <img src="data:image/png;base64,{base64_img}" 
                     style="max-width: 800px; border: 2px solid #ccc;" 
                     onclick="handleClick(event)" 
                     id="pageImage">
                {split_lines_html}
            </div>
            <script>
            function handleClick(event) {{
                const img = event.currentTarget;
                const rect = img.getBoundingClientRect();
                const x = event.clientX - rect.left;
                const xPercent = (x / rect.width) * 100;
                
                // Send click data to Streamlit
                const data = {{
                    x: x,
                    percent: xPercent,
                    pageX: (xPercent / 100) * {page_width}
                }};
                
                window.parent.postMessage({{
                    type: 'streamlit:setComponentValue',
                    value: JSON.stringify(data)
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
            </script>
            """
            
            # Handle clicks and navigation
            click_data = st.components.v1.html(html_code, height=600)
            
            if click_data:
                if click_data == "NAV_PREV" and st.session_state.current_page > 0:
                    st.session_state.current_page -= 1
                    st.rerun()
                elif click_data == "NAV_NEXT" and st.session_state.current_page < total_pages - 1:
                    st.session_state.current_page += 1
                    st.rerun()
                else:
                    try:
                        data = eval(click_data)
                        if 'pageX' in data:
                            new_split = data['pageX']
                            st.session_state.split_data[current_page_num].append(new_split)
                            st.session_state.split_data[current_page_num] = list(set(st.session_state.split_data[current_page_num]))  # Remove duplicates
                            st.rerun()
                    except:
                        pass
            
            # Split management
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Clear Splits on This Page"):
                    st.session_state.split_data[current_page_num] = []
                    st.rerun()
            
            with col_b:
                if st.button("Clear All Splits"):
                    st.session_state.split_data = {}
                    st.rerun()
            
            # Download section
            st.markdown("---")
            st.subheader("Download Split PDF")
            
            if st.button("Generate Split PDF"):
                with st.spinner("Creating split PDF..."):
                    try:
                        uploaded_file.seek(0)  # Reset file pointer
                        pdf_reader = PyPDF2.PdfReader(uploaded_file)
                        output_pdf = create_split_pdf(pdf_reader, st.session_state.split_data)
                        
                        # Save to bytes
                        output_buffer = io.BytesIO()
                        output_pdf.write(output_buffer)
                        output_buffer.seek(0)
                        
                        st.success("PDF split successfully!")
                        
                        # Download button
                        st.download_button(
                            label="📥 Download Split PDF",
                            data=output_buffer,
                            file_name="split_document.pdf",
                            mime="application/pdf"
                        )
                    except Exception as e:
                        st.error(f"Error generating PDF: {str(e)}")
            
            # Show summary
            st.markdown("### Split Summary")
            summary_data = []
            for page_num in range(total_pages):
                splits_count = len(st.session_state.split_data.get(page_num, []))
                summary_data.append(f"Page {page_num + 1}: {splits_count} splits → {splits_count + 1} segments")
            
            for summary in summary_data:
                st.write(summary)
                        
        except Exception as e:
            st.error(f"Error processing PDF: {str(e)}")
            st.info("Make sure you have PyMuPDF installed: `pip install PyMuPDF`")
    
    else:
        st.info("Please upload a PDF file to get started.")
        st.markdown("""
        **Features:**
        - Click on the PDF page to add vertical split lines
        - Use mouse or arrow keys for navigation
        - Each page can have different split configurations
        - Download the final split PDF
        """)

if __name__ == "__main__":
    main()
