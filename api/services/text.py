from PyPDF2 import PdfReader
from langchain_text_splitters import CharacterTextSplitter

class TextService:
  def __init__(self):
    pass

  def get_pdf_text_chunks(self, pdf_doc):
    text_splitter = CharacterTextSplitter(
      separator="\n",
      chunk_size=1000,
      chunk_overlap=200,
      length_function=len
    )
    
    pdf_reader = PdfReader(pdf_doc)
    text = ""
    for page in pdf_reader.pages:
      text += page.extract_text() or ""
    
    chunks = text_splitter.split_text(text)
      
    return chunks