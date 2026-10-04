from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from music.models import Track


@dataclass
class WaveSession:
    seed: Track
    limit: int
    completed: int = 0
    failures: int = 0
    pending: deque[Track] = field(default_factory=deque)
    seen: set[str] = field(default_factory=set)
    anchors: deque[Track] = field(default_factory=deque)
    queried: set[str] = field(default_factory=set)

    def add(self, tracks: list[Track]) -> None:
        for track in tracks:
            if track.url not in self.seen:
                self.seen.add(track.url)
                self.pending.append(track)
                self.anchors.appendleft(track)

    async def next_track(self, youtube) -> Track | None:
        if self.completed >= self.limit:
            return None
        # A finite budget prevents repeated Mix responses from looping forever.
        for _ in range(3):
            if self.pending:
                return self.pending.popleft()
            anchor = next((t for t in self.anchors if t.url not in self.queried), None)
            if anchor is None:
                return None
            self.queried.add(anchor.url)
            self.add(await youtube.get_mix(anchor))
        return self.pending.popleft() if self.pending else None
