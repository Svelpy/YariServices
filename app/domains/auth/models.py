from datetime import datetime, timezone
from uuid import UUID, uuid4

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, IndexModel


class AuthSession(Document):
    user_id: PydanticObjectId
    family_id: UUID = Field(default_factory=uuid4)
    refresh_token_hash: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None
    revocation_reason: str | None = None
    replaced_by: PydanticObjectId | None = None
    user_agent: str | None = None
    ip_address: str | None = None

    class Settings:
        name = "auth_sessions"
        indexes = [
            IndexModel([("refresh_token_hash", ASCENDING)],unique=True),
            IndexModel([("user_id", ASCENDING), ("revoked_at", ASCENDING)]),
            IndexModel([("family_id", ASCENDING), ("revoked_at", ASCENDING)]),
            IndexModel([("expires_at", ASCENDING)],expireAfterSeconds=0),
        ]
    @classmethod
    async def revoke_for_user(cls,user_id: PydanticObjectId,reason: str) -> None:
        await cls.find(cls.user_id == user_id,cls.revoked_at == None).update(
            {
                "$set": {
                    "revoked_at": datetime.now(timezone.utc),
                    "revocation_reason": reason,
                }
            }
        )

class EmailVerificationToken(Document):
    user_id: PydanticObjectId
    token_hash: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    used_at: datetime | None = None
    revoked_at: datetime | None = None

    class Settings:
        name = "email_verification_tokens"
        indexes = [
            IndexModel([("token_hash", ASCENDING)], unique=True),
            IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0),
        ]
