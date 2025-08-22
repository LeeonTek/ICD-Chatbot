from docling.document_converter import DocumentConverter
 
pdf_path = r"file_path"
converter = DocumentConverter()
result = converter.convert(pdf_path)
 
# Export to Markdown
md_output = result.document.export_to_markdown()
with open("output_docling.md", "w", encoding="utf-8") as f:
    f.write(md_output)
 
# # Export to JSON (optional, keeps structure info)
# json_output = result.document.json()
# with open("output_docling.json", "w", encoding="utf-8") as f:
#     f.write(json_output)
 
print("✅ Docling conversion done. Check output_docling.md ")