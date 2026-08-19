import os

import win32com.client

from .docx import extract_docx

USE_WORD_COM = os.name == "nt" 

def extract_doc(path: str) -> dict:
   
    if not USE_WORD_COM:
        return {"text": "", "method": "doc_unsupported_platform", "n_pages": None, "char_count": 0}

    word = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0

        doc = word.Documents.Open(os.path.abspath(path), ReadOnly=True)
        try:
            parts = [doc.Content.Text]

            for table in doc.Tables:
                for row in range(1, table.Rows.Count + 1):
                    cells = []
                    for col in range(1, table.Columns.Count + 1):
                        try:
                            cell_text = table.Cell(row, col).Range.Text
                            cells.append(cell_text.replace("\r\x07", "").strip())
                        except Exception:
                            pass
                    if any(cells):
                        parts.append(" | ".join(cells))

            text = "\n".join(parts)
        finally:
            doc.Close(False)

        return {"text": text, "method": "doc_via_word", "n_pages": None, "char_count": len(text)}

    except Exception as e:
        return {"text": "", "method": "doc_conversion_failed", "error": str(e), "n_pages": None, "char_count": 0}
    finally:
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass