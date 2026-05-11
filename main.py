from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from pydantic import BaseModel
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from typing import Optional
import os

app = FastAPI(title="영화 추천 API - 협업필터링")

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

# --- 🧠 메모리 다이어트를 한 AI 엔진 2.0 ---
print("데이터 불러오는 중...")
movies_df = pd.read_sql("SELECT movie_id, title, genres FROM movies", engine)
ratings_df = pd.read_sql("SELECT user_id, movie_id, rating FROM ratings", engine)

# 여기까지만 미리 만들어둡니다. (메모리 적게 차지함!)
user_item_matrix = ratings_df.pivot_table(index='movie_id', columns='user_id', values='rating', aggfunc='mean').fillna(0)
print("메모리 최적화 완료! 서버 정상 작동 시작 🚀")
# ----------------------------------------------------------------

class Rating(BaseModel):
    user_id: int
    movie_id: int
    rating: float

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
    return {"message": "업그레이드된 AI 영화 추천 서버입니다!"}

@app.get("/movies")
def get_movies(skip: int = 0, limit: int = 20, search: Optional[str] = ""):
    filtered_df = movies_df[movies_df['title'].str.contains(search, case=False, na=False)]
    paginated_df = filtered_df.iloc[skip : skip + limit]
    return paginated_df[['movie_id', 'title', 'genres']].to_dict('records')

@app.get("/recommend/{movie_id}")
def get_recommendations(movie_id: int):
    if movie_id not in user_item_matrix.index:
         return []

    # 🌟 핵심: 클릭한 영화가 들어오면, 그때서야 유사도 계산을 시작합니다!
    target_movie_vector = user_item_matrix.loc[movie_id].values.reshape(1, -1)
    
    # 클릭한 영화 1개 vs 나머지 전체 영화 비교
    sim_scores = cosine_similarity(user_item_matrix, target_movie_vector).flatten()
    
    # 점수 높은 순으로 줄 세우기
    sim_series = pd.Series(sim_scores, index=user_item_matrix.index)
    
    # 1등(자기 자신) 빼고 2~6등 영화 ID 5개 뽑기
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