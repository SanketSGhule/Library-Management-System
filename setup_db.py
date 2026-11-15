import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Use PyMySQL on cloud platforms
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass

import MySQLdb

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

db_name = os.getenv("DB_NAME", "railway")
db_user = os.getenv("DB_USER", "root")
db_password = os.getenv("DB_PASSWORD", "")
db_host = os.getenv("DB_HOST", "127.0.0.1")
db_port = int(os.getenv("DB_PORT", 3306))

print(f"Connecting to MySQL at {db_host}:{db_port}...")

try:
    conn = MySQLdb.connect(
        host=db_host,
        user=db_user,
        passwd=db_password,
        port=db_port,
        charset='utf8mb4'
    )
    print("Connected successfully!")
except MySQLdb.OperationalError as e:
    print(f"[ERROR] Could not connect to MySQL: {e}")
    sys.exit(1)

cursor = conn.cursor()

def run_sql_file(file_path):
    print(f"Executing {file_path.name}...")
    with open(file_path, "r", encoding="utf-8") as f:
        sql = f.read()

    # Adapt database name to match Railway environment
    sql = sql.replace("library_management", db_name)

    statements = sql.split(";")
    for stmt in statements:
        stmt = stmt.strip()
        lines = [line for line in stmt.splitlines() if not line.strip().startswith("--")]
        clean_stmt = "\n".join(lines).strip()
        if clean_stmt:
            try:
                cursor.execute(clean_stmt)
            except MySQLdb.Error as e:
                # 1062 = duplicate entry, 1007 = database already exists
                if e.args[0] in (1062, 1007):
                    pass
                else:
                    print(f"Notice: {e}")

try:
    schema_path = BASE_DIR / "database" / "schema.sql"
    data_path = BASE_DIR / "database" / "sample_data.sql"
    if schema_path.exists():
        run_sql_file(schema_path)
        conn.commit()
    conn.select_db(db_name)
    if data_path.exists():
        run_sql_file(data_path)
        conn.commit()
    print("Schema & sample data successfully imported!")
except Exception as e:
    print(f"[ERROR] Failed importing SQL: {e}")
finally:
    cursor.close()
    conn.close()

# Run Django migrations
print("\nRunning Django migrations...")
os.environ["DJANGO_SETTINGS_MODULE"] = "LibraryManagementSystem.settings"
os.system(f'"{sys.executable}" manage.py migrate')

# Create Superuser Admin3 and link to Librarian Profile
print("\nEnsuring Django superuser 'Admin3' exists...")
create_admin_code = """
import django
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='Admin3').exists():
    u = User.objects.create_superuser('Admin3', 'admin3@college.edu', 'Admin#2024')
    print("Superuser 'Admin3' successfully created!")
else:
    u = User.objects.get(username='Admin3')
    u.set_password('Admin#2024')
    u.is_superuser = True
    u.is_staff = True
    u.save()
    print("Superuser 'Admin3' password updated!")

try:
    from library_app.models import Members, UserProfile
    member = Members.objects.filter(member_type='LIBRARIAN').first()
    if not member:
        member = Members.objects.first()
    if member and not UserProfile.objects.filter(user=u).exists():
        UserProfile.objects.create(user=u, member=member)
        print(f"Linked Admin3 to Librarian member: {member.full_name}")
except Exception as e:
    print(f"Profile link notice: {e}")
"""
os.system(f'"{sys.executable}" -c "{create_admin_code}"')
print("\nSetup finished!")
