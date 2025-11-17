# utils.py
import os, time
from io import BytesIO
from PIL import Image, ImageOps


UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def _unique_name(orig_filename: str | None, default_ext=".jpg") -> str:
    ext = (os.path.splitext(orig_filename or "")[1] or default_ext).lower()
    # 將 heic/heif 統一輸出為 .jpg
    if ext in (".heic", ".heif", ".heics", ".heifs", ""):
        ext = ".jpg"
    ts = time.strftime("%Y%m%d%H%M%S")
    return f"{ts}_{int(time.time()*1_000_000)%1_000_000:06d}{ext}"

def save_bytes_crop_square_reduce(data: bytes, orig_filename: str | None, max_side=600) -> str:
    """
    data: 影像 bytes
    - 置中裁成 1:1
    - 縮到 max_side（約等於你原本的縮 20% 需求：體積小很多）
    - 失敗就寫原檔 bytes
    回傳：檔名（相對路徑）
    """
    name = _unique_name(orig_filename, ".jpg")
    path = os.path.join(UPLOAD_DIR, name)
    try:
        im = Image.open(BytesIO(data))
        im = ImageOps.exif_transpose(im)
        im = im.convert("RGB")
        w, h = im.size
        m = min(w, h)
        left = (w - m) // 2
        top = (h - m) // 2
        im = im.crop((left, top, left + m, top + m))
        im.thumbnail((max_side, max_side))
        im.save(path, format="JPEG", quality=85, optimize=True)
        return name
    except Exception:
        # 任何處理失敗就直接寫 bytes（避免 500）
        with open(path, "wb") as f:
            f.write(data)
        return name

def remove_upload_file(filename: str | None) -> None:
    """安全刪除 uploads/ 底下的單一檔案（略過不存在／空字串）"""
    if not filename:
        return
    # 防止路徑跳脫：只允許純檔名
    safe_name = os.path.basename(filename)
    path = os.path.join(UPLOAD_DIR, safe_name)
    try:
        if os.path.isfile(path):
            os.remove(path)
    except Exception:
        # 靜默略過任何刪檔失敗，不影響主要流程
        pass