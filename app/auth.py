from pwdlib import PasswordHash
import jwt
from datetime import datetime,timedelta, timezone

SECRET_KEY =""

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.hash(password, hashed_password)


def create_access_token(user_id:int) ->str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    
    payload = {
        "sub": str(user_id),
        "exp": expire,
    }
    
    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm="HS256"
    )
    
    

def decode_access_token(token: str) -> int:
    decoded = jwt.decode(
        token,
        SECRET_KEY,
        algorithms=["HS256"]
    )

    return int(decoded["sub"])
    




