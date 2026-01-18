import os
import shutil
import uuid  # 用于生成唯一的文件名，防止重名
from fastapi import APIRouter, UploadFile, File, HTTPException

# 创建一个路由器，专门处理上传相关的请求
router = APIRouter(tags=["文件上传"])

# ==========================================
# 配置：文件存哪里？
# ==========================================
# 1. 定义上传文件夹的名字
UPLOAD_DIR = "uploads"

# 2. 检查文件夹是否存在，如果不存在，代码自动创建一个
# 这样你就不用手动去新建文件夹了
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# ==========================================
# 接口：上传文件
# ==========================================
@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    【上传文件接口】
    功能：接收前端上传的图片或视频，保存到服务器本地的 uploads 文件夹中。
    
    参数:
    - file: 前端传来的文件对象 (类型是 UploadFile)
    
    返回:
    - 文件的访问 URL (例如: http://localhost:8000/uploads/abc.jpg)
    """
    
    # --- 1. 安全检查 ---
    # 检查是否有文件名
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    
    # --- 2. 生成唯一文件名 ---
    # 为什么要这样做？因为如果两个用户都传了 "photo.jpg"，后传的会覆盖先传的。
    # 解决方法：给文件起个乱码名字，比如 "f8a9...2b1c.jpg"
    
    # 获取文件后缀名 (例如 .jpg 或 .png)
    file_extension = os.path.splitext(file.filename)[1]
    
    # 生成随机文件名 (uuid4 生成一个随机的唯一ID)
    random_filename = f"{uuid.uuid4()}{file_extension}"
    
    # 拼凑出完整的保存路径 (例如: uploads/f8a9...2b1c.jpg)
    file_location = os.path.join(UPLOAD_DIR, random_filename)
    
    # --- 3. 保存文件 ---
    try:
        # 打开刚才定义好的路径，准备写入 ('wb' 表示以二进制写模式打开)
        with open(file_location, "wb") as buffer:
            # shutil.copyfileobj 是一个高效的工具，把上传的文件流拷贝到本地文件中
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        # 如果保存过程中出错（比如硬盘满了，或者没有权限），报错给前端
        raise HTTPException(status_code=500, detail=f"文件保存失败: {e}")
    finally:
        # 无论成功失败，都要关闭上传的文件流，释放内存
        file.file.close()
        
    # --- 4. 返回结果 ---
    # 告诉前端：文件保存好了，你可以通过这个 URL 访问它
    # 注意：这里的 /uploads/ 是我们在 api.py 里即将配置的“访问前缀”
    return {
        "filename": file.filename,          # 原文件名
        "url": f"/uploads/{random_filename}" # 访问链接 (相对路径)
    }