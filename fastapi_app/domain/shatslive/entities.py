from dataclasses import dataclass


@dataclass(frozen=True)
class LiveStream:
    id: int
    title: str
    description: str
    scheduled_at: str
    status: str
    stream_url: str
    created_at: str
    host_ism: str
    host_familiya: str
