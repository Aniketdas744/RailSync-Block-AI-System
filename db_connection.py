import psycopg2


DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "railsync",
    "user": "postgres",
    "password": "YOUR_POSTGRES_PASSWORD",
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def test_connection():
    try:
        conn = get_connection()

        print(
            "PostgreSQL connection successful"
        )

        conn.close()

        return True

    except Exception as e:

        print(
            "PostgreSQL connection failed:",
            e
        )

        return False


if __name__ == "__main__":
    test_connection()