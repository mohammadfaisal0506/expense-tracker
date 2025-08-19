

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from jose import JWTError, jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from pymongo import MongoClient
from bson import ObjectId, errors
from fastapi.middleware.cors import CORSMiddleware
import os

# -----------------------------
# Config
# -----------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")

# MongoDB setup
try:
    client = MongoClient(MONGODB_URI)
    db = client["expense_tracker"]
    users_collection = db["users"]
    expenses_collection = db["expenses"]
    categories_collection = db["categories"]
    client.admin.command('ping')
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# FastAPI app
app = FastAPI(title="Expense Tracker API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Models
# -----------------------------
class UserRegister(BaseModel):
    username: str
    password: str
    full_name: str
    email: EmailStr

class UserMeResponse(BaseModel):
    user_id: str
    username: str
    full_name: str
    email: str
    role: str
    balance: float # New field

class Token(BaseModel):
    access_token: str
    token_type: str

class ExpenseCreate(BaseModel):
    amount: float
    category: str
    date: str
    description: str

class ExpenseUpdate(BaseModel):
    amount: Optional[float] = None
    category: Optional[str] = None
    date: Optional[str] = None
    description: Optional[str] = None

class CategoryCreate(BaseModel):
    name: str

class CategoryUpdate(BaseModel):
    name: str

class PromoteUserRequest(BaseModel):
    username: str
    new_role: str

class AddFundsRequest(BaseModel): # New model for adding funds
    amount: float

# -----------------------------
# Helpers
# -----------------------------
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_user(username: str):
    return users_collection.find_one({"username": username})

def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user["password"]):
        return None
    return user

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(username)
    if user is None:
        raise credentials_exception
    return user

def get_current_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

def resolve_expense_object_id(expense_id: str, current_user: dict):
    tid = str(expense_id).strip()
    try:
        return ObjectId(tid)
    except Exception:
        pass
    try:
        idx = int(tid)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid expense ID format. Provide a 24-char ObjectId or numeric index.")
    
    expenses = list(expenses_collection.find({"user_id": str(current_user["_id"]) }).sort("date", -1))
    if idx < 0 or idx >= len(expenses):
        raise HTTPException(status_code=404, detail="Expense index out of range")
    return expenses[idx]["_id"]

# -----------------------------
# Routes
# -----------------------------
@app.post("/register")
def register(user: UserRegister):
    if users_collection.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Username already registered")
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pw = get_password_hash(user.password)
    role = "user"
    result = users_collection.insert_one({
        "username": user.username,
        "password": hashed_pw,
        "full_name": user.full_name,
        "email": user.email,
        "role": role,
        "balance": 0.0 # Initialize new user balance
    })
    return {
        "id": str(result.inserted_id),
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "role": role,
        "balance": 0.0
    }

@app.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=UserMeResponse)
def read_users_me(current_user: dict = Depends(get_current_user)):
    return {
        "user_id": str(current_user["_id"]),
        "username": current_user["username"],
        "full_name": current_user.get("full_name"),
        "email": current_user.get("email"),
        "role": current_user["role"],
        "balance": current_user.get("balance", 0.0)
    }

# -----------------------------
# Expense Endpoints
# -----------------------------
@app.post("/expenses")
def add_expense(expense: ExpenseCreate, current_user: dict = Depends(get_current_user)):
    # Check for sufficient funds
    if current_user.get("balance", 0.0) < expense.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds to record this expense.")

    if not categories_collection.find_one({"name": expense.category}):
        raise HTTPException(status_code=400, detail="Invalid category")

    doc = {
        "user_id": str(current_user["_id"]),
        "amount": expense.amount,
        "category": expense.category,
        "date": expense.date,
        "description": expense.description
    }
    result = expenses_collection.insert_one(doc)
    
    # Deduct expense amount from user's balance
    users_collection.update_one({"_id": current_user["_id"]}, {"$inc": {"balance": -expense.amount}})
    
    return {"message": "Expense added successfully", "expense_id": str(result.inserted_id)}


