from enum import Enum
from typing import Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field

# 1. الاستيراد المباشر من الحزمة المعيارية الموحدة
from nexus_arbiter.schemas import (
    ActionType,
    NegotiationPayload,
    EncryptedPayloadEnvelope,
    SignedNegotiationMessage
)

class SessionStatus(str, Enum):
    INITIATED = "INITIATED"
    NEGOTIATING = "NEGOTIATING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"

# 2. استثناءات مفصلة تخدم طبقة الـ API
class FSMException(Exception):
    """الاستثناء الأساسي لآلة الحالة."""
    pass

class UnauthorizedParticipantError(FSMException):
    """محاولة تدخل من طرف ثالث غير مصرح له."""
    pass

class KeyMismatchError(FSMException):
    """محاولة تغيير المفتاح العام المسجل للوكيل."""
    pass

class TurnViolationError(FSMException):
    """خرق لترتيب الأدوار بين الوكلاء."""
    pass

class NegotiationSession(BaseModel):
    session_id: UUID
    status: SessionStatus = SessionStatus.INITIATED
    expected_sequence_id: int = 1
    last_sender_id: Optional[str] = None
    buyer_id: Optional[str] = None
    seller_id: Optional[str] = None
    buyer_pubkey_hex: Optional[str] = None
    seller_pubkey_hex: Optional[str] = None
    agreed_payload: Optional[Union[NegotiationPayload, EncryptedPayloadEnvelope]] = None
    history: list[SignedNegotiationMessage] = Field(default_factory=list)

    def apply_transition(self, message: SignedNegotiationMessage) -> "NegotiationSession":
        if message.session_id != self.session_id:
            raise FSMException(f"Session ID mismatch: expected {self.session_id}, got {message.session_id}")

        if self.status in (SessionStatus.ACCEPTED, SessionStatus.REJECTED):
            raise FSMException(f"Terminal state reached ({self.status.value}). No further transitions allowed.")

        if message.sequence_id != self.expected_sequence_id:
            raise FSMException(
                f"Sequence mismatch: expected sequence_id={self.expected_sequence_id}, got {message.sequence_id}"
            )

        if self.last_sender_id and message.sender_agent_id == self.last_sender_id:
            raise TurnViolationError(f"Role turn violation: agent {message.sender_agent_id} cannot submit consecutive steps")

        # المرحلة الأولى: بدء الجلسة
        if self.status == SessionStatus.INITIATED:
            if message.action != ActionType.PROPOSE:
                raise FSMException("New session must be initialized with a PROPOSE action")
            self.status = SessionStatus.NEGOTIATING
            self.buyer_id = message.sender_agent_id
            self.buyer_pubkey_hex = message.public_key_hex

        # المرحلة الثانية: التفاوض القائم
        elif self.status == SessionStatus.NEGOTIATING:
            # تسجيل البائع في الخطوة الأولى التي يتفاعل فيها
            if self.seller_id is None:
                if message.sender_agent_id == self.buyer_id:
                    raise TurnViolationError("Buyer cannot negotiate with themselves")
                self.seller_id = message.sender_agent_id
                self.seller_pubkey_hex = message.public_key_hex
            else:
                # [حماية أمنية 1]: منع الأطراف الخارجية بعد تسجيل المشتري والبائع
                if message.sender_agent_id not in (self.buyer_id, self.seller_id):
                    raise UnauthorizedParticipantError(
                        f"Unauthorized agent {message.sender_agent_id}. Session is locked between {self.buyer_id} and {self.seller_id}."
                    )

            # [حماية أمنية 2]: التحقق من ثبات المفتاح العام وعدم انتحاله
            expected_key = self.buyer_pubkey_hex if message.sender_agent_id == self.buyer_id else self.seller_pubkey_hex
            if message.public_key_hex != expected_key:
                raise KeyMismatchError(f"Public key mismatch for agent {message.sender_agent_id}")

            # معالجة القرارات
            if message.action == ActionType.ACCEPT:
                self.status = SessionStatus.ACCEPTED
                self.agreed_payload = self.history[-1].payload
            elif message.action == ActionType.REJECT:
                self.status = SessionStatus.REJECTED
            elif message.action == ActionType.COUNTER:
                self.status = SessionStatus.NEGOTIATING
            else:
                raise FSMException(f"Invalid transition action '{message.action.value}' during negotiation state")

        self.last_sender_id = message.sender_agent_id
        self.expected_sequence_id += 1
        self.history.append(message)
        return self