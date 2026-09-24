path = "app/routers/document.py"
with open(path) as f:
    content = f.read()

marker = "# --- Ruční nahrávání faktur (PDF) - dokud iDoklad integrace není znovu ---"
count = content.count(marker)
if count != 1:
    print(f"CHYBA: marker nalezen {count}x")
else:
    new_endpoint = '''@router.get("/documents/{document_id}/vop-snapshot")
def download_vop_snapshot(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stáhne uložený snapshot VOP (přesné znění v době potvrzení) - jen pro přihlášené uživatele CRM."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document or not document.vop_snapshot_filename:
        raise HTTPException(status_code=404, detail="Snapshot VOP nenalezen")
    file_path = VOP_SNAPSHOT_DIR / document.vop_snapshot_filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Soubor snapshotu VOP nenalezen na disku")
    return FileResponse(file_path, media_type="application/pdf", filename=f"VOP_{document_id}.pdf")


''' + marker

    content = content.replace(marker, new_endpoint, 1)
    with open(path, 'w') as f:
        f.write(content)
    print("Endpoint pro stazeni VOP snapshotu pridan")
