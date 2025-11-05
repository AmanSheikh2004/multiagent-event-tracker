# PaddleOCR-based OCR Agent
from paddleocr import PaddleOCR
ocr_model = PaddleOCR(use_angle_cls=True, lang='en')

class OcrAgent:
    def __init__(self):
        self.model = ocr_model

    def process(self, data):
        path = data.get('file_path')
        result_text = []
        try:
            res = self.model.ocr(path, cls=True)
            for line in res:
                for box, txt, score in line:
                    result_text.append(txt)
        except Exception as e:
            result_text = []
        return {'raw_text': '\n'.join(result_text)}
