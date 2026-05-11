from sqlalchemy import create_engine, text

# 🌟 여기에 load_data.py에서 썼던 '진짜 Aiven 주소'를 그대로 붙여넣으세요!
DB_URL = "mysql+pymysql://avnadmin:1234@mysql-6e9cb4c-skslsh03.i.aivencloud.com:15887/defaultdb"
engine = create_engine(DB_URL, connect_args={'ssl': {}})

# DB에 접속해서 테이블(방)을 예쁘게 세팅하는 작업입니다.
with engine.begin() as conn:
    print("기존 찌꺼기 데이터 정리 중...")
    conn.execute(text("DROP TABLE IF EXISTS ratings;"))
    conn.execute(text("DROP TABLE IF EXISTS movies;"))
    conn.execute(text("DROP TABLE IF EXISTS users;"))

    print("새로운 테이블(users, movies, ratings) 생성 중...")
    
    conn.execute(text("""
    CREATE TABLE users (
        user_id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """))

    conn.execute(text("""
    CREATE TABLE movies (
        movie_id INT PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        genres VARCHAR(255)
    );
    """))

    conn.execute(text("""
    CREATE TABLE ratings (
        rating_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT,
        movie_id INT,
        rating FLOAT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (movie_id) REFERENCES movies(movie_id)
    );
    """))

print("🎉 클라우드 DB에 테이블 세팅이 완벽하게 끝났습니다!")