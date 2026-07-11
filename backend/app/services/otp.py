from schema.enums import OTPPurpose
from core.redis import redis_client
class OTPService:

    PREFIX = "otp"

    @classmethod
    def key(cls,purpose:OTPPurpose,email:str):
        return f"{cls.PREFIX}:{purpose.value}:{email}"
    
    @classmethod
    async def save(cls,purpose,email,otp):
        print(f"-----------USED REDIS TO SAVE--------")
        await redis_client.set(
            cls.key(purpose,email),
            otp,
            ex=600
        )
    
    @classmethod
    async def get(cls,purpose,email):
        print("-----------USED REDIS TO GET--------")
        return await redis_client.get(
            cls.key(purpose,email)
        )
    
    @classmethod
    async def delete(cls,purpose,email):
        print("-----------USED REDIS TO DELETE--------")
        await redis_client.delete(
            cls.key(purpose,email)
        )