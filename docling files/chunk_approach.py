from docling.document_converter import DocumentConverter
import fitz  # PyMuPDF
import os
import time
 
# pdf_path = r"singlePageIcd.pdf"
# pdf_path = r"21_splitted_1_splitted_2025_ICD_NEW[5].pdf"
pdf_path = r"C:\Users\Tamil\Documents\LeeonTek Projects\splitted icd document\New folder\new folder\singlePageIcd.pdf"

start_time = time.time()
 
 
output_md = "output_chunk_docling.md"
chunk_size = 50  # number of pages per chunk

pdf_doc = fitz.open(pdf_path)
total_pages = len(pdf_doc)
 
converter = DocumentConverter()
all_md = []
 
# Create temp folder for chunks (optional)
os.makedirs("temp_chunks", exist_ok=True)
 
# Process PDF in chunks
for start in range(0, total_pages, chunk_size):
    end = min(start + chunk_size - 1, total_pages - 1)  # zero-indexed
    print(f"Processing pages {start+1} to {end+1}...")
 
    # Create a temporary PDF chunk
    chunk_pdf_path = f"temp_chunks/chunk_{start+1}_{end+1}.pdf"
    chunk_doc = fitz.open()
    chunk_doc.insert_pdf(pdf_doc, from_page=start, to_page=end)
    chunk_doc.save(chunk_pdf_path)
    chunk_doc.close()
 
    # Convert chunk with Docling
    result = converter.convert(chunk_pdf_path)
    chunk_md = result.document.export_to_markdown()
    all_md.append(chunk_md)
 
# Combine all chunks into a single Markdown file
with open(output_md, "w", encoding="utf-8") as f:
    f.write("\n\n".join(all_md))
 
end_time = time.time()
 
print(f"✅ Conversion completed in {end_time - start_time:.2f} seconds")
print(f"✅ Docling conversion done. Markdown saved to {output_md}")