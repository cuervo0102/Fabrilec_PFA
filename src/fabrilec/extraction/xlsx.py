import openpyxl


def extract_xlsx(path: str) -> dict:
    ext = path.lower().rsplit(".", 1)[-1]
    rows_out = []
    n_sheets = 0
    try:
        if ext == "xls":
            import pandas as pd
            sheets = pd.read_excel(path, sheet_name=None, engine="xlrd", header=None)
            n_sheets = len(sheets)
            for df in sheets.values():
                for row in df.itertuples(index=False):
                    cells = [str(c) for c in row if str(c) != "nan"]
                    if cells:
                        rows_out.append(" | ".join(cells))
        else:
            wb = openpyxl.load_workbook(path, data_only=True)
            n_sheets = len(wb.worksheets)
            for sheet in wb.worksheets:
                for row in sheet.iter_rows(values_only=True):
                    cells = [str(c) for c in row if c is not None]
                    if cells:
                        rows_out.append(" | ".join(cells))
    except Exception as e:
        return {"text": "", "method": "xlsx_failed", "error": str(e), "n_pages": None}

    return {"text": "\n".join(rows_out), "method": "xlsx", "n_pages": n_sheets}