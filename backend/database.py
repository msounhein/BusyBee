from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import Config

engine = create_engine(f'sqlite:///{Config.DB_PATH}', echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    import models  # noqa: F401 — ensure models are registered
    import models_chat  # noqa: F401
    Base.metadata.create_all(bind=engine)

    from sqlalchemy import text
    db = SessionLocal()
    try:
        res = db.execute(text("PRAGMA table_info(profile)"))
        columns = [row[1] for row in res.fetchall()]
        
        migrations = [
            ("scrape_linkedin", "ALTER TABLE profile ADD COLUMN scrape_linkedin BOOLEAN DEFAULT 1"),
            ("scrape_indeed", "ALTER TABLE profile ADD COLUMN scrape_indeed BOOLEAN DEFAULT 1"),
            ("scrape_himalayas", "ALTER TABLE profile ADD COLUMN scrape_himalayas BOOLEAN DEFAULT 1"),
            ("scrape_remotive", "ALTER TABLE profile ADD COLUMN scrape_remotive BOOLEAN DEFAULT 1"),
            ("scrape_wwr", "ALTER TABLE profile ADD COLUMN scrape_wwr BOOLEAN DEFAULT 1"),
            ("llm_provider", "ALTER TABLE profile ADD COLUMN llm_provider VARCHAR(50) DEFAULT 'zai'"),
            ("llm_api_key", "ALTER TABLE profile ADD COLUMN llm_api_key VARCHAR(255) DEFAULT ''"),
            ("llm_model", "ALTER TABLE profile ADD COLUMN llm_model VARCHAR(255) DEFAULT 'glm-5.1'"),
            ("llm_api_url", "ALTER TABLE profile ADD COLUMN llm_api_url VARCHAR(500) DEFAULT ''"),
        ]
        
        for col_name, sql in migrations:
            if col_name not in columns:
                print(f"[migration] Adding column {col_name} to profile table...", flush=True)
                db.execute(text(sql))
        
        # Migrate resume_profile table to add github_url
        res_rp = db.execute(text("PRAGMA table_info(resume_profile)"))
        columns_rp = [row[1] for row in res_rp.fetchall()]
        if "github_url" not in columns_rp:
            print("[migration] Adding column github_url to resume_profile table...", flush=True)
            db.execute(text("ALTER TABLE resume_profile ADD COLUMN github_url VARCHAR(500) DEFAULT ''"))

        db.commit()
    except Exception as e:
        print(f"[migration] Error running migrations: {e}", flush=True)
        db.rollback()
    finally:
        db.close()
