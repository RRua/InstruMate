import os
import sqlite3


def execute_query(db_path, query, format='array'):
    if not os.path.exists(db_path):
        raise RuntimeError(f"Path does not exists: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    columns = [description[0] for description in cursor.description]
    conn.close()
    if format == 'dictionary':
        # Return an array of dictionaries
        return [dict(zip(columns, row)) for row in rows]
    elif format == 'array':
        # Return an array of arrays
        return [list(row) for row in rows]
    else:
        raise ValueError("Invalid format. Use 'array' or 'dictionary'.")