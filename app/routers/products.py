import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, and_
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json
from pydantic import BaseModel

from ..deps import get_db, get_current_user
from ..models import Product, Vendor, BarcodeSerial, User 
from ..schemas import ProductListOut, ProductDetailOut
from ..utils import save_bytes_crop_square_reduce, UPLOAD_DIR, remove_upload_file

router = APIRouter(prefix="/products", tags=["products"])

def _fmt_date_tw(dt):
    if not dt:
        return None
    # 以 UTC+8 輸出日期字串
    return (dt + timedelta(hours=8)).strftime("%Y-%m-%d")

def _get_photo_paths(p: Product) -> List[str]:
    paths: List[str] = []
    if getattr(p, "photo_path", None):
        paths.append(p.photo_path)

    extra = getattr(p, "extra_photo_paths", None)
    if extra:
        try:
            data = json.loads(extra)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, str) and item and item not in paths:
                        paths.append(item)
        except Exception:
            for part in str(extra).split(","):
                part = part.strip()
                if part and part not in paths:
                    paths.append(part)
    return paths


def _get_photo_urls(p: Product) -> List[str]:
    return [f"/uploads/{path}" for path in _get_photo_paths(p)]



def _vendor_code2(vendor_id: int) -> str:
    code = vendor_id % 100
    return f"{code:02d}" if code != 0 else "00"

def next_barcode(db: Session, vendor_id: int) -> str:
    today = datetime.now().strftime("%Y%m%d")
    v2 = _vendor_code2(vendor_id)
    row = (
        db.query(BarcodeSerial)
        .filter(and_(BarcodeSerial.yyyymmdd == today, BarcodeSerial.vendor_code2 == v2))
        .first()
    )
    if not row:
        row = BarcodeSerial(yyyymmdd=today, vendor_code2=v2, last_serial=0)
        db.add(row)
        db.flush()
    row.last_serial += 1
    if row.last_serial > 999:
        raise HTTPException(400, detail="序號已用盡")
    return f"{today}{v2}{row.last_serial:03d}"

def _fmt_date_tw(dt):
    if not dt:
        return None
    # 只回 YYYY-MM-DD
    return dt.strftime("%Y-%m-%d")

def _detail_from_model(p: Product, user) -> ProductDetailOut:
    return ProductDetailOut(
        id=p.id,
        name=p.name,
        product_no=p.product_no,
        vendor_name=(p.vendor.name if p.vendor else None),
        material=p.material,
        sku=p.sku,
        color=p.color,
        dye_amount=p.dye_amount,
        packaging=p.packaging,
        mold_barcode=p.mold_barcode,
        mold_location=getattr(p, "mold_location", None),
        other=p.other,
        photo_url=(f"/uploads/{p.photo_path}" if p.photo_path else None),
        unit_price=(p.unit_price if getattr(user, "role", None) == "admin" else None),
        produced_qty=(p.produced_qty or 0),
        produced_at=_fmt_date_tw(getattr(p, "produced_at", None)),
        produced_last_qty=getattr(p, "produced_last_qty", None),
        # 若你有這兩個欄位：
        mold_loc_photo_url=(f"/uploads/{p.mold_loc_photo}" if getattr(p, "mold_loc_photo", None) else None),
        mold_loc_updated_at=(_fmt_date_tw(getattr(p, "mold_loc_updated_at", None))),
    )


def _detail_from_model(p: Product, user) -> ProductDetailOut:
    photo_urls = _get_photo_urls(p)
    return ProductDetailOut(
        id=p.id,
        name=p.name,
        product_no=p.product_no,
        vendor_name=(p.vendor.name if p.vendor else None),
        material=p.material,
        sku=p.sku,
        color=p.color,
        dye_amount=p.dye_amount,
        packaging=p.packaging,
        mold_barcode=p.mold_barcode,
        mold_location=getattr(p, "mold_location", None),
        other=p.other,
        photo_url=(photo_urls[0] if photo_urls else None),
        photo_urls=photo_urls,
        unit_price=(p.unit_price if getattr(user, "role", None) == "admin" else None),
        produced_qty=(p.produced_qty or 0),
        produced_at=_fmt_date_tw(getattr(p, "produced_at", None)),
        produced_last_qty=getattr(p, "produced_last_qty", None),
        mold_loc_photo_url=(f"/uploads/{p.mold_loc_photo}" if getattr(p, "mold_loc_photo", None) else None),
        mold_loc_updated_at=(_fmt_date_tw(getattr(p, "mold_loc_updated_at", None))),
    )

