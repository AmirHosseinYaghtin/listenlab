"""Podcast CRUD endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services import podcast_service as svc

router = APIRouter(prefix="/api/podcasts", tags=["podcasts"])


class PodcastCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = ""
    audioFileId: str
    subtitleFileId: str
    vocabularyFileId: str | None = None
    coverFileId: str | None = None
    vocabularyMapping: dict[str, int | None] | None = None
    sourceKey: str | None = None


class PodcastUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    audioFileId: str | None = None
    subtitleFileId: str | None = None
    vocabularyFileId: str | None = None
    coverFileId: str | None = None
    vocabularyMapping: dict[str, int | None] | None = None


class VocabularyPreviewRequest(BaseModel):
    fileId: str
    mapping: dict[str, int | None] | None = None


def _handle(exc: Exception) -> None:
    if isinstance(exc, svc.PodcastNotFound):
        raise HTTPException(status_code=404, detail="Podcast not found.")
    if isinstance(exc, svc.PodcastValidationError):
        raise HTTPException(status_code=400, detail=str(exc))
    raise exc


@router.get("")
def list_podcasts():
    return svc.list_podcasts()


@router.get("/{podcast_id}")
def get_podcast(podcast_id: str):
    try:
        return svc.get_podcast(podcast_id)
    except svc.PodcastNotFound as exc:
        _handle(exc)


@router.post("", status_code=201)
def create_podcast(payload: PodcastCreate):
    try:
        return svc.create_podcast(payload.model_dump())
    except svc.PodcastValidationError as exc:
        _handle(exc)


@router.put("/{podcast_id}")
def update_podcast(podcast_id: str, payload: PodcastUpdate):
    try:
        return svc.update_podcast(podcast_id, payload.model_dump(exclude_unset=True))
    except (svc.PodcastNotFound, svc.PodcastValidationError) as exc:
        _handle(exc)


@router.delete("/{podcast_id}", status_code=204)
def delete_podcast(podcast_id: str):
    try:
        svc.delete_podcast(podcast_id)
    except svc.PodcastNotFound as exc:
        _handle(exc)


@router.get("/{podcast_id}/vocabulary")
def vocabulary(podcast_id: str):
    try:
        detail = svc.get_podcast(podcast_id)
    except svc.PodcastNotFound as exc:
        _handle(exc)
    return detail["vocabulary"]


@router.get("/{podcast_id}/matching-stats")
def matching_stats(podcast_id: str):
    try:
        return svc.matching_stats(podcast_id)
    except svc.PodcastNotFound as exc:
        _handle(exc)


@router.post("/vocabulary-preview")
def vocabulary_preview(payload: VocabularyPreviewRequest):
    try:
        return svc.vocabulary_preview(payload.model_dump())
    except svc.PodcastValidationError as exc:
        _handle(exc)
