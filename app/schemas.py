from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class VendorIn(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    contact_person: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None
    other: Optional[str] = None

class VendorOut(VendorIn):
    id: int
    class Config:
        from_attributes = True

class ProductListOut(BaseModel):
    id: int
    name: str
    product_no: Optional[str] = None
    vendor_name: Optional[str] = None
    material: Optional[str] = None
    sku: Optional[str] = None
    color: Optional[str] = None
    dye_amount: Optional[str] = None
    packaging: Optional[str] = None
    mold_barcode: Optional[str] = None
    mold_location: Optional[str] = None
    other: Optional[str] = None
    produced_qty: Optional[int] = 0
    produced_last_qty: Optional[int] = 0
    produced_at: Optional[str] = None
    photo_url: Optional[str] = None

class ProductDetailOut(ProductListOut):
    material: Optional[str] = None
    sku: Optional[str] = None
    color: Optional[str] = None
    dye_amount: Optional[str] = None
    packaging: Optional[str] = None
    unit_price: Optional[float] = None
    mold_loc_photo_url: Optional[str] = None
    mold_loc_updated_at: Optional[str] = None
    produced_last_qty: Optional[int] = None
