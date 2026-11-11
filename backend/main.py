import os
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI(
    title="Microsegmentation Lab API",
    version="2.0.0",
    description="Backend API phục vụ hệ thống phân đoạn vi mô Zero-Trust"
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lấy thông tin kết nối từ biến môi trường Kubernetes
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://dbuser:securepass@database:5432/appdb"
)

def get_db_connection():
    """Tạo kết nối tới PostgreSQL với RealDictCursor để trả về JSON dạng key-value"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# Tự động khởi tạo bảng cơ sở dữ liệu khi khởi động ứng dụng
@app.on_event("startup")
def startup_database():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                price NUMERIC(12, 2) NOT NULL CHECK (price >= 0),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print(" [INFO] Khởi tạo bảng 'products' trong PostgreSQL thành công!")
    except Exception as e:
        print(f" [ERROR] Lỗi kết nối hoặc khởi tạo DB: {e}")

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Tên sản phẩm")
    price: float = Field(..., gt=0, description="Giá sản phẩm phải lớn hơn 0")

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "healthy", "service": "backend-api"}

@app.get("/items", tags=["Products"])
def get_products():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, price, created_at FROM products ORDER BY id DESC;")
        items = cur.fetchall()
        cur.close()
        conn.close()
        return items
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi truy vấn cơ sở dữ liệu: {str(e)}"
        )

@app.post("/items", status_code=status.HTTP_201_CREATED, tags=["Products"])
def create_product(product: ProductCreate):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO products (name, price) VALUES (%s, %s) RETURNING id, name, price, created_at;",
            (product.name, product.price)
        )
        new_item = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return new_item
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Không thể thêm sản phẩm: {str(e)}"
        )

@app.delete("/items/{product_id}", tags=["Products"])
def delete_product(product_id: int):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE id = %s RETURNING id;", (product_id,))
        deleted = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if not deleted:
            raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm cần xóa")
        return {"message": "Đã xóa sản phẩm thành công", "id": product_id}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi xóa sản phẩm: {str(e)}"
        )