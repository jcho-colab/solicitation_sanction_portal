from fastapi import FastAPI, APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
import json
import io
import pandas as pd
import shutil

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# File upload directory
UPLOAD_DIR = ROOT_DIR / 'uploads'
UPLOAD_DIR.mkdir(exist_ok=True)

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'automotive-parts-portal-secret-key-2024')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

# Create the main app without a prefix
app = FastAPI(title="Automotive Parts Supplier Portal")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

security = HTTPBearer()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== MODELS =====

class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: str = Field(default="supplier")  # "admin" or "supplier"
    company_name: Optional[str] = None
    is_active: bool = True

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "supplier"
    company_name: Optional[str] = None

class User(UserBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class ChildPart(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    identifier: str  # Component identifier/SKU
    name: str
    description: Optional[str] = None
    country_of_origin: str
    weight_kg: float
    weight_lbs: Optional[float] = None
    value_usd: float
    aluminum_content_percent: float = 0
    steel_content_percent: float = 0
    has_russian_content: bool = False
    russian_content_percent: float = 0
    russian_content_description: Optional[str] = None
    manufacturing_method: Optional[str] = None
    document_ids: List[str] = []
    is_complete: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChildPartCreate(BaseModel):
    identifier: str
    name: str
    description: Optional[str] = None
    country_of_origin: str
    weight_kg: float
    value_usd: float
    aluminum_content_percent: float = 0
    steel_content_percent: float = 0
    has_russian_content: bool = False
    russian_content_percent: float = 0
    russian_content_description: Optional[str] = None
    manufacturing_method: Optional[str] = None

class ChildPartUpdate(BaseModel):
    identifier: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    country_of_origin: Optional[str] = None
    weight_kg: Optional[float] = None
    value_usd: Optional[float] = None
    aluminum_content_percent: Optional[float] = None
    steel_content_percent: Optional[float] = None
    has_russian_content: Optional[bool] = None
    russian_content_percent: Optional[float] = None
    russian_content_description: Optional[str] = None
    manufacturing_method: Optional[str] = None

class ParentPart(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sku: str  # Unique part number
    name: str
    description: Optional[str] = None
    supplier_id: str
    status: str = "incomplete"  # "incomplete", "completed", "needs_review"
    total_weight_kg: float = 0
    total_value_usd: float = 0
    country_of_origin: Optional[str] = None
    child_parts: List[ChildPart] = []
    document_ids: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ParentPartCreate(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    country_of_origin: Optional[str] = None
    total_weight_kg: float = 0
    total_value_usd: float = 0

class ParentPartUpdate(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    country_of_origin: Optional[str] = None
    total_weight_kg: Optional[float] = None
    total_value_usd: Optional[float] = None

class Document(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    supplier_id: str
    original_name: str
    stored_name: str
    file_type: str
    file_size: int
    file_path: str
    parent_part_ids: List[str] = []
    child_part_ids: List[str] = []
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DocumentUpdate(BaseModel):
    original_name: Optional[str] = None
    parent_part_ids: Optional[List[str]] = None
    child_part_ids: Optional[List[str]] = None

class AuditLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    user_email: str
    action: str  # "create", "update", "delete"
    entity_type: str  # "parent_part", "child_part", "document", "supplier"
    entity_id: str
    field_changes: List[Dict[str, Any]] = []  # [{"field": "name", "old": "x", "new": "y"}]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    supplier_id: Optional[str] = None

# ===== HELPER FUNCTIONS =====

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_token(user_id: str, email: str, role: str) -> str:
    expiration = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": expiration
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token_data = decode_token(credentials.credentials)
    user = await db.users.find_one({"id": token_data["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def get_admin_user(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

async def create_audit_log(
    user_id: str,
    user_email: str,
    action: str,
    entity_type: str,
    entity_id: str,
    field_changes: List[Dict] = [],
    supplier_id: Optional[str] = None
):
    audit = AuditLog(
        user_id=user_id,
        user_email=user_email,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        field_changes=field_changes,
        supplier_id=supplier_id
    )
    doc = audit.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    await db.audit_logs.insert_one(doc)

def calculate_part_status(parent_part: dict) -> str:
    """Calculate the status of a parent part based on its child parts."""
    child_parts = parent_part.get('child_parts', [])
    
    if not child_parts:
        return "incomplete"
    
    # Check if all child parts are complete
    all_complete = all(cp.get('is_complete', False) for cp in child_parts)
    
    # Calculate total weight of children
    child_weight_sum = sum(cp.get('weight_kg', 0) for cp in child_parts)
    parent_weight = parent_part.get('total_weight_kg', 0)
    
    # Check for weight mismatch (needs review)
    weight_tolerance = 0.01  # 1% tolerance
    if parent_weight > 0 and abs(child_weight_sum - parent_weight) / parent_weight > weight_tolerance:
        return "needs_review"
    
    if all_complete:
        return "completed"
    
    return "incomplete"

# ===== AUTH ROUTES =====

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    # Check if user already exists
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        email=user_data.email,
        name=user_data.name,
        role=user_data.role,
        company_name=user_data.company_name
    )
    
    user_dict = user.model_dump()
    user_dict['password_hash'] = hash_password(user_data.password)
    user_dict['created_at'] = user_dict['created_at'].isoformat()
    user_dict['updated_at'] = user_dict['updated_at'].isoformat()
    
    await db.users.insert_one(user_dict)
    
    token = create_token(user.id, user.email, user.role)
    
    return TokenResponse(
        access_token=token,
        user={
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "company_name": user.company_name
        }
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(credentials.password, user.get('password_hash', '')):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.get('is_active', True):
        raise HTTPException(status_code=401, detail="Account is disabled")
    
    token = create_token(user['id'], user['email'], user['role'])
    
    return TokenResponse(
        access_token=token,
        user={
            "id": user['id'],
            "email": user['email'],
            "name": user['name'],
            "role": user['role'],
            "company_name": user.get('company_name')
        }
    )

@api_router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user['id'],
        "email": current_user['email'],
        "name": current_user['name'],
        "role": current_user['role'],
        "company_name": current_user.get('company_name')
    }

# ===== SUPPLIER ROUTES (Admin only) =====

@api_router.get("/suppliers")
async def list_suppliers(admin: dict = Depends(get_admin_user)):
    suppliers = await db.users.find({"role": "supplier"}, {"_id": 0, "password_hash": 0}).to_list(1000)
    return suppliers

@api_router.post("/suppliers")
async def create_supplier(user_data: UserCreate, admin: dict = Depends(get_admin_user)):
    user_data.role = "supplier"
    
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        email=user_data.email,
        name=user_data.name,
        role="supplier",
        company_name=user_data.company_name
    )
    
    user_dict = user.model_dump()
    user_dict['password_hash'] = hash_password(user_data.password)
    user_dict['created_at'] = user_dict['created_at'].isoformat()
    user_dict['updated_at'] = user_dict['updated_at'].isoformat()
    
    await db.users.insert_one(user_dict)
    
    await create_audit_log(
        user_id=admin['id'],
        user_email=admin['email'],
        action="create",
        entity_type="supplier",
        entity_id=user.id,
        field_changes=[{"field": "supplier_created", "new": user.email}]
    )
    
    return {"id": user.id, "email": user.email, "name": user.name, "company_name": user.company_name}

@api_router.put("/suppliers/{supplier_id}")
async def update_supplier(
    supplier_id: str,
    name: Optional[str] = None,
    company_name: Optional[str] = None,
    is_active: Optional[bool] = None,
    admin: dict = Depends(get_admin_user)
):
    supplier = await db.users.find_one({"id": supplier_id, "role": "supplier"}, {"_id": 0})
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    updates = {}
    changes = []
    
    if name is not None:
        changes.append({"field": "name", "old": supplier.get('name'), "new": name})
        updates['name'] = name
    if company_name is not None:
        changes.append({"field": "company_name", "old": supplier.get('company_name'), "new": company_name})
        updates['company_name'] = company_name
    if is_active is not None:
        changes.append({"field": "is_active", "old": supplier.get('is_active'), "new": is_active})
        updates['is_active'] = is_active
    
    if updates:
        updates['updated_at'] = datetime.now(timezone.utc).isoformat()
        await db.users.update_one({"id": supplier_id}, {"$set": updates})
        
        await create_audit_log(
            user_id=admin['id'],
            user_email=admin['email'],
            action="update",
            entity_type="supplier",
            entity_id=supplier_id,
            field_changes=changes
        )
    
    return {"success": True}

@api_router.delete("/suppliers/{supplier_id}")
async def delete_supplier(supplier_id: str, admin: dict = Depends(get_admin_user)):
    supplier = await db.users.find_one({"id": supplier_id, "role": "supplier"}, {"_id": 0})
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    await db.users.delete_one({"id": supplier_id})
    
    await create_audit_log(
        user_id=admin['id'],
        user_email=admin['email'],
        action="delete",
        entity_type="supplier",
        entity_id=supplier_id,
        field_changes=[{"field": "supplier_deleted", "old": supplier.get('email')}]
    )
    
    return {"success": True}

# ===== PARENT PARTS ROUTES =====

@api_router.get("/parts")
async def list_parts(current_user: dict = Depends(get_current_user)):
    query = {}
    if current_user['role'] == 'supplier':
        query['supplier_id'] = current_user['id']
    
    parts = await db.parent_parts.find(query, {"_id": 0}).to_list(10000)
    return parts

@api_router.get("/parts/stats")
async def get_parts_stats(current_user: dict = Depends(get_current_user)):
    query = {}
    if current_user['role'] == 'supplier':
        query['supplier_id'] = current_user['id']
    
    parts = await db.parent_parts.find(query, {"_id": 0}).to_list(10000)
    
    completed = len([p for p in parts if p.get('status') == 'completed'])
    incomplete = len([p for p in parts if p.get('status') == 'incomplete'])
    needs_review = len([p for p in parts if p.get('status') == 'needs_review'])
    
    return {
        "completed": completed,
        "incomplete": incomplete,
        "needs_review": needs_review,
        "total": len(parts)
    }

@api_router.get("/parts/{part_id}")
async def get_part(part_id: str, current_user: dict = Depends(get_current_user)):
    query = {"id": part_id}
    if current_user['role'] == 'supplier':
        query['supplier_id'] = current_user['id']
    
    part = await db.parent_parts.find_one(query, {"_id": 0})
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    return part

@api_router.post("/parts")
async def create_part(part_data: ParentPartCreate, current_user: dict = Depends(get_current_user)):
    # Check for duplicate SKU
    existing = await db.parent_parts.find_one({"sku": part_data.sku, "supplier_id": current_user['id']})
    if existing:
        raise HTTPException(status_code=400, detail="SKU already exists for this supplier")
    
    part = ParentPart(
        sku=part_data.sku,
        name=part_data.name,
        description=part_data.description,
        supplier_id=current_user['id'],
        country_of_origin=part_data.country_of_origin,
        total_weight_kg=part_data.total_weight_kg,
        total_value_usd=part_data.total_value_usd
    )
    
    part_dict = part.model_dump()
    part_dict['created_at'] = part_dict['created_at'].isoformat()
    part_dict['updated_at'] = part_dict['updated_at'].isoformat()
    for cp in part_dict.get('child_parts', []):
        cp['created_at'] = cp['created_at'].isoformat() if isinstance(cp['created_at'], datetime) else cp['created_at']
        cp['updated_at'] = cp['updated_at'].isoformat() if isinstance(cp['updated_at'], datetime) else cp['updated_at']
    
    await db.parent_parts.insert_one(part_dict)
    
    await create_audit_log(
        user_id=current_user['id'],
        user_email=current_user['email'],
        action="create",
        entity_type="parent_part",
        entity_id=part.id,
        supplier_id=current_user['id'] if current_user['role'] == 'supplier' else None,
        field_changes=[{"field": "sku", "new": part.sku}]
    )
    
    # Remove MongoDB's _id before returning
    part_dict.pop('_id', None)
    return part_dict

@api_router.put("/parts/{part_id}")
async def update_part(
    part_id: str,
    part_data: ParentPartUpdate,
    current_user: dict = Depends(get_current_user)
):
    query = {"id": part_id}
    if current_user['role'] == 'supplier':
        query['supplier_id'] = current_user['id']
    
    part = await db.parent_parts.find_one(query, {"_id": 0})
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    
    updates = {}
    changes = []
    
    for field, value in part_data.model_dump(exclude_unset=True).items():
        if value is not None and part.get(field) != value:
            changes.append({"field": field, "old": part.get(field), "new": value})
            updates[field] = value
    
    if updates:
        updates['updated_at'] = datetime.now(timezone.utc).isoformat()
        await db.parent_parts.update_one({"id": part_id}, {"$set": updates})
        
        # Recalculate status
        updated_part = await db.parent_parts.find_one({"id": part_id}, {"_id": 0})
        new_status = calculate_part_status(updated_part)
        await db.parent_parts.update_one({"id": part_id}, {"$set": {"status": new_status}})
        
        await create_audit_log(
            user_id=current_user['id'],
            user_email=current_user['email'],
            action="update",
            entity_type="parent_part",
            entity_id=part_id,
            supplier_id=current_user['id'] if current_user['role'] == 'supplier' else None,
            field_changes=changes
        )
    
    return {"success": True}

@api_router.delete("/parts/{part_id}")
async def delete_part(part_id: str, current_user: dict = Depends(get_current_user)):
    query = {"id": part_id}
    if current_user['role'] == 'supplier':
        query['supplier_id'] = current_user['id']
    
    part = await db.parent_parts.find_one(query, {"_id": 0})
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    
    await db.parent_parts.delete_one({"id": part_id})
    
    await create_audit_log(
        user_id=current_user['id'],
        user_email=current_user['email'],
        action="delete",
        entity_type="parent_part",
        entity_id=part_id,
        supplier_id=current_user['id'] if current_user['role'] == 'supplier' else None,
        field_changes=[{"field": "sku", "old": part.get('sku')}]
    )
    
    return {"success": True}

# ===== CHILD PARTS ROUTES =====

@api_router.post("/parts/{part_id}/children")
async def add_child_part(
    part_id: str,
    child_data: ChildPartCreate,
    current_user: dict = Depends(get_current_user)
):
    query = {"id": part_id}
    if current_user['role'] == 'supplier':
        query['supplier_id'] = current_user['id']
    
    part = await db.parent_parts.find_one(query, {"_id": 0})
    if not part:
        raise HTTPException(status_code=404, detail="Parent part not found")
    
    child = ChildPart(
        identifier=child_data.identifier,
        name=child_data.name,
        description=child_data.description,
        country_of_origin=child_data.country_of_origin,
        weight_kg=child_data.weight_kg,
        weight_lbs=child_data.weight_kg * 2.20462,
        value_usd=child_data.value_usd,
        aluminum_content_percent=child_data.aluminum_content_percent,
        steel_content_percent=child_data.steel_content_percent,
        has_russian_content=child_data.has_russian_content,
        russian_content_percent=child_data.russian_content_percent,
        russian_content_description=child_data.russian_content_description,
        manufacturing_method=child_data.manufacturing_method,
        is_complete=True if all([
            child_data.identifier,
            child_data.name,
            child_data.country_of_origin,
            child_data.weight_kg > 0,
            child_data.value_usd > 0
        ]) else False
    )
    
    child_dict = child.model_dump()
    child_dict['created_at'] = child_dict['created_at'].isoformat()
    child_dict['updated_at'] = child_dict['updated_at'].isoformat()
    
    await db.parent_parts.update_one(
        {"id": part_id},
        {
            "$push": {"child_parts": child_dict},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    # Recalculate status
    updated_part = await db.parent_parts.find_one({"id": part_id}, {"_id": 0})
    new_status = calculate_part_status(updated_part)
    await db.parent_parts.update_one({"id": part_id}, {"$set": {"status": new_status}})
    
    await create_audit_log(
        user_id=current_user['id'],
        user_email=current_user['email'],
        action="create",
        entity_type="child_part",
        entity_id=child.id,
        supplier_id=current_user['id'] if current_user['role'] == 'supplier' else None,
        field_changes=[{"field": "identifier", "new": child.identifier}]
    )
    
    return child_dict

@api_router.put("/parts/{part_id}/children/{child_id}")
async def update_child_part(
    part_id: str,
    child_id: str,
    child_data: ChildPartUpdate,
    current_user: dict = Depends(get_current_user)
):
    query = {"id": part_id}
    if current_user['role'] == 'supplier':
        query['supplier_id'] = current_user['id']
    
    part = await db.parent_parts.find_one(query, {"_id": 0})
    if not part:
        raise HTTPException(status_code=404, detail="Parent part not found")
    
    # Find and update the child part
    child_parts = part.get('child_parts', [])
    child_index = None
    old_child = None
    
    for i, cp in enumerate(child_parts):
        if cp.get('id') == child_id:
            child_index = i
            old_child = cp.copy()
            break
    
    if child_index is None:
        raise HTTPException(status_code=404, detail="Child part not found")
    
    changes = []
    for field, value in child_data.model_dump(exclude_unset=True).items():
        if value is not None and old_child.get(field) != value:
            changes.append({"field": field, "old": old_child.get(field), "new": value})
            child_parts[child_index][field] = value
    
    if changes:
        # Update weight_lbs if weight_kg changed
        if 'weight_kg' in [c['field'] for c in changes]:
            child_parts[child_index]['weight_lbs'] = child_parts[child_index]['weight_kg'] * 2.20462
        
        child_parts[child_index]['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        # Check if complete
        cp = child_parts[child_index]
        child_parts[child_index]['is_complete'] = all([
            cp.get('identifier'),
            cp.get('name'),
            cp.get('country_of_origin'),
            cp.get('weight_kg', 0) > 0,
            cp.get('value_usd', 0) > 0
        ])
        
        await db.parent_parts.update_one(
            {"id": part_id},
            {
                "$set": {
                    "child_parts": child_parts,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        # Recalculate status
        updated_part = await db.parent_parts.find_one({"id": part_id}, {"_id": 0})
        new_status = calculate_part_status(updated_part)
        await db.parent_parts.update_one({"id": part_id}, {"$set": {"status": new_status}})
        
        await create_audit_log(
            user_id=current_user['id'],
            user_email=current_user['email'],
            action="update",
            entity_type="child_part",
            entity_id=child_id,
            supplier_id=current_user['id'] if current_user['role'] == 'supplier' else None,
            field_changes=changes
        )
    
    return {"success": True}

@api_router.delete("/parts/{part_id}/children/{child_id}")
async def delete_child_part(
    part_id: str,
    child_id: str,
    current_user: dict = Depends(get_current_user)
):
    query = {"id": part_id}
    if current_user['role'] == 'supplier':
        query['supplier_id'] = current_user['id']
    
    part = await db.parent_parts.find_one(query, {"_id": 0})
    if not part:
        raise HTTPException(status_code=404, detail="Parent part not found")
    
    child_parts = part.get('child_parts', [])
    deleted_child = None
    new_child_parts = []
    
    for cp in child_parts:
        if cp.get('id') == child_id:
            deleted_child = cp
        else:
            new_child_parts.append(cp)
    
    if not deleted_child:
        raise HTTPException(status_code=404, detail="Child part not found")
    
    await db.parent_parts.update_one(
        {"id": part_id},
        {
            "$set": {
                "child_parts": new_child_parts,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Recalculate status
    updated_part = await db.parent_parts.find_one({"id": part_id}, {"_id": 0})
    new_status = calculate_part_status(updated_part)
    await db.parent_parts.update_one({"id": part_id}, {"$set": {"status": new_status}})
    
    await create_audit_log(
        user_id=current_user['id'],
        user_email=current_user['email'],
        action="delete",
        entity_type="child_part",
        entity_id=child_id,
        supplier_id=current_user['id'] if current_user['role'] == 'supplier' else None,
        field_changes=[{"field": "identifier", "old": deleted_child.get('identifier')}]
    )
    
    return {"success": True}

@api_router.post("/parts/{part_id}/children/{child_id}/duplicate")
async def duplicate_child_part(
    part_id: str,
    child_id: str,
    current_user: dict = Depends(get_current_user)
):
    query = {"id": part_id}
    if current_user['role'] == 'supplier':
        query['supplier_id'] = current_user['id']
    
    part = await db.parent_parts.find_one(query, {"_id": 0})
    if not part:
        raise HTTPException(status_code=404, detail="Parent part not found")
    
    # Find the child to duplicate
    source_child = None
    for cp in part.get('child_parts', []):
        if cp.get('id') == child_id:
            source_child = cp
            break
    
    if not source_child:
        raise HTTPException(status_code=404, detail="Child part not found")
    
    # Create a copy with new ID
    new_child = ChildPart(
        identifier=f"{source_child.get('identifier')}_copy",
        name=f"{source_child.get('name')} (Copy)",
        description=source_child.get('description'),
        country_of_origin=source_child.get('country_of_origin'),
        weight_kg=source_child.get('weight_kg', 0),
        weight_lbs=source_child.get('weight_kg', 0) * 2.20462,
        value_usd=source_child.get('value_usd', 0),
        aluminum_content_percent=source_child.get('aluminum_content_percent', 0),
        steel_content_percent=source_child.get('steel_content_percent', 0),
        has_russian_content=source_child.get('has_russian_content', False),
        russian_content_percent=source_child.get('russian_content_percent', 0),
        russian_content_description=source_child.get('russian_content_description'),
        manufacturing_method=source_child.get('manufacturing_method'),
        is_complete=False  # Mark as incomplete since identifier changed
    )
    
    child_dict = new_child.model_dump()
    child_dict['created_at'] = child_dict['created_at'].isoformat()
    child_dict['updated_at'] = child_dict['updated_at'].isoformat()
    
    await db.parent_parts.update_one(
        {"id": part_id},
        {
            "$push": {"child_parts": child_dict},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    # Recalculate status
    updated_part = await db.parent_parts.find_one({"id": part_id}, {"_id": 0})
    new_status = calculate_part_status(updated_part)
    await db.parent_parts.update_one({"id": part_id}, {"$set": {"status": new_status}})
    
    await create_audit_log(
        user_id=current_user['id'],
        user_email=current_user['email'],
        action="create",
        entity_type="child_part",
        entity_id=new_child.id,
        supplier_id=current_user['id'] if current_user['role'] == 'supplier' else None,
        field_changes=[{"field": "duplicated_from", "old": child_id, "new": new_child.id}]
    )
    
    return child_dict

# ===== DOCUMENT ROUTES =====

@api_router.get("/documents")
async def list_documents(current_user: dict = Depends(get_current_user)):
    query = {}
    if current_user['role'] == 'supplier':
        query['supplier_id'] = current_user['id']
    
    documents = await db.documents.find(query, {"_id": 0}).to_list(10000)
    return documents

@api_router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    parent_part_ids: str = Form(default="[]"),
    child_part_ids: str = Form(default="[]"),
    current_user: dict = Depends(get_current_user)
):
    try:
        parent_ids = json.loads(parent_part_ids)
        child_ids = json.loads(child_part_ids)
    except:
        parent_ids = []
        child_ids = []
    
    # Check for duplicate filename
    existing = await db.documents.find_one({
        "supplier_id": current_user['id'],
        "original_name": file.filename
    })
    
    # Generate unique stored name
    file_ext = Path(file.filename).suffix
    stored_name = f"{uuid.uuid4()}{file_ext}"
    file_path = UPLOAD_DIR / stored_name
    
    # Save file
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    doc = Document(
        supplier_id=current_user['id'],
        original_name=file.filename,
        stored_name=stored_name,
        file_type=file.content_type or 'application/octet-stream',
        file_size=len(content),
        file_path=str(file_path),
        parent_part_ids=parent_ids,
        child_part_ids=child_ids,
        version=1 if not existing else (existing.get('version', 1) + 1)
    )
    
    doc_dict = doc.model_dump()
    doc_dict['created_at'] = doc_dict['created_at'].isoformat()
    doc_dict['updated_at'] = doc_dict['updated_at'].isoformat()
    
    await db.documents.insert_one(doc_dict)
    
    # Update parts with document reference
    if parent_ids:
        for pid in parent_ids:
            await db.parent_parts.update_one(
                {"id": pid},
                {"$addToSet": {"document_ids": doc.id}}
            )
    
    if child_ids:
        # Update child parts within parent parts
        parts = await db.parent_parts.find({"supplier_id": current_user['id']}, {"_id": 0}).to_list(10000)
        for part in parts:
            updated = False
            child_parts = part.get('child_parts', [])
            for cp in child_parts:
                if cp.get('id') in child_ids:
                    if 'document_ids' not in cp:
                        cp['document_ids'] = []
                    if doc.id not in cp['document_ids']:
                        cp['document_ids'].append(doc.id)
                        updated = True
            if updated:
                await db.parent_parts.update_one(
                    {"id": part['id']},
                    {"$set": {"child_parts": child_parts}}
                )
    
    await create_audit_log(
        user_id=current_user['id'],
        user_email=current_user['email'],
        action="create",
        entity_type="document",
        entity_id=doc.id,
        supplier_id=current_user['id'] if current_user['role'] == 'supplier' else None,
        field_changes=[{"field": "filename", "new": file.filename}]
    )
    
    return {
        "id": doc.id,
        "original_name": doc.original_name,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "duplicate_warning": existing is not None
    }

@api_router.get("/documents/{doc_id}")
async def get_document(doc_id: str, current_user: dict = Depends(get_current_user)):
    query = {"id": doc_id}
    if current_user['role'] == 'supplier':
        query['supplier_id'] = current_user['id']
    
    doc = await db.documents.find_one(query, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@api_router.get("/documents/{doc_id}/download")
async def download_document(doc_id: str, current_user: dict = Depends(get_current_user)):
    query = {"id": doc_id}
    if current_user['role'] == 'supplier':
        query['supplier_id'] = current_user['id']
    
    doc = await db.documents.find_one(query, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = Path(doc['file_path'])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    return FileResponse(
        path=str(file_path),
        filename=doc['original_name'],
        media_type=doc['file_type']
    )

@api_router.put("/documents/{doc_id}")
async def update_document(
    doc_id: str,
    doc_data: DocumentUpdate,
    current_user: dict = Depends(get_current_user)
):
    query = {"id": doc_id}
    if current_user['role'] == 'supplier':
        query['supplier_id'] = current_user['id']
    
    doc = await db.documents.find_one(query, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    updates = {}
    changes = []
    
    if doc_data.original_name is not None and doc_data.original_name != doc.get('original_name'):
        changes.append({"field": "original_name", "old": doc.get('original_name'), "new": doc_data.original_name})
        updates['original_name'] = doc_data.original_name
    
    if doc_data.parent_part_ids is not None:
        old_ids = doc.get('parent_part_ids', [])
        if set(old_ids) != set(doc_data.parent_part_ids):
            changes.append({"field": "parent_part_ids", "old": old_ids, "new": doc_data.parent_part_ids})
            updates['parent_part_ids'] = doc_data.parent_part_ids
            
            # Remove from old parts
            for pid in old_ids:
                if pid not in doc_data.parent_part_ids:
                    await db.parent_parts.update_one(
                        {"id": pid},
                        {"$pull": {"document_ids": doc_id}}
                    )
            # Add to new parts
            for pid in doc_data.parent_part_ids:
                if pid not in old_ids:
                    await db.parent_parts.update_one(
                        {"id": pid},
                        {"$addToSet": {"document_ids": doc_id}}
                    )
    
    if doc_data.child_part_ids is not None:
        old_ids = doc.get('child_part_ids', [])
        if set(old_ids) != set(doc_data.child_part_ids):
            changes.append({"field": "child_part_ids", "old": old_ids, "new": doc_data.child_part_ids})
            updates['child_part_ids'] = doc_data.child_part_ids
            
            # Update child parts in parent parts
            parts = await db.parent_parts.find({"supplier_id": current_user['id']}, {"_id": 0}).to_list(10000)
            for part in parts:
                updated = False
                child_parts = part.get('child_parts', [])
                for cp in child_parts:
                    cp_id = cp.get('id')
                    if 'document_ids' not in cp:
                        cp['document_ids'] = []
                    
                    # Remove if was in old but not in new
                    if cp_id in old_ids and cp_id not in doc_data.child_part_ids:
                        if doc_id in cp['document_ids']:
                            cp['document_ids'].remove(doc_id)
                            updated = True
                    
                    # Add if in new but not in old
                    if cp_id in doc_data.child_part_ids and cp_id not in old_ids:
                        if doc_id not in cp['document_ids']:
                            cp['document_ids'].append(doc_id)
                            updated = True
                
                if updated:
                    await db.parent_parts.update_one(
                        {"id": part['id']},
                        {"$set": {"child_parts": child_parts}}
                    )
    
    if updates:
        updates['updated_at'] = datetime.now(timezone.utc).isoformat()
        await db.documents.update_one({"id": doc_id}, {"$set": updates})
        
        await create_audit_log(
            user_id=current_user['id'],
            user_email=current_user['email'],
            action="update",
            entity_type="document",
            entity_id=doc_id,
            supplier_id=current_user['id'] if current_user['role'] == 'supplier' else None,
            field_changes=changes
        )
    
    return {"success": True}

@api_router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, current_user: dict = Depends(get_current_user)):
    query = {"id": doc_id}
    if current_user['role'] == 'supplier':
        query['supplier_id'] = current_user['id']
    
    doc = await db.documents.find_one(query, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Remove file from disk
    file_path = Path(doc['file_path'])
    if file_path.exists():
        file_path.unlink()
    
    # Remove document reference from parts
    await db.parent_parts.update_many(
        {"document_ids": doc_id},
        {"$pull": {"document_ids": doc_id}}
    )
    
    # Remove from child parts
    parts = await db.parent_parts.find({"child_parts.document_ids": doc_id}, {"_id": 0}).to_list(10000)
    for part in parts:
        child_parts = part.get('child_parts', [])
        for cp in child_parts:
            if 'document_ids' in cp and doc_id in cp['document_ids']:
                cp['document_ids'].remove(doc_id)
        await db.parent_parts.update_one(
            {"id": part['id']},
            {"$set": {"child_parts": child_parts}}
        )
    
    await db.documents.delete_one({"id": doc_id})
    
    await create_audit_log(
        user_id=current_user['id'],
        user_email=current_user['email'],
        action="delete",
        entity_type="document",
        entity_id=doc_id,
        supplier_id=current_user['id'] if current_user['role'] == 'supplier' else None,
        field_changes=[{"field": "filename", "old": doc.get('original_name')}]
    )
    
    return {"success": True}

# ===== IMPORT/EXPORT ROUTES =====

@api_router.get("/export/template")
async def download_template(current_user: dict = Depends(get_current_user)):
    # Create Excel template
    df = pd.DataFrame(columns=[
        'parent_sku', 'parent_name', 'parent_description', 'parent_country_of_origin',
        'parent_total_weight_kg', 'parent_total_value_usd',
        'child_identifier', 'child_name', 'child_description', 'child_country_of_origin',
        'child_weight_kg', 'child_value_usd', 'child_aluminum_percent', 'child_steel_percent',
        'child_has_russian_content', 'child_russian_percent', 'child_russian_description',
        'child_manufacturing_method'
    ])
    
    # Add example row
    example = {
        'parent_sku': 'SKU-001',
        'parent_name': 'ATV Frame Assembly',
        'parent_description': 'Main frame for ATV model X',
        'parent_country_of_origin': 'USA',
        'parent_total_weight_kg': 25.5,
        'parent_total_value_usd': 500.00,
        'child_identifier': 'COMP-001',
        'child_name': 'Steel Frame Tube',
        'child_description': 'Main structural tube',
        'child_country_of_origin': 'USA',
        'child_weight_kg': 5.0,
        'child_value_usd': 50.00,
        'child_aluminum_percent': 0,
        'child_steel_percent': 95,
        'child_has_russian_content': False,
        'child_russian_percent': 0,
        'child_russian_description': '',
        'child_manufacturing_method': 'Welded'
    }
    df = pd.concat([df, pd.DataFrame([example])], ignore_index=True)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Parts Template', index=False)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=parts_template.xlsx'}
    )

@api_router.post("/import/excel")
async def import_excel(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Please upload an Excel file")
    
    content = await file.read()
    df = pd.read_excel(io.BytesIO(content))
    
    results = {
        "created_parents": 0,
        "updated_parents": 0,
        "created_children": 0,
        "updated_children": 0,
        "errors": []
    }
    
    # Group by parent SKU
    if 'parent_sku' not in df.columns:
        raise HTTPException(status_code=400, detail="Missing 'parent_sku' column")
    
    for parent_sku in df['parent_sku'].unique():
        if pd.isna(parent_sku):
            continue
            
        parent_rows = df[df['parent_sku'] == parent_sku]
        first_row = parent_rows.iloc[0]
        
        try:
            # Check if parent exists
            existing_parent = await db.parent_parts.find_one({
                "sku": str(parent_sku),
                "supplier_id": current_user['id']
            })
            
            if existing_parent:
                # Update parent
                updates = {}
                if pd.notna(first_row.get('parent_name')):
                    updates['name'] = str(first_row['parent_name'])
                if pd.notna(first_row.get('parent_description')):
                    updates['description'] = str(first_row['parent_description'])
                if pd.notna(first_row.get('parent_country_of_origin')):
                    updates['country_of_origin'] = str(first_row['parent_country_of_origin'])
                if pd.notna(first_row.get('parent_total_weight_kg')):
                    updates['total_weight_kg'] = float(first_row['parent_total_weight_kg'])
                if pd.notna(first_row.get('parent_total_value_usd')):
                    updates['total_value_usd'] = float(first_row['parent_total_value_usd'])
                
                if updates:
                    updates['updated_at'] = datetime.now(timezone.utc).isoformat()
                    await db.parent_parts.update_one(
                        {"id": existing_parent['id']},
                        {"$set": updates}
                    )
                    results['updated_parents'] += 1
                
                parent_id = existing_parent['id']
            else:
                # Create parent
                parent = ParentPart(
                    sku=str(parent_sku),
                    name=str(first_row.get('parent_name', parent_sku)),
                    description=str(first_row.get('parent_description', '')) if pd.notna(first_row.get('parent_description')) else None,
                    supplier_id=current_user['id'],
                    country_of_origin=str(first_row.get('parent_country_of_origin', '')) if pd.notna(first_row.get('parent_country_of_origin')) else None,
                    total_weight_kg=float(first_row.get('parent_total_weight_kg', 0)) if pd.notna(first_row.get('parent_total_weight_kg')) else 0,
                    total_value_usd=float(first_row.get('parent_total_value_usd', 0)) if pd.notna(first_row.get('parent_total_value_usd')) else 0
                )
                
                parent_dict = parent.model_dump()
                parent_dict['created_at'] = parent_dict['created_at'].isoformat()
                parent_dict['updated_at'] = parent_dict['updated_at'].isoformat()
                
                await db.parent_parts.insert_one(parent_dict)
                results['created_parents'] += 1
                parent_id = parent.id
            
            # Process child parts
            for _, row in parent_rows.iterrows():
                if pd.isna(row.get('child_identifier')):
                    continue
                
                child_identifier = str(row['child_identifier'])
                
                # Check if child exists
                parent_doc = await db.parent_parts.find_one({"id": parent_id}, {"_id": 0})
                existing_child = None
                existing_child_index = None
                
                for i, cp in enumerate(parent_doc.get('child_parts', [])):
                    if cp.get('identifier') == child_identifier:
                        existing_child = cp
                        existing_child_index = i
                        break
                
                if existing_child:
                    # Update child
                    child_parts = parent_doc.get('child_parts', [])
                    
                    if pd.notna(row.get('child_name')):
                        child_parts[existing_child_index]['name'] = str(row['child_name'])
                    if pd.notna(row.get('child_description')):
                        child_parts[existing_child_index]['description'] = str(row['child_description'])
                    if pd.notna(row.get('child_country_of_origin')):
                        child_parts[existing_child_index]['country_of_origin'] = str(row['child_country_of_origin'])
                    if pd.notna(row.get('child_weight_kg')):
                        child_parts[existing_child_index]['weight_kg'] = float(row['child_weight_kg'])
                        child_parts[existing_child_index]['weight_lbs'] = float(row['child_weight_kg']) * 2.20462
                    if pd.notna(row.get('child_value_usd')):
                        child_parts[existing_child_index]['value_usd'] = float(row['child_value_usd'])
                    if pd.notna(row.get('child_aluminum_percent')):
                        child_parts[existing_child_index]['aluminum_content_percent'] = float(row['child_aluminum_percent'])
                    if pd.notna(row.get('child_steel_percent')):
                        child_parts[existing_child_index]['steel_content_percent'] = float(row['child_steel_percent'])
                    if pd.notna(row.get('child_has_russian_content')):
                        child_parts[existing_child_index]['has_russian_content'] = bool(row['child_has_russian_content'])
                    if pd.notna(row.get('child_russian_percent')):
                        child_parts[existing_child_index]['russian_content_percent'] = float(row['child_russian_percent'])
                    if pd.notna(row.get('child_russian_description')):
                        child_parts[existing_child_index]['russian_content_description'] = str(row['child_russian_description'])
                    if pd.notna(row.get('child_manufacturing_method')):
                        child_parts[existing_child_index]['manufacturing_method'] = str(row['child_manufacturing_method'])
                    
                    child_parts[existing_child_index]['updated_at'] = datetime.now(timezone.utc).isoformat()
                    
                    # Check completion
                    cp = child_parts[existing_child_index]
                    child_parts[existing_child_index]['is_complete'] = all([
                        cp.get('identifier'),
                        cp.get('name'),
                        cp.get('country_of_origin'),
                        cp.get('weight_kg', 0) > 0,
                        cp.get('value_usd', 0) > 0
                    ])
                    
                    await db.parent_parts.update_one(
                        {"id": parent_id},
                        {"$set": {"child_parts": child_parts, "updated_at": datetime.now(timezone.utc).isoformat()}}
                    )
                    results['updated_children'] += 1
                else:
                    # Create child
                    child = ChildPart(
                        identifier=child_identifier,
                        name=str(row.get('child_name', child_identifier)) if pd.notna(row.get('child_name')) else child_identifier,
                        description=str(row.get('child_description', '')) if pd.notna(row.get('child_description')) else None,
                        country_of_origin=str(row.get('child_country_of_origin', '')) if pd.notna(row.get('child_country_of_origin')) else '',
                        weight_kg=float(row.get('child_weight_kg', 0)) if pd.notna(row.get('child_weight_kg')) else 0,
                        value_usd=float(row.get('child_value_usd', 0)) if pd.notna(row.get('child_value_usd')) else 0,
                        aluminum_content_percent=float(row.get('child_aluminum_percent', 0)) if pd.notna(row.get('child_aluminum_percent')) else 0,
                        steel_content_percent=float(row.get('child_steel_percent', 0)) if pd.notna(row.get('child_steel_percent')) else 0,
                        has_russian_content=bool(row.get('child_has_russian_content', False)) if pd.notna(row.get('child_has_russian_content')) else False,
                        russian_content_percent=float(row.get('child_russian_percent', 0)) if pd.notna(row.get('child_russian_percent')) else 0,
                        russian_content_description=str(row.get('child_russian_description', '')) if pd.notna(row.get('child_russian_description')) else None,
                        manufacturing_method=str(row.get('child_manufacturing_method', '')) if pd.notna(row.get('child_manufacturing_method')) else None
                    )
                    child.weight_lbs = child.weight_kg * 2.20462
                    child.is_complete = all([
                        child.identifier,
                        child.name,
                        child.country_of_origin,
                        child.weight_kg > 0,
                        child.value_usd > 0
                    ])
                    
                    child_dict = child.model_dump()
                    child_dict['created_at'] = child_dict['created_at'].isoformat()
                    child_dict['updated_at'] = child_dict['updated_at'].isoformat()
                    
                    await db.parent_parts.update_one(
                        {"id": parent_id},
                        {
                            "$push": {"child_parts": child_dict},
                            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
                        }
                    )
                    results['created_children'] += 1
            
            # Recalculate parent status
            updated_parent = await db.parent_parts.find_one({"id": parent_id}, {"_id": 0})
            new_status = calculate_part_status(updated_parent)
            await db.parent_parts.update_one({"id": parent_id}, {"$set": {"status": new_status}})
                    
        except Exception as e:
            results['errors'].append(f"Error processing SKU {parent_sku}: {str(e)}")
    
    await create_audit_log(
        user_id=current_user['id'],
        user_email=current_user['email'],
        action="import",
        entity_type="batch_import",
        entity_id=str(uuid.uuid4()),
        supplier_id=current_user['id'] if current_user['role'] == 'supplier' else None,
        field_changes=[{
            "field": "import_results",
            "new": f"Parents: {results['created_parents']} created, {results['updated_parents']} updated. Children: {results['created_children']} created, {results['updated_children']} updated."
        }]
    )
    
    return results

@api_router.get("/export/parts")
async def export_parts(current_user: dict = Depends(get_current_user)):
    query = {}
    if current_user['role'] == 'supplier':
        query['supplier_id'] = current_user['id']
    
    parts = await db.parent_parts.find(query, {"_id": 0}).to_list(10000)
    
    rows = []
    for part in parts:
        for child in part.get('child_parts', []):
            rows.append({
                'parent_sku': part.get('sku'),
                'parent_name': part.get('name'),
                'parent_description': part.get('description'),
                'parent_country_of_origin': part.get('country_of_origin'),
                'parent_total_weight_kg': part.get('total_weight_kg'),
                'parent_total_value_usd': part.get('total_value_usd'),
                'parent_status': part.get('status'),
                'child_identifier': child.get('identifier'),
                'child_name': child.get('name'),
                'child_description': child.get('description'),
                'child_country_of_origin': child.get('country_of_origin'),
                'child_weight_kg': child.get('weight_kg'),
                'child_weight_lbs': child.get('weight_lbs'),
                'child_value_usd': child.get('value_usd'),
                'child_aluminum_percent': child.get('aluminum_content_percent'),
                'child_steel_percent': child.get('steel_content_percent'),
                'child_has_russian_content': child.get('has_russian_content'),
                'child_russian_percent': child.get('russian_content_percent'),
                'child_russian_description': child.get('russian_content_description'),
                'child_manufacturing_method': child.get('manufacturing_method'),
                'child_is_complete': child.get('is_complete')
            })
        
        # If no children, still include the parent
        if not part.get('child_parts'):
            rows.append({
                'parent_sku': part.get('sku'),
                'parent_name': part.get('name'),
                'parent_description': part.get('description'),
                'parent_country_of_origin': part.get('country_of_origin'),
                'parent_total_weight_kg': part.get('total_weight_kg'),
                'parent_total_value_usd': part.get('total_value_usd'),
                'parent_status': part.get('status')
            })
    
    df = pd.DataFrame(rows)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Parts Export', index=False)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename=parts_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'}
    )

# ===== AUDIT LOG ROUTES (Admin only) =====

@api_router.get("/audit-logs")
async def get_audit_logs(
    supplier_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    admin: dict = Depends(get_admin_user)
):
    query = {}
    
    if supplier_id:
        query['supplier_id'] = supplier_id
    if entity_type:
        query['entity_type'] = entity_type
    if start_date:
        query['timestamp'] = {"$gte": start_date}
    if end_date:
        if 'timestamp' in query:
            query['timestamp']['$lte'] = end_date
        else:
            query['timestamp'] = {"$lte": end_date}
    
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    return logs

@api_router.get("/audit-logs/export")
async def export_audit_logs(
    supplier_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin: dict = Depends(get_admin_user)
):
    query = {}
    
    if supplier_id:
        query['supplier_id'] = supplier_id
    if entity_type:
        query['entity_type'] = entity_type
    if start_date:
        query['timestamp'] = {"$gte": start_date}
    if end_date:
        if 'timestamp' in query:
            query['timestamp']['$lte'] = end_date
        else:
            query['timestamp'] = {"$lte": end_date}
    
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(100000)
    
    rows = []
    for log in logs:
        rows.append({
            'timestamp': log.get('timestamp'),
            'user_email': log.get('user_email'),
            'action': log.get('action'),
            'entity_type': log.get('entity_type'),
            'entity_id': log.get('entity_id'),
            'changes': json.dumps(log.get('field_changes', []))
        })
    
    df = pd.DataFrame(rows)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Audit Logs', index=False)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename=audit_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'}
    )

# ===== SEARCH ROUTE =====

@api_router.get("/search")
async def search_parts(
    q: str = Query(..., min_length=1),
    current_user: dict = Depends(get_current_user)
):
    query = {
        "$or": [
            {"sku": {"$regex": q, "$options": "i"}},
            {"name": {"$regex": q, "$options": "i"}},
            {"child_parts.identifier": {"$regex": q, "$options": "i"}},
            {"child_parts.name": {"$regex": q, "$options": "i"}}
        ]
    }
    
    if current_user['role'] == 'supplier':
        query['supplier_id'] = current_user['id']
    
    parts = await db.parent_parts.find(query, {"_id": 0}).to_list(100)
    return parts

# ===== SEED DATA ROUTE =====

@api_router.post("/seed-data")
async def seed_data():
    """Create dummy data for testing"""
    
    # Create admin user
    admin_exists = await db.users.find_one({"email": "admin@rvparts.com"})
    if not admin_exists:
        admin = User(
            email="admin@rvparts.com",
            name="Admin User",
            role="admin",
            company_name="RV Parts International"
        )
        admin_dict = admin.model_dump()
        admin_dict['password_hash'] = hash_password("admin123")
        admin_dict['created_at'] = admin_dict['created_at'].isoformat()
        admin_dict['updated_at'] = admin_dict['updated_at'].isoformat()
        await db.users.insert_one(admin_dict)
    
    # Create supplier users
    suppliers_data = [
        {"email": "supplier1@metalworks.com", "name": "John Smith", "company": "MetalWorks Inc."},
        {"email": "supplier2@plasticspro.com", "name": "Sarah Johnson", "company": "Plastics Pro LLC"},
        {"email": "supplier3@autosupply.com", "name": "Mike Chen", "company": "Auto Supply Co."}
    ]
    
    supplier_ids = []
    for sd in suppliers_data:
        existing = await db.users.find_one({"email": sd['email']})
        if existing:
            supplier_ids.append(existing['id'])
        else:
            supplier = User(
                email=sd['email'],
                name=sd['name'],
                role="supplier",
                company_name=sd['company']
            )
            supplier_dict = supplier.model_dump()
            supplier_dict['password_hash'] = hash_password("supplier123")
            supplier_dict['created_at'] = supplier_dict['created_at'].isoformat()
            supplier_dict['updated_at'] = supplier_dict['updated_at'].isoformat()
            await db.users.insert_one(supplier_dict)
            supplier_ids.append(supplier.id)
    
    # Create parts for first supplier
    if supplier_ids:
        parts_data = [
            {
                "sku": "RV-FRAME-001",
                "name": "ATV Main Frame Assembly",
                "description": "Primary structural frame for all-terrain vehicle",
                "country_of_origin": "USA",
                "total_weight_kg": 45.5,
                "total_value_usd": 1200.00,
                "children": [
                    {"identifier": "FRAME-TUBE-01", "name": "Main Frame Tube", "country": "USA", "weight": 15.0, "value": 350, "steel": 98, "method": "Welded"},
                    {"identifier": "FRAME-TUBE-02", "name": "Cross Support Tube", "country": "Canada", "weight": 8.5, "value": 200, "steel": 95, "method": "Welded"},
                    {"identifier": "FRAME-BRACKET-01", "name": "Engine Mount Bracket", "country": "USA", "weight": 5.0, "value": 150, "steel": 100, "method": "CNC Machined"},
                    {"identifier": "FRAME-GUSSET-01", "name": "Reinforcement Gusset", "country": "Mexico", "weight": 2.5, "value": 75, "steel": 90, "aluminum": 10, "method": "Stamped"},
                ]
            },
            {
                "sku": "RV-SUSP-002",
                "name": "Front Suspension Kit",
                "description": "Complete front suspension assembly with shocks",
                "country_of_origin": "USA",
                "total_weight_kg": 22.0,
                "total_value_usd": 850.00,
                "children": [
                    {"identifier": "SUSP-ARM-01", "name": "A-Arm Upper", "country": "USA", "weight": 4.5, "value": 180, "steel": 85, "aluminum": 15, "method": "Forged"},
                    {"identifier": "SUSP-ARM-02", "name": "A-Arm Lower", "country": "USA", "weight": 5.0, "value": 190, "steel": 85, "aluminum": 15, "method": "Forged"},
                    {"identifier": "SUSP-SHOCK-01", "name": "Gas Shock Absorber", "country": "Japan", "weight": 3.5, "value": 220, "steel": 70, "aluminum": 25, "method": "Assembled"},
                ]
            },
            {
                "sku": "RV-BODY-003",
                "name": "Body Panel Set",
                "description": "Complete exterior body panel kit",
                "country_of_origin": "Canada",
                "total_weight_kg": 18.0,
                "total_value_usd": 650.00,
                "children": [
                    {"identifier": "BODY-FENDER-FL", "name": "Front Left Fender", "country": "Canada", "weight": 2.2, "value": 85, "aluminum": 100, "method": "Stamped"},
                    {"identifier": "BODY-FENDER-FR", "name": "Front Right Fender", "country": "Canada", "weight": 2.2, "value": 85, "aluminum": 100, "method": "Stamped"},
                    {"identifier": "BODY-HOOD-01", "name": "Engine Hood", "country": "Canada", "weight": 4.5, "value": 150, "aluminum": 95, "method": "Stamped"},
                ]
            },
            {
                "sku": "RV-ENGINE-004",
                "name": "Engine Block Assembly",
                "description": "4-stroke engine block with components",
                "country_of_origin": "Japan",
                "total_weight_kg": 85.0,
                "total_value_usd": 3500.00,
                "children": [
                    {"identifier": "ENG-BLOCK-01", "name": "Cast Iron Block", "country": "Japan", "weight": 45.0, "value": 1500, "steel": 95, "method": "Cast"},
                    {"identifier": "ENG-HEAD-01", "name": "Cylinder Head", "country": "Japan", "weight": 12.0, "value": 650, "aluminum": 90, "method": "Cast"},
                    {"identifier": "ENG-CRANK-01", "name": "Crankshaft", "country": "Germany", "weight": 15.0, "value": 800, "steel": 100, "method": "Forged"},
                ]
            },
            {
                "sku": "RV-WHEEL-005",
                "name": "Wheel & Tire Assembly",
                "description": "Complete wheel with all-terrain tire",
                "country_of_origin": "China",
                "total_weight_kg": 25.0,
                "total_value_usd": 280.00,
                "status": "needs_review",
                "children": [
                    {"identifier": "WHEEL-RIM-01", "name": "Alloy Rim 14\"", "country": "China", "weight": 8.0, "value": 120, "aluminum": 95, "method": "Cast"},
                    {"identifier": "WHEEL-TIRE-01", "name": "AT Tire 26x9-14", "country": "Thailand", "weight": 12.0, "value": 95, "method": "Molded"},
                ]
            }
        ]
        
        for pd_item in parts_data:
            existing = await db.parent_parts.find_one({"sku": pd_item['sku'], "supplier_id": supplier_ids[0]})
            if existing:
                continue
                
            children = []
            for c in pd_item.get('children', []):
                child = ChildPart(
                    identifier=c['identifier'],
                    name=c['name'],
                    country_of_origin=c['country'],
                    weight_kg=c['weight'],
                    weight_lbs=c['weight'] * 2.20462,
                    value_usd=c['value'],
                    aluminum_content_percent=c.get('aluminum', 0),
                    steel_content_percent=c.get('steel', 0),
                    manufacturing_method=c.get('method'),
                    is_complete=True
                )
                child_dict = child.model_dump()
                child_dict['created_at'] = child_dict['created_at'].isoformat()
                child_dict['updated_at'] = child_dict['updated_at'].isoformat()
                children.append(child_dict)
            
            part = ParentPart(
                sku=pd_item['sku'],
                name=pd_item['name'],
                description=pd_item['description'],
                supplier_id=supplier_ids[0],
                country_of_origin=pd_item['country_of_origin'],
                total_weight_kg=pd_item['total_weight_kg'],
                total_value_usd=pd_item['total_value_usd'],
                child_parts=children,
                status=pd_item.get('status', 'incomplete')
            )
            
            part_dict = part.model_dump()
            part_dict['created_at'] = part_dict['created_at'].isoformat()
            part_dict['updated_at'] = part_dict['updated_at'].isoformat()
            
            # Recalculate status
            new_status = calculate_part_status(part_dict)
            part_dict['status'] = new_status
            
            await db.parent_parts.insert_one(part_dict)
    
    return {
        "message": "Seed data created successfully",
        "admin_credentials": {"email": "admin@rvparts.com", "password": "admin123"},
        "supplier_credentials": {"email": "supplier1@metalworks.com", "password": "supplier123"}
    }

# ===== ROOT ROUTE =====

@api_router.get("/")
async def root():
    return {"message": "Automotive Parts Supplier Portal API", "version": "1.0.0"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
