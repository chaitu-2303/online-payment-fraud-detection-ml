from app.services.auth_db import create_user

print('create_user returned:', create_user('testuser', 'password123'))
