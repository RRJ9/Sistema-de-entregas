import psycopg2

# Pegas aquí tu cadena de Railway
conn_str = "postgresql://postgres:TuygIYekmCYaCmnlqVIxyKARymZXXGvH@turntable.proxy.rlwy.net:18922/railway"

try:
    conn = psycopg2.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
    tablas = cursor.fetchall()
    print("✅ Tablas encontradas:", tablas)
    conn.close()
except Exception as e:
    print("❌ Error al conectar:", e)