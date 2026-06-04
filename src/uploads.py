import os
import zipfile
from typing import List


def safe_extract_zip(zip_path: str, dest_dir: str) -> None:
    os.makedirs(dest_dir, exist_ok=True)
    dest_abs = os.path.abspath(dest_dir)

    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            member_path = os.path.abspath(os.path.join(dest_dir, member))
            if not (member_path == dest_abs or member_path.startswith(dest_abs + os.sep)):
                raise ValueError(f"Refusing to extract unsafe path in zip: {member}")
        zf.extractall(dest_dir)


def save_uploaded_files(files, dest_dir: str) -> List[str]:
    """Save a list of Flask FileStorage objects into dest_dir. Any .zip
    file is extracted (and then discarded) rather than saved as-is."""
    from werkzeug.utils import secure_filename

    os.makedirs(dest_dir, exist_ok=True)
    saved = []

    for f in files:
        filename = secure_filename(f.filename or "")
        if not filename:
            continue

        if filename.lower().endswith(".zip"):
            tmp_zip_path = os.path.join(dest_dir, filename)
            f.save(tmp_zip_path)
            try:
                safe_extract_zip(tmp_zip_path, dest_dir)
                saved.append(f"{filename} (bundle, extracted)")
            finally:
                os.remove(tmp_zip_path)
        else:
            path = os.path.join(dest_dir, filename)
            f.save(path)
            saved.append(filename)

    return saved
