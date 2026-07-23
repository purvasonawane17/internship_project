from db import get_connection  # To check the DB conection 

def main():
    conn = get_connection()
    if conn is None:
        print("Could not connect to the database.")
        return
    
    cursor = conn.cursor()
    try:
        # Get column names
        cursor.execute("DESCRIBE users")
        columns = cursor.fetchall()
        print("--- Columns in 'users' table ---")
        for col in columns:
            print(f"Field: {col[0]}, Type: {col[1]}")
        
        # Get all rows
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        print("\n--- Rows in 'users' table ---")
        for row in rows:
            print(row)
            
    except Exception as e:
        print("Error reading database:", e)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
