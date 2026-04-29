"""
Sincroniza observações do iNaturalist para espécies com inaturalist_taxon_id cadastrado.

Estratégia:
- Incremental por padrão: usa last_inaturalist_sync_at + updated_since da API iNat
- Full sync quando: primeiro sync da espécie, FORCE_FULL_SYNC=true, ou LUMM_ID especificado
- UPSERT via INSERT ... ON CONFLICT para evitar delete massivo
- ThreadPool com MAX_WORKERS threads para paralelismo controlado
- MAX_RUNTIME_SECONDS como failsafe para o limite do GitHub Actions
- Retry automático em 429 e timeouts
"""

import os
import sys
import time
import threading
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.sql import func

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.extensions import db
from app.models.observation import Observation
from app.models.species import Species

INAT_API_URL = os.getenv("INATURALIST_API_URL", "https://api.inaturalist.org/v1")
INAT_API_KEY = os.getenv("INATURALIST_API_KEY")
PER_PAGE = 200
MAX_WORKERS = int(os.getenv("INATURALIST_MAX_WORKERS", "4"))
MAX_RUNTIME_SECONDS = int(os.getenv("INATURALIST_MAX_RUNTIME_SECONDS", "3000"))
SLEEP_BETWEEN_PAGES = float(os.getenv("INATURALIST_SLEEP_BETWEEN_PAGES", "0.3"))
REQUEST_TIMEOUT = int(os.getenv("INATURALIST_REQUEST_TIMEOUT_SECONDS", "30"))
FORCE_FULL_SYNC = os.getenv("FORCE_FULL_SYNC", "").lower() in ("1", "true", "yes")

app = create_app()
_log_lock = threading.Lock()
_start_time: float = 0.0


def _log(message: str, level: str = "INFO") -> None:
    with _log_lock:
        print(f"[{level}] {message}", flush=True)


def _int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _deadline_exceeded() -> bool:
    return time.time() - _start_time > MAX_RUNTIME_SECONDS


def _build_headers() -> dict:
    headers = {"Accept": "application/json"}
    if INAT_API_KEY:
        headers["Authorization"] = f"Bearer {INAT_API_KEY}"
    return headers


def _parse_location(location: str | None) -> tuple[float | None, float | None]:
    if not location:
        return None, None
    try:
        lat_str, lng_str = location.split(",", 1)
        return float(lat_str.strip()), float(lng_str.strip())
    except (ValueError, AttributeError):
        return None, None


