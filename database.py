from db_connection import get_connection


def database_enabled():
    return True


def get_database_url():
    return "PostgreSQL localhost:5432/railsync"


def database_status():
    try:
        conn = get_connection()
        conn.close()

        return {
            "enabled": True,
            "status": "CONNECTED"
        }

    except Exception as e:
        return {
            "enabled": False,
            "status": "ERROR",
            "message": str(e)
        }