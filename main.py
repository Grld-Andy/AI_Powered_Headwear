from core.app.lifecycle import initialize_app, run_main_loop
from database import setup_db

if __name__ == "__main__":
    setup_db()
    initialize_app()
    run_main_loop()
