import re
import zipfile


def detect_page_count(uploaded, ext):
    """Best-effort page count for a PDF/DOCX upload. Returns an int or None."""
    try:
        uploaded.seek(0)
        if ext == ".pdf":
            from pypdf import PdfReader

            reader = PdfReader(uploaded, strict=False)
            if reader.is_encrypted:
                try:
                    if reader.decrypt("") == 0:
                        return None
                except Exception:
                    return None
            try:
                pages = len(reader.pages)
            except Exception:
                pages = None

            # A few PDF producers create documents that pypdf can otherwise
            # open, but whose page objects make normal traversal fail.
            if pages is None or pages < 1:
                uploaded.seek(0)
                data = uploaded.read()
                matches = re.findall(rb"/Type\s*/Page\b", data)
                pages = len(matches) if matches else None
        elif ext == ".docx":
            with zipfile.ZipFile(uploaded) as archive:
                xml = archive.read("docProps/app.xml").decode("utf-8", "ignore")
            match = re.search(r"<Pages>(\d+)</Pages>", xml)
            pages = int(match.group(1)) if match else None
        else:
            return None
        return pages if pages and pages >= 1 else None
    except Exception:
        return None
    finally:
        try:
            uploaded.seek(0)
        except Exception:
            pass
