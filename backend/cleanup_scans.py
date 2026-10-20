import os
import shutil
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database connection
DB_URL = os.environ.get("DATABASE_URL", "postgresql://cams_user:cams_password@db:5432/cams_db")
if DB_URL.startswith("postgresql+asyncpg://"):
    DB_URL = DB_URL.replace("postgresql+asyncpg://", "postgresql://")

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def is_valid_uuid(val):
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False

def clean_orphaned_scans():
    from sqlalchemy import text
    session = SessionLocal()
    try:
        # 1. Get all valid folder UUIDs from DB
        result = session.execute(text("SELECT file_url FROM scan_jobs"))
        valid_folder_uuids = set()
        for row in result:
            file_url = row[0]
            try:
                # e.g. /scans/<folder_uuid>/source/source.pdf
                folder_uuid = file_url.split("/")[-3]
                if is_valid_uuid(folder_uuid):
                    valid_folder_uuids.add(folder_uuid)
            except Exception:
                pass
        
        print(f"Found {len(valid_folder_uuids)} valid scan folders in DB: {valid_folder_uuids}")

        # 2. Iterate through storage/scans
        scans_dir = "/app/storage/scans"
        if not os.path.exists(scans_dir):
            print(f"Directory {scans_dir} does not exist.")
            return

        for item in os.listdir(scans_dir):
            item_path = os.path.join(scans_dir, item)
            
            # Delete debug PNGs
            if os.path.isfile(item_path) and item.startswith("debug_") and item.endswith(".png"):
                print(f"Deleting debug file: {item}")
                os.remove(item_path)
                continue

            if os.path.isdir(item_path):
                # Delete test directories
                if item.startswith("test-"):
                    print(f"Deleting test directory: {item}")
                    shutil.rmtree(item_path)
                    continue

                # Delete orphaned UUID directories
                if is_valid_uuid(item):
                    if item not in valid_folder_uuids:
                        print(f"Deleting orphaned directory: {item}")
                        shutil.rmtree(item_path)
                    else:
                        print(f"Keeping active directory: {item}")

    finally:
        session.close()

if __name__ == "__main__":
    clean_orphaned_scans()
