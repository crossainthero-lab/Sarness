"""Projects, folders, generations, collections, tags, files and uploads."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from ..api.deps import AppState, require_auth
from ..db import new_id, now

router = APIRouter(prefix="/v1")


# ------------------------------------------------------------------ projects
@router.get("/projects")
def list_projects(st: AppState = Depends(require_auth)):
    projects = st.db.all("SELECT * FROM projects WHERE archived = 0 ORDER BY sort, created_at")
    folders = st.db.all("SELECT * FROM folders ORDER BY sort, name")
    counts = {r["project_id"]: r["c"] for r in st.db.all(
        "SELECT project_id, COUNT(*) c FROM generations WHERE deleted_at IS NULL GROUP BY project_id")}
    for p in projects:
        p["folders"] = [f for f in folders if f["project_id"] == p["id"]]
        p["generation_count"] = counts.get(p["id"], 0)
    return projects


@router.post("/projects")
def create_project(body: dict[str, Any] = Body(...), st: AppState = Depends(require_auth)):
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "name is required")
    row = {"id": new_id("p_"), "name": name[:120], "color": body.get("color"), "icon": body.get("icon"),
           "sort": int(st.db.scalar("SELECT COALESCE(MAX(sort), 0) + 1 FROM projects")), "archived": 0,
           "created_at": now(), "updated_at": now()}
    st.db.insert("projects", row)
    st.bus.publish("projects.changed", {})
    return {**row, "folders": [], "generation_count": 0}


@router.patch("/projects/{pid}")
def update_project(pid: str, body: dict[str, Any] = Body(...), st: AppState = Depends(require_auth)):
    vals = {k: v for k, v in body.items() if k in ("name", "color", "icon", "sort", "archived")}
    vals["updated_at"] = now()
    st.db.update("projects", pid, vals)
    st.bus.publish("projects.changed", {})
    return st.db.one("SELECT * FROM projects WHERE id = ?", [pid])


@router.delete("/projects/{pid}")
def delete_project(pid: str, st: AppState = Depends(require_auth)):
    # Generations and conversations are kept; they simply become unfiled.
    with st.db.transaction() as db:
        db.execute("UPDATE generations SET project_id = NULL, folder_id = NULL WHERE project_id = ?", [pid])
        db.execute("UPDATE conversations SET project_id = NULL, folder_id = NULL WHERE project_id = ?", [pid])
        db.execute("DELETE FROM projects WHERE id = ?", [pid])
    st.bus.publish("projects.changed", {})
    return {"ok": True}


@router.post("/folders")
def create_folder(body: dict[str, Any] = Body(...), st: AppState = Depends(require_auth)):
    if not st.db.one("SELECT id FROM projects WHERE id = ?", [body.get("project_id")]):
        raise HTTPException(404, "project not found")
    parent = body.get("parent_id")
    if parent and not st.db.one("SELECT id FROM folders WHERE id = ? AND project_id = ?", [parent, body["project_id"]]):
        raise HTTPException(400, "parent folder is not in this project")
    row = {"id": new_id("fo_"), "project_id": body["project_id"], "parent_id": parent,
           "name": (body.get("name") or "New folder")[:120], "sort": 0, "created_at": now()}
    st.db.insert("folders", row)
    st.bus.publish("projects.changed", {})
    return row


@router.patch("/folders/{fid}")
def update_folder(fid: str, body: dict[str, Any] = Body(...), st: AppState = Depends(require_auth)):
    vals = {k: v for k, v in body.items() if k in ("name", "parent_id", "sort")}
    if vals.get("parent_id"):
        # Refuse cycles.
        cur = vals["parent_id"]
        while cur:
            if cur == fid:
                raise HTTPException(400, "a folder cannot be moved inside itself")
            row = st.db.one("SELECT parent_id FROM folders WHERE id = ?", [cur])
            cur = row["parent_id"] if row else None
    st.db.update("folders", fid, vals)
    st.bus.publish("projects.changed", {})
    return st.db.one("SELECT * FROM folders WHERE id = ?", [fid])


@router.delete("/folders/{fid}")
def delete_folder(fid: str, st: AppState = Depends(require_auth)):
    ids = [fid]
    i = 0
    while i < len(ids):
        ids += [r["id"] for r in st.db.all("SELECT id FROM folders WHERE parent_id = ?", [ids[i]])]
        i += 1
    marks = ",".join("?" * len(ids))
    with st.db.transaction() as db:
        db.execute(f"UPDATE generations SET folder_id = NULL WHERE folder_id IN ({marks})", ids)
        db.execute(f"UPDATE conversations SET folder_id = NULL WHERE folder_id IN ({marks})", ids)
        db.execute("DELETE FROM folders WHERE id = ?", [fid])
    st.bus.publish("projects.changed", {})
    return {"ok": True}


# --------------------------------------------------------------- generations
@router.get("/generations")
def list_generations(
    st: AppState = Depends(require_auth),
    type: str | None = None, project_id: str | None = None, folder_id: str | None = None,
    q: str | None = None, model_id: str | None = None, favorite: bool | None = None, tag: str | None = None,
    collection_id: str | None = None, since: float | None = None, until: float | None = None,
    before: float | None = Query(None, description="cursor: created_at of the last item"),
    limit: int = Query(60, le=500), trash: bool = False, job_id: str | None = None,
):
    conds = ["g.deleted_at IS NOT NULL" if trash else "g.deleted_at IS NULL"]
    args: list[Any] = []
    if project_id == "none":
        conds.append("g.project_id IS NULL")
        project_id = None
    for col, val in (("g.type", type), ("g.project_id", project_id), ("g.folder_id", folder_id),
                     ("g.model_id", model_id), ("g.job_id", job_id)):
        if val:
            conds.append(f"{col} = ?")
            args.append(val)
    if favorite is not None:
        conds.append("g.favorite = ?")
        args.append(int(favorite))
    if q:
        conds.append("(g.prompt LIKE ? OR g.negative_prompt LIKE ? OR EXISTS (SELECT 1 FROM tags t WHERE t.generation_id = g.id AND t.tag LIKE ?))")
        args += [f"%{q}%"] * 3
    if tag:
        conds.append("EXISTS (SELECT 1 FROM tags t WHERE t.generation_id = g.id AND t.tag = ?)")
        args.append(tag)
    if collection_id:
        conds.append("EXISTS (SELECT 1 FROM collection_items ci WHERE ci.generation_id = g.id AND ci.collection_id = ?)")
        args.append(collection_id)
    if since:
        conds.append("g.created_at >= ?")
        args.append(since)
    if until:
        conds.append("g.created_at <= ?")
        args.append(until)
    if before:
        conds.append("g.created_at < ?")
        args.append(before)
    sql = (f"SELECT g.* FROM generations g WHERE {' AND '.join(conds)} ORDER BY g.created_at DESC LIMIT ?")
    rows = st.db.all(sql, [*args, limit + 1])
    has_more = len(rows) > limit
    rows = rows[:limit]
    tags = _tags_for(st, [r["id"] for r in rows])
    items = []
    for r in rows:
        pub = st.jobs.generation_public(r)
        pub["tags"] = tags.get(r["id"], [])
        items.append(pub)
    return {"items": items, "next_cursor": rows[-1]["created_at"] if has_more and rows else None}


def _tags_for(st: AppState, ids: list[str]) -> dict[str, list[str]]:
    if not ids:
        return {}
    marks = ",".join("?" * len(ids))
    out: dict[str, list[str]] = {}
    for t in st.db.all(f"SELECT generation_id, tag FROM tags WHERE generation_id IN ({marks}) ORDER BY tag", ids):
        out.setdefault(t["generation_id"], []).append(t["tag"])
    return out


def _gen(st: AppState, gid: str) -> dict[str, Any]:
    g = st.db.one("SELECT * FROM generations WHERE id = ?", [gid])
    if not g:
        raise HTTPException(404, "generation not found")
    return g


@router.get("/generations/{gid}")
def get_generation(gid: str, st: AppState = Depends(require_auth)):
    g = _gen(st, gid)
    pub = st.jobs.generation_public(g)
    pub["workflow"] = g["workflow"]
    pub["tags"] = _tags_for(st, [gid]).get(gid, [])
    pub["collections"] = [r["collection_id"] for r in st.db.all(
        "SELECT collection_id FROM collection_items WHERE generation_id = ?", [gid])]
    f = st.storage.get(g["file_id"])
    pub["file"] = {k: f[k] for k in ("mime", "size", "sha256", "width", "height", "duration")} if f else None
    pub["path_on_server"] = str(st.storage.resolve(f["path"])) if f else None
    return pub


@router.patch("/generations/{gid}")
def update_generation(gid: str, body: dict[str, Any] = Body(...), st: AppState = Depends(require_auth)):
    _gen(st, gid)
    vals = {k: v for k, v in body.items() if k in ("favorite", "project_id", "folder_id")}
    if "favorite" in vals:
        vals["favorite"] = int(bool(vals["favorite"]))
    with st.db.transaction() as db:
        if vals:
            db.update("generations", gid, vals)
        if "tags" in body:
            db.execute("DELETE FROM tags WHERE generation_id = ?", [gid])
            for t in {str(t).strip().lower()[:48] for t in body["tags"] if str(t).strip()}:
                db.execute("INSERT INTO tags(generation_id, tag) VALUES (?, ?)", [gid, t])
    out = get_generation(gid, st)
    st.bus.publish("generation.updated", {k: v for k, v in out.items() if k != "workflow"})
    return out


@router.post("/generations/bulk")
def bulk_generations(body: dict[str, Any] = Body(...), st: AppState = Depends(require_auth)):
    ids = body.get("ids") or []
    action = body.get("action")
    if not ids:
        return {"ok": True, "count": 0}
    marks = ",".join("?" * len(ids))
    if action == "move":
        st.db.execute(f"UPDATE generations SET project_id = ?, folder_id = ? WHERE id IN ({marks})",
                      [body.get("project_id"), body.get("folder_id"), *ids])
    elif action == "favorite":
        st.db.execute(f"UPDATE generations SET favorite = ? WHERE id IN ({marks})", [int(bool(body.get("value", True))), *ids])
    elif action == "trash":
        st.db.execute(f"UPDATE generations SET deleted_at = ? WHERE id IN ({marks})", [now(), *ids])
    elif action == "restore":
        st.db.execute(f"UPDATE generations SET deleted_at = NULL WHERE id IN ({marks})", ids)
    elif action == "tag":
        for gid in ids:
            st.db.execute("INSERT OR IGNORE INTO tags(generation_id, tag) VALUES (?, ?)", [gid, str(body["tag"]).lower()[:48]])
    else:
        raise HTTPException(400, "unknown action")
    st.bus.publish("generations.changed", {"ids": ids, "action": action})
    return {"ok": True, "count": len(ids)}


@router.delete("/generations/{gid}")
def delete_generation(gid: str, permanent: bool = False, st: AppState = Depends(require_auth)):
    g = _gen(st, gid)
    if not permanent:
        st.db.update("generations", gid, {"deleted_at": now()})
    else:
        for fid in (g["file_id"], g.get("thumb_file_id")):
            f = st.storage.get(fid) if fid else None
            if f:
                try:
                    st.storage.resolve(f["path"]).unlink(missing_ok=True)
                except Exception:
                    pass
                st.db.execute("DELETE FROM files WHERE id = ?", [fid])
        st.db.execute("DELETE FROM generations WHERE id = ?", [gid])
    st.bus.publish("generations.changed", {"ids": [gid], "action": "delete" if permanent else "trash"})
    return {"ok": True}


@router.post("/generations/{gid}/rerun")
def rerun_generation(gid: str, body: dict[str, Any] = Body(default={}), st: AppState = Depends(require_auth)):
    import copy

    g = _gen(st, gid)
    graph = copy.deepcopy(g["workflow"])
    if body.get("new_seed"):
        for n in graph.get("nodes", []):
            if n["type"] in ("sampler.image", "sampler.video", "value.seed"):
                n.setdefault("params", {})["seed"] = -1
    return st.jobs.submit(kind=g["type"], workflow=graph, project_id=body.get("project_id", g["project_id"]),
                          folder_id=body.get("folder_id", g["folder_id"]))


@router.get("/generations/{gid}/metadata")
def generation_metadata(gid: str, st: AppState = Depends(require_auth)):
    g = get_generation(gid, st)
    return JSONResponse({"format": "sarness.generation", "version": 1, **g},
                        headers={"Content-Disposition": f'attachment; filename="{gid}.json"'})


@router.get("/tags")
def list_tags(st: AppState = Depends(require_auth)):
    return st.db.all("SELECT tag, COUNT(*) AS count FROM tags t JOIN generations g ON g.id = t.generation_id "
                     "WHERE g.deleted_at IS NULL GROUP BY tag ORDER BY count DESC, tag LIMIT 500")


@router.get("/library/models")
def library_models(st: AppState = Depends(require_auth)):
    return st.db.all("SELECT model_id, type, COUNT(*) AS count FROM generations WHERE deleted_at IS NULL "
                     "AND model_id IS NOT NULL GROUP BY model_id, type ORDER BY count DESC")


# --------------------------------------------------------------- collections
@router.get("/collections")
def list_collections(st: AppState = Depends(require_auth)):
    rows = st.db.all("SELECT c.*, (SELECT COUNT(*) FROM collection_items ci WHERE ci.collection_id = c.id) AS count "
                     "FROM collections c ORDER BY c.name")
    for r in rows:
        cover = st.db.one("SELECT g.thumb_file_id FROM collection_items ci JOIN generations g ON g.id = ci.generation_id "
                          "WHERE ci.collection_id = ? AND g.deleted_at IS NULL ORDER BY ci.added_at DESC LIMIT 1", [r["id"]])
        r["cover_url"] = st.storage.file_url(cover["thumb_file_id"]) if cover else None
    return rows


@router.post("/collections")
def create_collection(body: dict[str, Any] = Body(...), st: AppState = Depends(require_auth)):
    row = {"id": new_id("co_"), "name": (body.get("name") or "Collection")[:120], "created_at": now()}
    st.db.insert("collections", row)
    return row


@router.patch("/collections/{cid}")
def rename_collection(cid: str, body: dict[str, Any] = Body(...), st: AppState = Depends(require_auth)):
    st.db.update("collections", cid, {"name": (body.get("name") or "Collection")[:120]})
    return st.db.one("SELECT * FROM collections WHERE id = ?", [cid])


@router.delete("/collections/{cid}")
def delete_collection(cid: str, st: AppState = Depends(require_auth)):
    st.db.execute("DELETE FROM collections WHERE id = ?", [cid])
    return {"ok": True}


@router.post("/collections/{cid}/items")
def add_items(cid: str, body: dict[str, Any] = Body(...), st: AppState = Depends(require_auth)):
    for gid in body.get("generation_ids") or []:
        st.db.execute("INSERT OR IGNORE INTO collection_items(collection_id, generation_id, added_at) VALUES (?, ?, ?)",
                      [cid, gid, now()])
    return {"ok": True}


@router.delete("/collections/{cid}/items/{gid}")
def remove_item(cid: str, gid: str, st: AppState = Depends(require_auth)):
    st.db.execute("DELETE FROM collection_items WHERE collection_id = ? AND generation_id = ?", [cid, gid])
    return {"ok": True}


# --------------------------------------------------------------------- files
@router.get("/files/{fid}")
def get_file(fid: str, request: Request, exp: str | None = None, sig: str | None = None):
    st: AppState = request.app.state.sarness
    if not st.storage.verify(fid, exp, sig):
        require_auth(request)
    f = st.storage.get(fid)
    if not f:
        raise HTTPException(404, "file not found")
    path = st.storage.resolve(f["path"])
    if not path.exists():
        raise HTTPException(410, "file is missing on disk")
    name = f.get("original_name") or path.name
    return FileResponse(path, media_type=f["mime"], filename=None,
                        headers={"Cache-Control": "private, max-age=31536000, immutable",
                                 "ETag": f'"{f["sha256"][:32]}"' if f.get("sha256") else "",
                                 "X-Sarness-Filename": name})


@router.post("/files/{fid}/sign")
def sign_file(fid: str, st: AppState = Depends(require_auth)):
    if not st.storage.get(fid):
        raise HTTPException(404, "file not found")
    return {"url": st.storage.sign(fid)}


@router.post("/uploads")
async def upload(request: Request, file: UploadFile = File(...)):
    st = require_auth(request)
    data = await file.read()
    row = st.storage.save_upload(data, file.filename or "upload", file.content_type)
    return {**row, "url": st.storage.file_url(row["id"])}
