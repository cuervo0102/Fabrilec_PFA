# src/fabrilec/extraction/doc.py
import os
import subprocess
import tempfile
from pathlib import Path

from .docx import extract_docx

IS_WINDOWS = os.name == "nt"


def _extract_doc_windows(path: str) -> dict:
    import win32com.client  

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


def _extract_doc_libreoffice(path: str) -> dict:
    
    with tempfile.TemporaryDirectory() as tmpdir, tempfile.TemporaryDirectory() as profile_dir:
        try:
            subprocess.run(
                ["libreoffice", "--headless", "--norestore",
                 f"-env:UserInstallation=file://{profile_dir}",
                 "--convert-to", "docx", "--outdir", tmpdir, path],
                check=True, capture_output=True, timeout=30,
            )
        except Exception as e:
            return {"text": "", "method": "doc_conversion_failed", "error": str(e), "n_pages": None, "char_count": 0}

        converted = list(Path(tmpdir).glob("*.docx"))
        if not converted:
            return {"text": "", "method": "doc_conversion_failed", "n_pages": None, "char_count": 0}

        result = extract_docx(str(converted[0]))
        result["method"] = "doc_via_libreoffice"
        result["char_count"] = len(result.get("text", ""))
        return result


def extract_doc(path: str) -> dict:
    if IS_WINDOWS:
        return _extract_doc_windows(path)
    return _extract_doc_libreoffice(path)