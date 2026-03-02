from app.domain.interfaces import PDFParserInterface


class V1_PDFParser(PDFParserInterface):
    def parse_pdf(self, file_content: bytes) -> str:
        pass       