from app.admin.app import create_app
from app.config import settings

app = create_app()

if __name__ == "__main__":
    app.run(host=settings.admin_host, port=settings.admin_port, debug=True)
