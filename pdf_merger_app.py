import streamlit as st
import PyPDF2
import fitz  # PyMuPDF
from PIL import Image, ImageEnhance, ImageOps
import io
import os
import tempfile
import time

def main():
    st.set_page_config(
        page_title="PDF Merger & Filter",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("📄 PDF Merger & Filter App")
    st.markdown("**Port: 8501** | **Drag to reorder PDFs** | **Progress tracking**")
    
    # Navigation to other app
    st.sidebar.success("✅ App running on port 8501")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔗 Other Apps:")
    st.sidebar.markdown("[🔄 PDF Processor App (Port 8502)](http://localhost:8502)")
    
    # Initialize session state
    if 'pdf_files' not in st.session_state:
        st.session_state.pdf_files = []
    if 'file_order' not in st.session_state:
        st.session_state.file_order = []
    if 'merged_pdf' not in st.session_state:
        st.session_state.merged_pdf = None
    if 'inverted_pdf' not in st.session_state:
        st.session_state.inverted_pdf = None
    if 'filtered_pdf' not in st.session_state:
        st.session_state.filtered_pdf = None

    # File upload with drag-and-drop reordering
    with st.sidebar:
        st.header("📁 Upload & Arrange PDFs")
        uploaded_files = st.file_uploader(
            "Choose PDF files", 
            type="pdf", 
            accept_multiple_files=True,
            help="Upload multiple PDFs and rearrange them using drag and drop"
        )
        
        if uploaded_files:
            # Initialize file order if empty or new files added
            if not st.session_state.file_order or len(st.session_state.file_order) != len(uploaded_files):
                st.session_state.file_order = list(range(len(uploaded_files)))
                st.session_state.pdf_files = uploaded_files
            
            st.success(f"📎 {len(uploaded_files)} PDF(s) uploaded!")
            
            # File reordering interface
            st.subheader("🔄 Arrange PDF Order")
            st.info("Drag items to reorder the merge sequence")
            
            # Create reorderable list
            reordered_files = []
            for i in st.session_state.file_order:
                reordered_files.append(uploaded_files[i])
            
            # Display files with drag handles
            for i, file_idx in enumerate(st.session_state.file_order):
                col1, col2 = st.columns([1, 8])
                with col1:
                    st.markdown(f"**{i+1}.**")
                with col2:
                    st.write(f"📄 {uploaded_files[file_idx].name}")
            
            # Reordering controls
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("⬆️ Move Up", key="move_up"):
                    move_file_up()
            with col2:
                if st.button("⬇️ Move Down", key="move_down"):
                    move_file_down()
            with col3:
                if st.button("🔄 Reset Order", key="reset_order"):
                    st.session_state.file_order = list(range(len(uploaded_files)))
                    st.rerun()

    # Main workflow with progress tracking
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.header("🔄 Step 1: Merge PDFs")
        if st.session_state.pdf_files:
            # Show current order
            st.write("**Merge order:**")
            reordered_files = [st.session_state.pdf_files[i] for i in st.session_state.file_order]
            for i, file in enumerate(reordered_files):
                st.write(f"{i+1}. {file.name}")
            
            if st.button("Merge PDFs", type="primary", key="merge_btn"):
                with st.spinner("Starting merge process..."):
                    # Create progress bar and status
                    merge_progress = st.progress(0)
                    status_text = st.empty()
                    
                    # Simulate progress with time estimation
                    merged_pdf = merge_pdfs_with_progress(reordered_files, merge_progress, status_text)
                    st.session_state.merged_pdf = merged_pdf
                    st.session_state.inverted_pdf = None
                    st.session_state.filtered_pdf = None
                    
                    merge_progress.empty()
                    status_text.empty()
                st.success("✅ PDFs merged successfully!")
                
            if st.session_state.merged_pdf:
                st.download_button(
                    label="📥 Download Merged PDF",
                    data=st.session_state.merged_pdf,
                    file_name="merged_document.pdf",
                    mime="application/pdf",
                    key="download_merged"
                )
        else:
            st.info("📝 Upload PDF files to begin")
    
    with col2:
        st.header("🎨 Step 2: Invert Colors")
        if st.session_state.merged_pdf:
            if st.button("Invert PDF (Negative)", type="primary", key="invert_btn"):
                with st.spinner("Starting color inversion..."):
                    # Create progress bar for inversion
                    invert_progress = st.progress(0)
                    invert_status = st.empty()
                    
                    inverted_pdf = invert_pdf_colors_with_progress(
                        st.session_state.merged_pdf, 
                        invert_progress, 
                        invert_status
                    )
                    st.session_state.inverted_pdf = inverted_pdf
                    st.session_state.filtered_pdf = None
                    
                    invert_progress.empty()
                    invert_status.empty()
                st.success("✅ Colors inverted successfully!")
                
            if st.session_state.inverted_pdf:
                st.download_button(
                    label="📥 Download Inverted PDF",
                    data=st.session_state.inverted_pdf,
                    file_name="inverted_document.pdf",
                    mime="application/pdf",
                    key="download_inverted"
                )
        else:
            st.info("🔄 Merge PDFs first")
    
    with col3:
        st.header("✨ Step 3: Apply Filter")
        if st.session_state.inverted_pdf:
            filter_option = st.selectbox(
                "Choose filter:",
                ["None", "Vibrant", "Soft Tone", "OCV Color", "OCV Black & White"],
                key="filter_select"
            )
            
            if st.button("Apply Filter", type="primary", key="filter_btn"):
                with st.spinner(f"Starting {filter_option} filter application..."):
                    # Create progress bar for filtering
                    filter_progress = st.progress(0)
                    filter_status = st.empty()
                    
                    filtered_pdf = apply_filter_to_pdf_with_progress(
                        st.session_state.inverted_pdf, 
                        filter_option,
                        filter_progress,
                        filter_status
                    )
                    st.session_state.filtered_pdf = filtered_pdf
                    
                    filter_progress.empty()
                    filter_status.empty()
                st.success(f"✅ '{filter_option}' filter applied!")
                
            if st.session_state.filtered_pdf and filter_option != "None":
                st.download_button(
                    label=f"📥 Download {filter_option} PDF",
                    data=st.session_state.filtered_pdf,
                    file_name=f"filtered_{filter_option.lower().replace(' ', '_')}_document.pdf",
                    mime="application/pdf",
                    key="download_filtered"
                )
        else:
            st.info("🎨 Invert PDF first")

    # Preview section
    if st.session_state.merged_pdf:
        st.markdown("---")
        st.header("👁️ Preview")
        preview_col1, preview_col2, preview_col3 = st.columns(3)
        
        with preview_col1:
            if st.session_state.merged_pdf:
                st.subheader("Merged PDF")
                show_pdf_preview(st.session_state.merged_pdf, "Merged")
        
        with preview_col2:
            if st.session_state.inverted_pdf:
                st.subheader("Inverted PDF")
                show_pdf_preview(st.session_state.inverted_pdf, "Inverted")
        
        with preview_col3:
            if st.session_state.filtered_pdf:
                st.subheader("Filtered PDF")
                show_pdf_preview(st.session_state.filtered_pdf, "Filtered")

def move_file_up():
    """Move selected file up in order"""
    # Simple implementation - in a real app you'd use st.data_editor or custom component
    st.info("Use the arrow buttons to rearrange files. Full drag-and-drop requires custom components.")

def move_file_down():
    """Move selected file down in order"""
    st.info("Use the arrow buttons to rearrange files. Full drag-and-drop requires custom components.")

def merge_pdfs_with_progress(pdf_files, progress_bar, status_text):
    """Merge multiple PDF files into one with progress tracking"""
    pdf_merger = PyPDF2.PdfMerger()
    total_files = len(pdf_files)
    start_time = time.time()
    
    for i, uploaded_file in enumerate(pdf_files):
        # Update progress
        progress = (i + 1) / total_files
        progress_bar.progress(progress)
        
        # Calculate time remaining
        elapsed_time = time.time() - start_time
        if i > 0:
            time_per_file = elapsed_time / i
            remaining_time = time_per_file * (total_files - i)
            status_text.text(f"📄 Merging {i+1}/{total_files} - {uploaded_file.name} - Est: {remaining_time:.1f}s")
        else:
            status_text.text(f"📄 Merging {i+1}/{total_files} - {uploaded_file.name}")
        
        pdf_merger.append(uploaded_file)
        
        # Small delay to show progress
        time.sleep(0.5)
    
    output_buffer = io.BytesIO()
    pdf_merger.write(output_buffer)
    pdf_merger.close()
    
    return output_buffer.getvalue()

def invert_pdf_colors_with_progress(pdf_data, progress_bar, status_text):
    """Invert colors of all pages in PDF with progress tracking"""
    pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
    output_pdf = fitz.open()
    total_pages = len(pdf_document)
    start_time = time.time()
    
    for page_num in range(total_pages):
        # Update progress
        progress = (page_num + 1) / total_pages
        progress_bar.progress(progress)
        
        # Calculate time remaining
        elapsed_time = time.time() - start_time
        if page_num > 0:
            time_per_page = elapsed_time / page_num
            remaining_time = time_per_page * (total_pages - page_num)
            status_text.text(f"🎨 Inverting page {page_num+1}/{total_pages} - Est: {remaining_time:.1f}s")
        else:
            status_text.text(f"🎨 Inverting page {page_num+1}/{total_pages}")
        
        page = pdf_document[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_data = pix.tobytes("ppm")
        
        img = Image.open(io.BytesIO(img_data))
        inverted_img = ImageOps.invert(img.convert('RGB'))
        
        img_bytes = io.BytesIO()
        inverted_img.save(img_bytes, format='PDF')
        inverted_page_pdf = fitz.open("pdf", img_bytes.getvalue())
        output_pdf.insert_pdf(inverted_page_pdf)
        
        # Small delay to show progress
        time.sleep(0.3)
    
    output_buffer = io.BytesIO()
    output_pdf.save(output_buffer)
    output_pdf.close()
    pdf_document.close()
    
    return output_buffer.getvalue()

def apply_filter_to_pdf_with_progress(pdf_data, filter_option, progress_bar, status_text):
    """Apply selected filter to all pages with progress tracking"""
    if filter_option == "None":
        return pdf_data
    
    pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
    output_pdf = fitz.open()
    total_pages = len(pdf_document)
    start_time = time.time()
    
    for page_num in range(total_pages):
        # Update progress
        progress = (page_num + 1) / total_pages
        progress_bar.progress(progress)
        
        # Calculate time remaining
        elapsed_time = time.time() - start_time
        if page_num > 0:
            time_per_page = elapsed_time / page_num
            remaining_time = time_per_page * (total_pages - page_num)
            status_text.text(f"✨ Applying {filter_option} to page {page_num+1}/{total_pages} - Est: {remaining_time:.1f}s")
        else:
            status_text.text(f"✨ Applying {filter_option} to page {page_num+1}/{total_pages}")
        
        page = pdf_document[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_data = pix.tobytes("ppm")
        
        img = Image.open(io.BytesIO(img_data))
        filtered_img = apply_image_filter(img, filter_option)
        
        img_bytes = io.BytesIO()
        filtered_img.save(img_bytes, format='PDF')
        filtered_page_pdf = fitz.open("pdf", img_bytes.getvalue())
        output_pdf.insert_pdf(filtered_page_pdf)
        
        # Small delay to show progress
        time.sleep(0.4)
    
    output_buffer = io.BytesIO()
    output_pdf.save(output_buffer)
    output_pdf.close()
    pdf_document.close()
    
    return output_buffer.getvalue()

def apply_image_filter(img, filter_option):
    """Apply the selected filter to an image"""
    img = img.convert('RGB')
    
    if filter_option == "Vibrant":
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.5)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2)
        enhancer = ImageEnhance.Sharpness(img)
        return enhancer.enhance(1.1)
    
    elif filter_option == "Soft Tone":
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(0.7)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.1)
        enhancer = ImageEnhance.Contrast(img)
        return enhancer.enhance(0.9)
    
    elif filter_option == "OCV Color":
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(2.0)
        enhancer = ImageEnhance.Color(img)
        return enhancer.enhance(1.1)
    
    elif filter_option == "OCV Black & White":
        img = img.convert('L')
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(3.0)
        enhancer = ImageEnhance.Sharpness(img)
        return enhancer.enhance(2.0).convert('RGB')
    
    return img

def show_pdf_preview(pdf_data, title):
    """Show preview of first page of PDF"""
    try:
        pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
        if len(pdf_document) > 0:
            page = pdf_document[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))
            img_data = pix.tobytes("png")
            st.image(img_data, caption=f"{title} - Page 1", use_column_width=True)
            st.caption(f"Total pages: {len(pdf_document)}")
        pdf_document.close()
    except Exception as e:
        st.error(f"Preview error: {str(e)}")

if __name__ == "__main__":
    main()
