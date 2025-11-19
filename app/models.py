from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(Text)
    role = Column(String, default="admin")

class Vendor(Base):
    __tablename__ = "vendors"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True)
    address = Column(Text)
    phone = Column(String)
    contact_person = Column(String)
    fax = Column(String)
    email = Column(String)
    other = Column(Text)
    products = relationship("Product", back_populates="vendor")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    product_no = Column(String, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    material = Column(String)
    sku = Column(String, index=True)
    color = Column(String)
    dye_amount = Column(String)
    packaging = Column(String)
    unit_price = Column(Float, nullable=True)
    mold_barcode = Column(String, unique=True, index=True)
    mold_location = Column(String)
    other = Column(Text)
    photo_path = Column(Text, nullable=True)
    extra_photo_paths = Column(Text, nullable=True)
    produced_qty = Column(Integer, default=0)
    produced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    vendor = relationship("Vendor", back_populates="products")
    mold_loc_photo = Column(Text, nullable=True)
    mold_loc_updated_at = Column(DateTime, nullable=True)
    produced_last_qty = Column(Integer, nullable=True)

class BarcodeSerial(Base):
    __tablename__ = "barcode_serials"
    id = Column(Integer, primary_key=True)
    yyyymmdd = Column(String, index=True)
    vendor_code2 = Column(String, index=True)  # 兩位（'00'~'99'）
    last_serial = Column(Integer, default=0)