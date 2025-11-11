import streamlit as st
import PyPDF2
import io
from datetime import datetime
import os

st.set_page_config(
    page_title="PDF Merger - Alternate Pages",
    page_icon="📄",
    layout="centered"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-msg {
        padding: 1rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.5rem;
        color: #155724;
    }
    .upload-box {
        border: 2px dashed #1f77b4;
        border-radius: 0.5rem;
        padding: 2rem;
        text-align: center;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def merge_pdfs_alternating(pdf1_file, pdf2_file):
    """Merge two PDFs with alternating pages"""
    try:
        # Create PDF reader objects
        pdf1_reader = PyPDF2.PdfReader(pdf1_file)
        pdf2_reader = PyPDF2.PdfReader(pdf2_file)
        
        # Create PDF writer object
        pdf_writer = PyPDF2.PdfWriter()
        
        # Get the maximum number of pages between both PDFs
        max_pages = max(len(pdf1_reader.pages), len(pdf2_reader.pages))
        
        # Merge pages alternately
        for i in range(max_pages):
            # Add page from first PDF if it exists
            if i < len(pdf1_reader.pages):
                pdf_writer.add_page(pdf1_reader.pages[i])
            
            # Add page from second PDF if it exists
            if i < len(pdf2_reader.pages):
                pdf_writer.add_page(pdf2_reader.pages[i])
        
        # Create a bytes buffer for the output
        output_buffer = io.BytesIO()
        pdf_writer.write(output_buffer)
        output_buffer.seek(0)
        
        return output_buffer, None
        
    except Exception as e:
        return None, str(e)

def main():
    # Header
    st.markdown('<h1 class="main-header">📄 PDF Merger - Alternate Pages</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    This app merges two PDF files by alternating their pages:
    - 1st page from PDF 1
    - 2nd page from PDF 2  
    - 3rd page from PDF 1
    - 4th page from PDF 2
    - and so on...
    """)
    
    # File upload section
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="upload-box">', unsafe_allow_html=True)
        pdf1 = st.file_uploader("Upload First PDF", type=['pdf'], key="pdf1")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col2:
        st.markdown('<div class="upload-box">', unsafe_allow_html=True)
        pdf2 = st.file_uploader("Upload Second PDF", type=['pdf'], key="pdf2")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Display file info when uploaded
    if pdf1 is not None:
        st.sidebar.success(f"📄 PDF 1: {pdf1.name}")
    
    if pdf2 is not None:
        st.sidebar.success(f"📄 PDF 2: {pdf2.name}")
    
    # Merge button and logic
    if pdf1 is not None and pdf2 is not None:
        if st.button("🔄 Merge PDFs", type="primary", use_container_width=True):
            with st.spinner("Merging PDFs with alternating pages..."):
                # Perform the merge
                merged_pdf, error = merge_pdfs_alternating(pdf1, pdf2)
                
                if error:
                    st.error(f"Error merging PDFs: {error}")
                else:
                    st.success("✅ PDFs merged successfully!")
                    
                    # Display merge statistics
                    pdf1_reader = PyPDF2.PdfReader(pdf1)
                    pdf2_reader = PyPDF2.PdfReader(pdf2)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("PDF 1 Pages", len(pdf1_reader.pages))
                    with col2:
                        st.metric("PDF 2 Pages", len(pdf2_reader.pages))
                    with col3:
                        st.metric("Merged Pages", len(pdf1_reader.pages) + len(pdf2_reader.pages))
                    
                    # Download button
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    download_filename = f"merged_alternating_{timestamp}.pdf"
                    
                    st.download_button(
                        label="📥 Download Merged PDF",
                        data=merged_pdf,
                        file_name=download_filename,
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                    st.markdown('<div class="success-msg">', unsafe_allow_html=True)
                    st.markdown("**Merge completed!** Click the download button above to get your merged PDF.")
                    st.markdown('</div>', unsafe_allow_html=True)
    
    # Instructions in sidebar
    with st.sidebar:
        st.header("ℹ️ Instructions")
        st.markdown("""
        1. Upload two PDF files
        2. Click the 'Merge PDFs' button
        3. Download your merged PDF
        
        **How pages are merged:**
        - Page 1: From PDF 1
        - Page 2: From PDF 2
        - Page 3: From PDF 1
        - Page 4: From PDF 2
        - Continues alternating...
        
        If one PDF has more pages, the extra pages will be added at the end.
        """)
        
        st.header("⚙️ Technical Info")
        st.markdown("""
        - Built with Streamlit
        - Uses PyPDF2 for PDF processing
        - Works entirely in your browser
        - No files stored on server
        """)

if __name__ == "__main__":
    main()
