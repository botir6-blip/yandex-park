from app.admin.app import create_app
from app.config import settings
from app.db import Base, engine
import app.models  # моделлар Base га рўйхатдан ўтиши учун

Base.metadata.create_all(bind=engine)

app = create_app()

if __name__ == "__main__":
    app.run(host=settings.admin_host, port=settings.admin_port, debug=True)
