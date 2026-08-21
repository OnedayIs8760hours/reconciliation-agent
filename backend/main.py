from pathlib import Path
import sys

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 项目根目录：确保以脚本方式运行时，也能正确导入 backend 下的模块。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.api.router import router


# 创建 FastAPI 应用实例。
app = FastAPI()

# 注册 CORS 中间件：允许前端开发服务器跨域访问后端接口。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://192.168.0.26:5173", "http://192.168.0.26:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由。
app.include_router(router)


# 本地直接运行入口：启动 Uvicorn 开发服务器。
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=6161, reload=True)