def _fetch_page(taxon_id: int, id_above: int | None, updated_since: str | None) -> dict:
    params = {
        "taxon_id": taxon_id,
        "has[]": "geo",
        "per_page": PER_PAGE,
        "order": "asc",
        "order_by": "id",
    }
    if id_above is not None:
        params["id_above"] = id_above
    if updated_since:
        params["updated_since"] = updated_since

    for attempt in range(3):
        try:
            response = requests.get(
                f"{INAT_API_URL}/observations",
                headers=_build_headers(),
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            if response.status_code == 429:
                wait = 2 ** attempt * 5
                _log(f"  Rate limit (429) — aguardando {wait}s antes de retry", "AVISO")
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            if attempt < 2:
                _log(f"  Timeout na tentativa {attempt + 1}, retentando...", "AVISO")
                time.sleep(2)
            else:
                raise
    raise RuntimeError("Máximo de tentativas atingido")


def _collect(taxon_id: int, updated_since: str | None) -> list[dict]:
    collected = []
    id_above = None
    page_num = 0

    while not _deadline_exceeded():
        page_num += 1
        data = _fetch_page(taxon_id, id_above, updated_since)
        results = data.get("results", [])
        if not results:
            break

        for obs in results:
            obs_id = str(obs.get("id"))
            lat, lng = _parse_location(obs.get("location"))
            if lat is None or lng is None:
                continue

            photos = obs.get("photos") or []
            raw_photo_url = photos[0].get("url") if photos else None
            photo_url = raw_photo_url.replace("/square.", "/medium.") if raw_photo_url else None

            collected.append({
                "source": "inaturalist",
                "external_id": obs_id,
                "latitude": lat,
                "longitude": lng,
                "location_obscured": bool(obs.get("obscured", False)),
                "observed_on": obs.get("observed_on") or None,
                "quality_grade": obs.get("quality_grade") or None,
                "photo_url": photo_url,
                "url": obs.get("uri") or None,
            })

        if len(results) < PER_PAGE:
            break

        id_above = results[-1].get("id")
        time.sleep(SLEEP_BETWEEN_PAGES)

    return collected


def _upsert(session, species_id: int, rows: list[dict]) -> int:
    if not rows:
        return 0
    stmt = pg_insert(Observation).values([{"species_id": species_id, **r} for r in rows])
    stmt = stmt.on_conflict_do_update(
        constraint="uq_observation_source_external_id",
        set_={
            "species_id": stmt.excluded.species_id,
            "latitude": stmt.excluded.latitude,
            "longitude": stmt.excluded.longitude,
            "location_obscured": stmt.excluded.location_obscured,
            "observed_on": stmt.excluded.observed_on,
            "quality_grade": stmt.excluded.quality_grade,
            "photo_url": stmt.excluded.photo_url,
            "url": stmt.excluded.url,
            "updated_at": func.now(),
        },
    )
    session.execute(stmt)
    return len(rows)


def _sync_species(species_id: int, force_full: bool) -> tuple[str, int, str]:
    """Executa num thread separado. Retorna (scientific_name, upserted, modo)."""
    with app.app_context():
        species = db.session.get(Species, species_id)
        if not species:
            return ("?", 0, "erro")

        is_full = force_full or species.last_inaturalist_sync_at is None
        updated_since = None
        if not is_full and species.last_inaturalist_sync_at:
            updated_since = species.last_inaturalist_sync_at.strftime("%Y-%m-%dT%H:%M:%S+00:00")

        mode = "full" if is_full else "incremental"
        _log(f"  [{species.scientific_name}] modo={mode} updated_since={updated_since}")

        rows = _collect(species.inaturalist_taxon_id, updated_since)

        if is_full:
            db.session.query(Observation).filter_by(
                species_id=species_id, source="inaturalist"
            ).delete()

        upserted = _upsert(db.session, species_id, rows)

        species.last_inaturalist_sync_at = datetime.now(timezone.utc)
        db.session.commit()
        db.session.remove()

        return (species.scientific_name, upserted, mode)


def main():
    global _start_time
    _start_time = time.time()

    raw_lumm_ids = os.environ.get("LUMM_ID", "")
    lumm_ids = [v for raw in raw_lumm_ids.split(",") if (v := _int(raw.strip()))]
    force_full = FORCE_FULL_SYNC or bool(lumm_ids)

    _log("=== Sync iNaturalist: inicio ===")
    if INAT_API_KEY:
        _log("Usando API key", "OK")
    else:
        _log("Sem API key — rate limit reduzido", "AVISO")
    if force_full:
        _log("Modo: FULL SYNC", "AVISO")
    if FORCE_FULL_SYNC:
        _log("FORCE_FULL_SYNC ativado via env", "AVISO")

    with app.app_context():
        query = db.session.query(Species.id).filter(
            Species.inaturalist_taxon_id.isnot(None)
        )
        if lumm_ids:
            _log(f"Modo individual: LUMM_IDs={lumm_ids}")
            query = query.filter(Species.id.in_(lumm_ids))
        species_ids = [row.id for row in query.all()]

    total = len(species_ids)
    _log(f"Espécies a sincronizar: {total}", "OK")

    total_upserted = 0
    errors = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(_sync_species, sid, force_full): sid
            for sid in species_ids
        }
        completed = 0
        for future in as_completed(futures):
            completed += 1
            try:
                name, upserted, mode = future.result()
                total_upserted += upserted
                _log(f"[{completed}/{total}] {name} — {upserted} obs ({mode})", "OK")
            except Exception as e:
                errors += 1
                _log(f"[{completed}/{total}] Erro: {e}", "ERRO")

            if _deadline_exceeded():
                _log(f"Limite de tempo atingido ({MAX_RUNTIME_SECONDS}s) — encerrando", "AVISO")
                pool.shutdown(wait=False, cancel_futures=True)
                break

    elapsed = int(time.time() - _start_time)
    _log(
        f"Upserted: {total_upserted} | Erros: {errors} | Tempo: {elapsed}s",
        "RESUMO",
    )
    _log("Sincronização finalizada", "OK")


if __name__ == "__main__":
    main()
