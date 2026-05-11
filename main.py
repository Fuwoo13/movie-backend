from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text # 👈 text 추가
from pydantic import BaseModel # 👈 프론트엔드 데이터를 받기 위해 추가
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

app = FastAPI(title="영화 추천 API - 협업필터링")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_URL = "mysql+pymysql://root:vagrant@localhost:3306/movie_recommendation"
engine = create_engine(DB_URL)

# 클라이언트(React)가 보낼 데이터의 형식을 정의합니다.
class Rating(BaseModel):
    user_id: int
    movie_id: int
    rating: float

# --- 🧠 업그레이드된 AI 엔진 학습 (협업 필터링) ---
print("AI 엔진 2.0 학습 중... (10만 개 평점 데이터 분석 중)")

# 1. 영화 정보와 평점 데이터를 모두 불러옵니다.
movies_df = pd.read_sql("SELECT movie_id, title, genres FROM movies", engine)
ratings_df = pd.read_sql("SELECT user_id, movie_id, rating FROM ratings", engine)

# 2. User-Item Matrix (사용자-영화 평점 행렬) 만들기 ⭐️ 핵심!
# 세로는 영화 ID, 가로는 사용자 ID로 표를 만들고 빈칸(안 본 영화)은 0점으로 채웁니다.
user_item_matrix = ratings_df.pivot_table(index='movie_id', columns='user_id', values='rating', aggfunc='mean').fillna(0)

# 3. 영화들 간의 코사인 유사도 계산 (어떤 영화들이 비슷한 평가 패턴을 가졌는가?)
item_sim = cosine_similarity(user_item_matrix)
item_sim_df = pd.DataFrame(item_sim, index=user_item_matrix.index, columns=user_item_matrix.index)

print("AI 엔진 2.0 학습 완료! 🚀")
# ----------------------------------------------------------------

@app.get("/")
def read_root():
    return {"message": "업그레이드된 AI 영화 추천 서버입니다!"}

# 🌟 검색 및 페이징이 적용된 API
@app.get("/movies")
def get_movies(skip: int = 0, limit: int = 20, search: Optional[str] = ""):
    # 1. 검색어가 있으면 제목에서 찾기 (대소문자 무시)
    filtered_df = movies_df[movies_df['title'].str.contains(search, case=False, na=False)]
    
    # 2. skip부터 limit 개수만큼만 데이터 자르기
    paginated_df = filtered_df.iloc[skip : skip + limit]
    
    return paginated_df[['movie_id', 'title', 'genres']].to_dict('records')

@app.get("/recommend/{movie_id}")
def get_recommendations(movie_id: int):
    # 만약 평점 데이터가 없는 아주 마이너한 영화라면 예외 처리
    if movie_id not in item_sim_df.index:
         return []

    # 1. 해당 영화와 다른 영화들의 유사도 점수를 가져와서 높은 순으로 정렬
    sim_scores = item_sim_df[movie_id].sort_values(ascending=False)
    
    # 2. 자기 자신(1위)을 제외하고 2~6위까지 영화 ID 5개 뽑기
    top_5_ids = sim_scores.iloc[1:6].index.tolist()
    
    # 3. 프론트엔드로 보낼 영화 정보 예쁘게 포장하기
    recommendations = []
    for mid in top_5_ids:
        movie_info = movies_df[movies_df['movie_id'] == mid].iloc[0]
        recommendations.append({
            "movie_id": int(movie_info['movie_id']),
            "title": movie_info['title'],
            "genres": movie_info['genres']
        })
        
    return recommendations
# 🌟 별점 저장 API
@app.post("/rate")
def save_rating(rating_data: Rating):
    # DB에 데이터를 집어넣는 SQL 쿼리
    query = text("""
        INSERT INTO ratings (user_id, movie_id, rating) 
        VALUES (:user_id, :movie_id, :rating)
    """)
    
    # DB에 연결해서 쿼리 실행 후 저장(commit)
    with engine.begin() as conn:
        conn.execute(query, {
            "user_id": rating_data.user_id,
            "movie_id": rating_data.movie_id,
            "rating": rating_data.rating
        })
        
    return {"message": f"{rating_data.movie_id}번 영화에 {rating_data.rating}점이 저장되었습니다!"}