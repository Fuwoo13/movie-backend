from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from pydantic import BaseModel
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from typing import Optional
import os
import hashlib # 🌟 비밀번호 암호화를 위해 추가된 기본 라이브러리

app = FastAPI(title="영화 추천 API - 협업필터링 + 로그인 기능")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Render 환경변수에서 주소를 가져옵니다.
DB_URL = os.getenv("DB_URL")
engine = create_engine(DB_URL, connect_args={'ssl': {}})
try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(50) UNIQUE"))
except:
    pass # 칸이 이미 있으면 그냥 통과!

try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN password VARCHAR(255)"))
except:
    pass # 칸이 이미 있으면 그냥 통과!

# --- 🧠 메모리 다이어트를 한 AI 엔진 2.0 ---
print("데이터 불러오는 중...")
movies_df = pd.read_sql("SELECT movie_id, title, genres FROM movies", engine)
ratings_df = pd.read_sql("SELECT user_id, movie_id, rating FROM ratings", engine)

user_item_matrix = ratings_df.pivot_table(index='movie_id', columns='user_id', values='rating', aggfunc='mean').fillna(0)
print("메모리 최적화 완료! 서버 정상 작동 시작 🚀")
# ----------------------------------------------------------------

# 🌟 기존 별점 모델
class Rating(BaseModel):
    user_id: int
    movie_id: int
    rating: float

# 🌟 새로 추가된 유저 모델 (회원가입/로그인용)
class UserAuth(BaseModel):
    username: str
    password: str

@app.post("/rate")
def save_rating(rating_data: Rating):
    query = text("""
        INSERT INTO ratings (user_id, movie_id, rating) 
        VALUES (:user_id, :movie_id, :rating)
    """)
    with engine.begin() as conn:
        conn.execute(query, {
            "user_id": rating_data.user_id,
            "movie_id": rating_data.movie_id,
            "rating": rating_data.rating
        })
    return {"message": f"{rating_data.movie_id}번 영화에 {rating_data.rating}점이 저장되었습니다!"}

@app.get("/")
def read_root():
    return {"message": "업그레이드된 AI 영화 추천 서버입니다! (로그인 지원)"}

@app.get("/movies")
def get_movies(skip: int = 0, limit: int = 20, search: Optional[str] = ""):
    filtered_df = movies_df[movies_df['title'].str.contains(search, case=False, na=False)]
    paginated_df = filtered_df.iloc[skip : skip + limit]
    return paginated_df[['movie_id', 'title', 'genres']].to_dict('records')

@app.get("/recommend/{movie_id}")
def get_recommendations(movie_id: int):
    if movie_id not in user_item_matrix.index:
         return []

    target_movie_vector = user_item_matrix.loc[movie_id].values.reshape(1, -1)
    sim_scores = cosine_similarity(user_item_matrix, target_movie_vector).flatten()
    sim_series = pd.Series(sim_scores, index=user_item_matrix.index)
    
    top_5_ids = sim_series.sort_values(ascending=False).iloc[1:6].index.tolist()
    
    recommendations = []
    for mid in top_5_ids:
        movie_info = movies_df[movies_df['movie_id'] == mid].iloc[0]
        recommendations.append({
            "movie_id": int(movie_info['movie_id']),
            "title": movie_info['title'],
            "genres": movie_info['genres']
        })
        
    return recommendations

# =========================================================
# 🌟 신규 기능: 회원가입 및 로그인 로직
# =========================================================

# 비밀번호를 안전하게 해싱(암호화)하는 함수
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

@app.post("/signup")
def signup(user: UserAuth):
    check_query = text("SELECT user_id FROM users WHERE username = :username")
    insert_query = text("INSERT INTO users (username, password) VALUES (:username, :password)")
    
    with engine.begin() as conn:
        # 1. 이미 존재하는 아이디인지 검사
        existing_user = conn.execute(check_query, {"username": user.username}).fetchone()
        if existing_user:
            return {"success": False, "message": "이미 존재하는 아이디입니다."}
        
        # 2. 비밀번호 암호화 후 DB에 저장
        hashed_pw = hash_password(user.password)
        conn.execute(insert_query, {"username": user.username, "password": hashed_pw})
        
    return {"success": True, "message": "회원가입이 완료되었습니다!"}

@app.post("/login")
def login(user: UserAuth):
    query = text("SELECT user_id, password FROM users WHERE username = :username")
    
    with engine.connect() as conn:
        result = conn.execute(query, {"username": user.username}).fetchone()
        
        # 1. 아이디가 존재하지 않는 경우
        if not result:
            return {"success": False, "message": "존재하지 않는 아이디입니다."}
        
        # 2. 비밀번호 검증
        db_user_id = result[0]
        db_password = result[1]
        
        if db_password == hash_password(user.password):
            return {"success": True, "user_id": db_user_id, "message": "로그인 성공!"}
        else:
            return {"success": False, "message": "비밀번호가 틀렸습니다."}