@app.get("/expenses")
def get_expenses(
    category: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {"user_id": str(current_user["_id"]) }
    if category:
        query["category"] = category
    if start and end:
        query["date"] = {"$gte": start, "$lte": end}
    elif start:
        query["date"] = {"$gte": start}
    elif end:
        query["date"] = {"$lte": end}

    expenses = list(expenses_collection.find(query).sort("date", -1))
    out = []
    for e in expenses:
        e_id = str(e.get("_id"))
        out.append({
            "_id": e_id,
            "id": e_id,
            "user_id": str(e.get("user_id")),
            "amount": e.get("amount"),
            "category": e.get("category"),
            "date": e.get("date"),
            "description": e.get("description")
        })
    return out


@app.get("/expenses/{expense_id}")
def get_expense(expense_id: str, current_user: dict = Depends(get_current_user)):
    obj_id = resolve_expense_object_id(expense_id, current_user)
    doc = expenses_collection.find_one({"_id": obj_id, "user_id": str(current_user["_id"])})
    if not doc:
        raise HTTPException(status_code=404, detail="Expense not found or not authorized")
    doc_id = str(doc.get("_id"))
    return {
        "_id": doc_id,
        "id": doc_id,
        "user_id": str(doc.get("user_id")),
        "amount": doc.get("amount"),
        "category": doc.get("category"),
        "date": doc.get("date"),
        "description": doc.get("description")
    }


@app.put("/expenses/{expense_id}")
def update_expense(expense_id: str, expense: ExpenseUpdate, current_user: dict = Depends(get_current_user)):
    obj_id = resolve_expense_object_id(expense_id, current_user)
    doc = expenses_collection.find_one({"_id": obj_id, "user_id": str(current_user["_id"])})
    if not doc:
        raise HTTPException(status_code=404, detail="Expense not found or not authorized")
    
    original_amount = doc.get("amount")
    update_data = {k: v for k, v in expense.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "category" in update_data and not categories_collection.find_one({"name": update_data["category"]}):
        raise HTTPException(status_code=400, detail="Invalid category")
    
    new_amount = update_data.get("amount", original_amount)
    amount_change = new_amount - original_amount
    
    if current_user.get("balance", 0.0) < amount_change:
        raise HTTPException(status_code=400, detail="Insufficient funds to update expense to this amount.")

    result = expenses_collection.update_one({"_id": obj_id, "user_id": str(current_user["_id"])}, {"$set": update_data})
    
    if result.matched_count > 0:
        users_collection.update_one({"_id": current_user["_id"]}, {"$inc": {"balance": -amount_change}})
        return {"message": "Expense updated successfully"}
    
    raise HTTPException(status_code=404, detail="Expense not found or not authorized")


@app.delete("/expenses/{expense_id}")
def delete_expense(expense_id: str, current_user: dict = Depends(get_current_user)):
    obj_id = resolve_expense_object_id(expense_id, current_user)
    doc = expenses_collection.find_one({"_id": obj_id, "user_id": str(current_user["_id"])})
    if not doc:
        raise HTTPException(status_code=404, detail="Expense not found or not authorized")
        
    result = expenses_collection.delete_one({"_id": obj_id, "user_id": str(current_user["_id"])})
    
    if result.deleted_count > 0:
        # Add the amount back to the user's balance
        users_collection.update_one({"_id": current_user["_id"]}, {"$inc": {"balance": doc.get("amount")}})
        return {"message": "Expense deleted successfully"}
    
    raise HTTPException(status_code=404, detail="Expense not found or not authorized")

# -----------------------------
# Funds Endpoints
# -----------------------------
@app.post("/funds")
def add_funds(funds: AddFundsRequest, current_user: dict = Depends(get_current_user)):
    if funds.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    result = users_collection.update_one({"_id": current_user["_id"]}, {"$inc": {"balance": funds.amount}})
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    updated_user = users_collection.find_one({"_id": current_user["_id"]})
    return {"message": "Funds added successfully", "new_balance": updated_user.get("balance")}


# -----------------------------
# Other Endpoints (Categories, Admin) - remain unchanged
# -----------------------------
@app.get("/categories")
def get_categories(current_user: dict = Depends(get_current_user)):
    categories = list(categories_collection.find())
    out = []
    for c in categories:
        cid = str(c.get("_id"))
        out.append({"_id": cid, "id": cid, "name": c.get("name")})
    return out


@app.post("/categories")
def create_category(category: CategoryCreate, current_user: dict = Depends(get_current_admin)):
    if categories_collection.find_one({"name": category.name}):
        raise HTTPException(status_code=400, detail="Category already exists")
    result = categories_collection.insert_one({"name": category.name})
    return {"message": "Category created successfully", "id": str(result.inserted_id)}


@app.put("/categories/{category_id}")
def update_category(category_id: str, category: CategoryUpdate, current_user: dict = Depends(get_current_admin)):
    try:
        obj_id = ObjectId(category_id)
    except errors.InvalidId:
        raise HTTPException(status_code=400, detail="Invalid category ID")
    result = categories_collection.update_one({"_id": obj_id}, {"$set": {"name": category.name}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"message": "Category updated successfully"}


@app.delete("/categories/{category_id}")
def delete_category(category_id: str, current_user: dict = Depends(get_current_admin)):
    try:
        obj_id = ObjectId(category_id)
    except errors.InvalidId:
        raise HTTPException(status_code=400, detail="Invalid category ID")
    result = categories_collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"message": "Category deleted successfully"}


@app.get("/admin/users")
def list_users(current_user: dict = Depends(get_current_admin)):
    users = list(users_collection.find({}, {"password": 0}))
    out = []
    for u in users:
        uid = str(u.get("_id"))
        out.append({"_id": uid, "id": uid, "username": u.get("username"), "full_name": u.get("full_name"), "email": u.get("email"), "role": u.get("role"), "balance": u.get("balance")})
    return out


@app.delete("/admin/users/{username}")
def delete_user(username: str, current_user: dict = Depends(get_current_admin)):
    user_to_delete = users_collection.find_one({"username": username})
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User not found")
    
    expenses_collection.delete_many({"user_id": str(user_to_delete["_id"])})
    users_collection.delete_one({"_id": user_to_delete["_id"]})
    
    return {"message": f"User {username} and their expenses deleted successfully"}


@app.post("/admin/promote")
def promote_user(request: PromoteUserRequest, current_user: dict = Depends(get_current_admin)):
    if request.new_role not in ["user", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    result = users_collection.update_one({"username": request.username}, {"$set": {"role": request.new_role}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": f"User {request.username} promoted to {request.new_role}"}


@app.get("/admin/expenses")
def admin_get_expenses(
    category: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    current_user: dict = Depends(get_current_admin)
):
    query = {}
    if category:
        query["category"] = category
    if start and end:
        query["date"] = {"$gte": start, "$lte": end}
    elif start:
        query["date"] = {"$gte": start}
    elif end:
        query["date"] = {"$lte": end}

    expenses = list(expenses_collection.find(query).sort("date", -1))
    out = []
    for e in expenses:
        e_id = str(e.get("_id"))
        out.append({
            "_id": e_id,
            "id": e_id,
            "user_id": str(e.get("user_id")),
            "amount": e.get("amount"),
            "category": e.get("category"),
            "date": e.get("date"),
            "description": e.get("description")
        })

    return out
