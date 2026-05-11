import pandas as pd
from sqlalchemy import create_engine

# 1. MariaDB 연결 설정 
# 형식: mysql+pymysql://사용자이름:비밀번호@호스트주소:포트번호/데이터베이스이름
# (예시: 본인의 DB 설정에 맞게 반드시 수정하세요!)
engine = create_engine("mysql+pymysql://root:vagrant@localhost:3306/movie_recommendation")

# 2. 다운로드한 CSV 파일 읽어오기
print("데이터를 읽어오는 중...")
movies_df = pd.read_csv('movies.csv')
ratings_df = pd.read_csv('ratings.csv')

# 3. 컬럼명을 우리가 만든 DB 테이블과 똑같이 맞추기
movies_df.rename(columns={'movieId': 'movie_id'}, inplace=True)
ratings_df.rename(columns={'userId': 'user_id', 'movieId': 'movie_id'}, inplace=True)

# 4. Users 테이블 채우기 (Foreign Key 에러 방지)
# ratings에 있는 고유한 유저 ID를 뽑아서 'user_1', 'user_2' 형태로 임시 유저를 만듭니다.
print("Users 데이터 삽입 중...")
unique_users = pd.DataFrame({'user_id': ratings_df['user_id'].unique()})
unique_users['username'] = 'user_' + unique_users['user_id'].astype(str)
unique_users.to_sql(name='users', con=engine, if_exists='append', index=False)

# 5. Movies 테이블 채우기
print("Movies 데이터 삽입 중...")
movies_df.to_sql(name='movies', con=engine, if_exists='append', index=False)

# 6. Ratings 테이블 채우기 (불필요한 timestamp 컬럼은 빼고 삽입)
print("Ratings 데이터 삽입 중... (10만 개라 몇 초 걸릴 수 있습니다)")
ratings_db_df = ratings_df[['user_id', 'movie_id', 'rating']]
ratings_db_df.to_sql(name='ratings', con=engine, if_exists='append', index=False)

print("🎉 모든 데이터 적재 완료! DBeaver나 DataGrip에서 확인해보세요!")