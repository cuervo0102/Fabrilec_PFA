import os


from .pdf import extract_pdf
from .docx import extract_docx
from .doc import extract_doc
from .xlsx import extract_xlsx

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".xls"}


def discover_files(root_folder: str):
    for dirpath, _dirnames, filenames in os.walk(root_folder):
        for name in filenames:
            if name.startswith("~$"):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                full_path = os.path.join(dirpath, name)
                relative_path = os.path.relpath(full_path, root_folder)
                relative_path = relative_path.replace(os.sep, "/")  
                yield full_path, relative_path


def extract_file(path: str) -> dict:
    ext = path.lower().rsplit(".", 1)[-1] if "." in path else ""

    if ext == "pdf":
        result = extract_pdf(path)
    elif ext == "docx":
        result = extract_docx(path)
    elif ext == "doc":
        result = extract_doc(path)
    elif ext in ("xlsx", "xls", "xlsm"):
        result = extract_xlsx(path)
    else:
        result = {"text": "", "method": "unsupported", "n_pages": None}

    result["source_path"] = path
    result["extension"] = ext
    result["char_count"] = len(result.get("text", ""))
    return result