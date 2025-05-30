from PyPDF2 import PdfReader
from langchain_text_splitters import CharacterTextSplitter

class TextService:
  def __init__(self):
    pass

  def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
      pdf_reader = PdfReader(pdf)
      for page in pdf_reader.pages:
        text += page.extract_text()

    return text

  def get_text_chunks(raw_text):
    text_splitter = CharacterTextSplitter(
      separator = "\n",
      chunk_size=1000,
      chunk_overlap=200,
      length_function=len
    )
    chunks = text_splitter.split_text(raw_text)
    return chunks