class ProduceIn(BaseModel):
    qty: int

@router.get("", response_model=List[ProductListOut])
def list_products(
    q: Optional[str] = None,
    vendor_id: Optional[int] = None,
    product_no: Optional[str] = None,
    sku: Optional[str] = None,
    mold_barcode: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    query = db.query(Product).outerjoin(Vendor)

    if q:
        q_norm = q.strip().lower()
        query = query.filter(func.lower(Product.name).like(f"%{q_norm}%"))

    if vendor_id:
        query = query.filter(Product.vendor_id == vendor_id)
    if product_no:
        query = query.filter(Product.product_no == product_no)
    if sku:
        query = query.filter(Product.sku == sku)
    if mold_barcode:
        query = query.filter(Product.mold_barcode == mold_barcode)

    query = query.order_by(
        func.lower(func.coalesce(func.nullif(Vendor.name, ''), 'zzz')).asc(),
        func.lower(Product.name).asc(),
        Product.id.desc(),
    ).offset((page - 1) * size).limit(size)

    items = query.all()

    def _fmt_date(d):
        if not d:
            return None
        try:
            return d.strftime("%Y-%m-%d")
        except Exception:
            return str(d)

    return [
        ProductListOut(
            id=p.id,
            name=p.name,
            product_no=p.product_no,
            vendor_name=(p.vendor.name if p.vendor else None),
            material=p.material,
            sku=p.sku,
            color=p.color,
            dye_amount=p.dye_amount,
            packaging=p.packaging,
            mold_barcode=p.mold_barcode,
            mold_location=getattr(p, "mold_location", None),
            other=p.other,
            produced_qty=(p.produced_qty or 0),
            produced_last_qty=(p.produced_last_qty if p.produced_last_qty is not None else 0),
            produced_at=(_fmt_date(getattr(p, "produced_at", None))),
            photo_urls=_get_photo_urls(p),
            photo_url=(_get_photo_urls(p)[0] if _get_photo_urls(p) else None),
        )
        for p in items
    ]

@router.get("/{pid}", response_model=ProductDetailOut)
def get_product_detail(
    pid: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)):
    p = db.query(Product).filter(Product.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")

    return _detail_from_model(p, user)

@router.post("/{pid}/produce", response_model=ProductDetailOut)
def produce(pid: int, qty: int = Body(..., embed=True),
            db: Session = Depends(get_db),
            user=Depends(get_current_user)):
    if qty is None or qty <= 0:
        raise HTTPException(400, detail="數量需為正整數")

    p = db.query(Product).filter(Product.id == pid).first()
    if not p:
        raise HTTPException(404, detail="Product not found")

    p.produced_qty = (p.produced_qty or 0) + int(qty)
    p.produced_last_qty = int(qty)          # ← 關鍵：寫入最後生產數量
    p.produced_at = datetime.utcnow().date()
    db.commit(); db.refresh(p)

    # 回傳詳情（前端會更新詳情 & 之後呼叫列表）
    return ProductDetailOut(
        id=p.id,
        name=p.name,
        product_no=p.product_no,
        vendor_name=(p.vendor.name if p.vendor else None),
        material=p.material,
        sku=p.sku,
        color=p.color,
        dye_amount=p.dye_amount,
        packaging=p.packaging,
        mold_barcode=p.mold_barcode,
        other=p.other,
        photo_url=(f"/uploads/{p.photo_path}" if p.photo_path else None),
        unit_price=(p.unit_price if getattr(user, "role", None) == "admin" else None),
        mold_loc_photo_url=(f"/uploads/{getattr(p, 'mold_loc_photo', None)}" if getattr(p, "mold_loc_photo", None) else None),
        mold_loc_updated_at=(p.mold_loc_updated_at.strftime("%Y-%m-%d") if getattr(p, "mold_loc_updated_at", None) else None),
        produced_qty=(p.produced_qty or 0),
        produced_at=(p.produced_at.strftime("%Y-%m-%d") if getattr(p, "produced_at", None) else None),
        produced_last_qty=getattr(p, "produced_last_qty", None),
    )
    
def get_product_detail(pid: int, db: Session, user: User) -> ProductDetailOut:
    p = db.query(Product).filter(Product.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")

    return _detail_from_model(p, user)

@router.post("", response_model=ProductDetailOut)
async def create_product(
    name: str = Form(...),
    product_no: str = Form(...),
    vendor_id: Optional[str] = Form(None),  # 前端可能給 ""，先用字串接收
    material: Optional[str] = Form(None),
    sku: Optional[str] = Form(None),
    color: Optional[str] = Form(None),
    dye_amount: Optional[str] = Form(None),
    packaging: Optional[str] = Form(None),
    unit_price: Optional[float] = Form(None),
    mold_location: Optional[str] = Form(None),  # 你若已經不需要這個欄位，可移除
    other: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    photos: Optional[List[UploadFile]] = File(None),
    mold_location_photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    # --- vendor_id 正規化："" 或 None -> None；非空才轉 int ---
    vendor_id_val: Optional[int] = None
    if vendor_id is not None and str(vendor_id).strip() != "":
        try:
            vendor_id_val = int(vendor_id)
        except ValueError:
            raise HTTPException(400, detail="vendor_id 格式不正確")

    vendor = db.query(Vendor).filter(Vendor.id == vendor_id_val).first() if vendor_id_val else None
    if vendor_id_val and not vendor:
        raise HTTPException(400, detail="Vendor not found")

    # --- 產生 13 碼條碼：無廠商 = 00 ---
    code13 = next_barcode(db, vendor.id if vendor else 0)

    # --- 成品照片：支援多張 ---
    photo_paths: List[str] = []

    if photos:
        for f in photos:
            if not f:
                continue
            raw = await f.read()
            path = save_bytes_crop_square_reduce(raw, f.filename)
            photo_paths.append(path)
    elif photo:
        raw = await photo.read()
        path = save_bytes_crop_square_reduce(raw, photo.filename)
        photo_paths.append(path)

    photo_path = photo_paths[0] if photo_paths else None
    extra_photo_paths = json.dumps(photo_paths) if photo_paths else None

    # --- 模具位置照片：只保留最後一張 ---
    loc_photo_path = None
    loc_updated_at = None
    if mold_location_photo:
        loc_bytes = await mold_location_photo.read() # ← 用 await 讀 bytes
        loc_photo_path = save_bytes_crop_square_reduce(loc_bytes, mold_location_photo.filename)
    
    obj = Product(
        name=name,
        product_no=product_no,
        vendor_id=(vendor.id if vendor else None),
        material=material,
        sku=sku,
        color=color,
        dye_amount=dye_amount,
        packaging=packaging,
        unit_price=unit_price,
        mold_barcode=code13,
        other=other,
        photo_path=photo_path,
        extra_photo_paths=extra_photo_paths,
        mold_loc_photo=loc_photo_path,
        mold_loc_updated_at=(datetime.utcnow() if loc_photo_path else None),
    )

    db.add(obj); db.commit(); db.refresh(obj)

    return get_product_detail(obj.id, db, user)



@router.delete("/{pid}")
def delete_product(
    pid: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    p = db.query(Product).filter(Product.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")

    # 先刪檔，再刪資料（包含所有成品照片與模具位置照片）
    for path in _get_photo_paths(p):
        remove_upload_file(path)
    remove_upload_file(getattr(p, "mold_loc_photo", None))

    db.delete(p)
    db.commit()
    return {"ok": True}


class ProductUpdateIn(BaseModel):
    name: Optional[str] = None
    product_no: Optional[str] = None
    material: Optional[str] = None
    sku: Optional[str] = None
    color: Optional[str] = None
    dye_amount: Optional[str] = None
    packaging: Optional[str] = None
    unit_price: Optional[float] = None
    other: Optional[str] = None

@router.put("/{pid}", response_model=ProductDetailOut)
def update_product(
    pid: int,
    payload: ProductUpdateIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    p = db.query(Product).filter(Product.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")

    # 逐欄位套用（只更新有給值的欄位）
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(p, field, value)

    db.commit()
    db.refresh(p)
    # 用你已存在的詳細輸出格式回傳
    return get_product_detail(p.id, db, user)    

@router.put("/{pid}/mold-location-photo", response_model=ProductDetailOut)
async def update_mold_loc_photo(
    pid: int,
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    p = db.query(Product).filter(Product.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")

    # 讀 bytes
    raw = await photo.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    # 刪舊檔（只保留最後一張）
    if p.mold_loc_photo:
        try:
            old_path = os.path.join(UPLOAD_DIR, p.mold_loc_photo)
            if os.path.isfile(old_path):
                os.remove(old_path)
        except Exception:
            pass

    # 正確呼叫：給 bytes + 原始檔名
    new_name = save_bytes_crop_square_reduce(raw, photo.filename)

    p.mold_loc_photo = new_name
    p.mold_loc_updated_at = datetime.utcnow()
    db.commit(); db.refresh(p)

    # 回傳你現有的樣式
    return ProductDetailOut(
        id=p.id,
        name=p.name,
        product_no=p.product_no,
        vendor_name=(p.vendor.name if p.vendor else None),
        material=p.material,
        sku=p.sku,
        color=p.color,
        dye_amount=p.dye_amount,
        packaging=p.packaging,
        mold_barcode=p.mold_barcode,
        other=p.other,
        photo_url=(f"/uploads/{p.photo_path}" if p.photo_path else None),
        unit_price=(p.unit_price if getattr(user, "role", None) == "admin" else None),
        mold_loc_photo_url=(f"/uploads/{p.mold_loc_photo}" if p.mold_loc_photo else None),
        mold_loc_updated_at=(p.mold_loc_updated_at.strftime("%Y-%m-%d") if p.mold_loc_updated_at else None),
        produced_qty=getattr(p, "produced_qty", 0),
        produced_at=(p.produced_at.strftime("%Y-%m-%d") if getattr(p, "produced_at", None) else None),
        produced_last_qty=getattr(p, "produced_last_qty", None),
    )
    
@router.put("/{pid}/photos", response_model=ProductDetailOut)
async def update_product_photos(
    pid: int,
    keep_paths: Optional[str] = Form(None),
    photos: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    # 1. 找出產品
    p = db.query(Product).filter(Product.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")

    # 2. 既有所有照片路徑（含 photo_path + extra_photo_paths）
    existing = _get_photo_paths(p)

    # 3. 前端傳來要保留的舊檔名
    keep_list: List[str] = []
    if keep_paths:
        try:
            data = json.loads(keep_paths)
            if isinstance(data, list):
                keep_list = [str(x) for x in data]
        except Exception:
            # 後備：逗號分隔字串
            keep_list = [s.strip() for s in str(keep_paths).split(",") if s.strip()]

    # 只保留本來就存在的檔名，避免亂傳
    keep_final = [path for path in keep_list if path in existing]

    # 4. 刪除被移除的舊照片
    for path in existing:
        if path not in keep_final:
            remove_upload_file(path)

    # 5. 把要保留的 + 新增的組成新的 photo_paths
    photo_paths: List[str] = list(keep_final)

    if photos:
        for f in photos:
            if not f:
                continue
            raw = await f.read()
            new_path = save_bytes_crop_square_reduce(raw, f.filename)
            photo_paths.append(new_path)

    # 6. 更新 DB 欄位
    p.photo_path = photo_paths[0] if photo_paths else None
    p.extra_photo_paths = json.dumps(photo_paths) if photo_paths else None

    db.commit()
    db.refresh(p)

    # 7. 回傳最新詳情（含 photo_urls）
    return _detail_from_model(p, user)