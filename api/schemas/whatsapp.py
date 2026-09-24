from pydantic import BaseModel, ConfigDict, Field


class Profile(BaseModel):
    name: str | None = None


class Contact(BaseModel):
    profile: Profile | None = None
    wa_id: str


class TextBody(BaseModel):
    body: str


class MediaAttachment(BaseModel):
    id: str
    mime_type: str | None = None


class IncomingMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    from_number: str = Field(alias="from")
    timestamp: str
    type: str
    text: TextBody | None = None
    audio: MediaAttachment | None = None
    voice: MediaAttachment | None = None


class Metadata(BaseModel):
    display_phone_number: str | None = None
    phone_number_id: str | None = None


class ChangeValue(BaseModel):
    messaging_product: str
    metadata: Metadata | None = None
    contacts: list[Contact] = Field(default_factory=list)
    messages: list[IncomingMessage] = Field(default_factory=list)
    statuses: list[dict] = Field(default_factory=list)


class Change(BaseModel):
    value: ChangeValue
    field: str


class Entry(BaseModel):
    id: str
    changes: list[Change] = Field(default_factory=list)


class WhatsAppWebhookPayload(BaseModel):
    """Raw shape of a Meta WhatsApp Cloud API webhook event."""

    object: str
    entry: list[Entry] = Field(default_factory=list)


class ParsedMessage(BaseModel):
    """Flattened, router/service-friendly view of one incoming message."""

    sender: str
    message_type: str
    text: str | None = None
    media_id: str | None = None
    mime_type: str | None = None
    message_id: str
