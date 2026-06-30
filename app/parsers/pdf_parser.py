import fitz  # PyMuPDF

from parsers.base_parser import BaseParser
from models.parser import ParserOutput
from utils.logger import logger
from utils.exceptions import ParserError


class PDFParser(BaseParser):

    def parse(self, file_path: str) -> ParserOutput:
        try:
            logger.info(f"Parsing PDF file: {file_path}")

            text = ""
            geometric_links = []

            with fitz.open(file_path) as doc:
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    text += str(page.get_text("text")) + "\n"
                    
                    # Extract geometric links
                    links = page.get_links()
                    for link in links:
                        uri = link.get("uri")
                        if uri:
                            rect = link.get("from")
                            # get_text("words") returns list of (x0, y0, x1, y1, word, block_no, line_no, word_no)
                            words = page.get_text("words")
                            anchor_text = []
                            for w in words:
                                w_rect = fitz.Rect(w[:4])
                                if w_rect.intersects(rect):
                                    anchor_text.append(w[4])
                            geometric_links.append({
                                "text_anchor": " ".join(anchor_text),
                                "url": uri
                            })

            return ParserOutput(
                source="resume_pdf",
                source_type="unstructured",
                content=text,
                metadata={"geometric_links": geometric_links}
            )

        except Exception as e:
            logger.error(f"PDF parsing failed: {str(e)}")
            raise ParserError(str(e))
