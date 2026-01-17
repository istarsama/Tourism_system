# src/auth.py
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from pydantic import BaseModel
from passlib.context import CryptContext
import jwt # 刚才装的库
from database import get_session
from models import User
#################################
# --- 0. 环境变量加载 ---
import os # 新增：用来读取系统环境变量
from dotenv import load_dotenv # 新增：用来加载 .env 文件

load_dotenv()  # 加载当前目录下的 .env 文件

# --- 配置部分 ---
# 从环境变量里取值，如果没有取到（比如文件忘了建），就报错或者用默认值
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
# 安全检查：如果没有密钥，直接阻止程序启动
if not SECRET_KEY:
    raise ValueError("❌ 严重错误：未设置 SECRET_KEY！请检查 .env 文件。")
#################################

router = APIRouter(prefix="/auth", tags=["用户认证"])

# 改用 argon2 (现在的标准)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# --- 数据模型 ---
class UserRegister(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

# --- 辅助函数 ---
def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    """制作 JWT 通行证"""
    to_encode = data.copy()
    # 通行证 7 天后过期
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- 接口定义 ---

@router.post("/register")
def register(user_data: UserRegister, session: Session = Depends(get_session)):
    # 1. 查重
    statement = select(User).where(User.username == user_data.username)
    if session.exec(statement).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 2. 创建
    new_user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password)
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return {"msg": "注册成功", "username": new_user.username}

@router.post("/login")
def login(login_data: LoginRequest, session: Session = Depends(get_session)):
    """
    登录接口：验证账号密码，返回 Token
    """
    # 1. 找人
    statement = select(User).where(User.username == login_data.username)
    user = session.exec(statement).first()
    
    # 2. 验证 (人不存在 或者 密码不对)
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="账号或密码错误")
    
    # 3. 发证 (把用户ID写进 token 里)
    access_token = create_access_token(data={"sub": str(user.id), "name": user.username})
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "msg": "登录成功！"
    }

############################
# --- cookie 与 token 的处理 ---
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError

# 1. 定义 Token 在哪里找 (OAuth2 标准是在 Header: Authorization: Bearer <token>)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    """
    这是一个依赖项函数（Dependency）。
    它的作用是：任何需要“登录”才能访问的接口，都要注入这个函数。
    它会自动从 Header 拿 Token -> 解密 -> 查数据库 -> 返回 User 对象。
    """
    credentials_exception = HTTPException(
        status_code=401,
        detail="无法验证凭证 (Token无效或已过期)",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 2. 解密 Token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except PyJWTError:
        raise credentials_exception
        
    # 3. 查数据库确认用户还在
    user = session.get(User, int(user_id))
    if user is None:
        raise credentials_exception
        
    return user