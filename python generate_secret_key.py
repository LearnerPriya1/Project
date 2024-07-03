import secrets

def generate_secret_key():
    return secrets.token_hex(32)

secret_key = generate_secret_key()
print(secret_key)