from tools.pipeline_paths import get_space_id
#!/usr/bin/env python3
"""D799: Nuclear reset — delete ALL FBs from Anytype and clear push ledger.

CRITICAL: This is IRREVERSIBLE. Maxwell explicitly authorized this.
Usage: python3 tools/nuke_anytype.py --confirm
       python3 tools/nuke_anytype.py --dry-run  (list only, no delete)
"""
import json, os, sys, time, argparse, requests
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
ANYTYPE_URL = "http://127.0.0.1:31009"
ANYTYPE_KEY = "f8JwVR/tR7XakA+6B7x23YBuTEiMxkem1YlLM/lXkRc="
HEADERS = {"Authorization": f"Bearer {ANYTYPE_KEY}", "Content-Type": "application/json"}
LEDGER = ROOT / "push_ledger.jsonl"

SPACES = {
    "Non-Private (KB)": get_space_id("non_private"),
    "Private (DP)": get_space_id("private"),
}


def list_objects(space_id: str) -> list:
    """List all objects in a space, paginated."""
    objects = []
    offset = 0
    limit = 200
    
    while True:
        url = f"{ANYTYPE_URL}/v1/spaces/{space_id}/objects?limit={limit}&offset={offset}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code != 200:
                print(f"  HTTP {r.status_code} at offset {offset}: {r.text[:100]}")
                break
            data = r.json()
            batch = data.get("data", [])
            if not batch:
                break
            objects.extend(batch)
            offset += len(batch)
            if len(batch) < limit:
                break
        except Exception as e:
            print(f"  Error at offset {offset}: {e}")
            break
    
    return objects


def delete_object(space_id: str, object_id: str, name: str = "") -> bool:
    """Delete a single object from Anytype."""
    url = f"{ANYTYPE_URL}/v1/spaces/{space_id}/objects/{object_id}"
    try:
        r = requests.delete(url, headers=HEADERS, timeout=15)
        if r.status_code in (200, 204):
            return True
        else:
            print(f"  DELETE {name[:40]}: HTTP {r.status_code}")
            return False
    except Exception as e:
        print(f"  DELETE {name[:40]}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true", help="Actually delete (required)")
    parser.add_argument("--dry-run", action="store_true", help="List only, no delete")
    args = parser.parse_args()
    
    if not args.confirm and not args.dry_run:
        print("ERROR: Must specify --confirm to delete or --dry-run to list")
        print("  python3 tools/nuke_anytype.py --dry-run")
        print("  python3 tools/nuke_anytype.py --confirm")
        sys.exit(1)
    
    all_objects = {}
    total = 0
    fb_count = 0
    
    for label, space_id in SPACES.items():
        print(f"\n{'='*60}")
        print(f"Space: {label}")
        print(f"  ID: {space_id}")
        
        objects = list_objects(space_id)
        all_objects[label] = objects
        print(f"  Total objects: {len(objects)}")
        
        # Count by type
        from collections import Counter
        types = Counter()
        fbs = []
        for obj in objects:
            t = obj.get("type", obj.get("type_key", "unknown"))
            if isinstance(t, dict):
                t = t.get("key", t.get("name", "dict"))
            types[str(t)] += 1
            # FB types
            t_str = str(t).lower()
            if "fb" in t_str or "foundational" in t_str or "block" in t_str:
                fbs.append(obj)
        
        print(f"  Types: {dict(types.most_common(5))}")
        print(f"  FB-like objects: {len(fbs)}")
        fb_count += len(fbs)
        total += len(objects)
        
        if fbs:
            print(f"  Sample FBs:")
            for obj in fbs[:3]:
                oid = obj.get("id", "?")[:40]
                raw_name = obj.get("name", "?")
                if isinstance(raw_name, dict):
                    raw_name = raw_name.get("name", str(raw_name))
                name = str(raw_name)[:50]
                print(f"    {oid} | {name}")
    
    print(f"\n{'='*60}")
    print(f"SUMMARY: {total} total objects, ~{fb_count} FB-like objects across both spaces")
    
    if args.dry_run:
        print("\n[DRY RUN] No objects deleted. Use --confirm to actually delete.")
        return
    
    if not args.confirm:
        return
    
    # BACKUP ledger first
    if LEDGER.exists():
        backup = Path(f"{LEDGER}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        backup.write_text(LEDGER.read_text())
        print(f"\nLedger backed up to: {backup}")
    
    # DELETE only FB objects (not collections, bookmarks, pages, etc.)
    print(f"\n{'='*60}")
    print("DELETING ALL FBs FROM ANYTYPE (other objects preserved)")
    print(f"{'='*60}")
    
    deleted = 0
    failed = 0
    skipped = 0
    
    for label, space_id in SPACES.items():
        objects = all_objects.get(label, [])
        
        # SAFETY: Only delete FB-type objects (foundational_block / foundation_block).
        # NEVER touch collections, bookmarks, pages, notes, tasks, types, or property schemas.
        # The DELETE endpoint only removes object instances, not type definitions.
        FB_TYPE_PATTERNS = ["foundational_block", "foundation_block"]
        fbs = []
        non_fbs = []
        for obj in objects:
            t = obj.get("type", obj.get("type_key", ""))
            if isinstance(t, dict):
                t = t.get("key", t.get("name", ""))
            t_str = str(t).lower()
            # Only match exact FB type patterns — NOT "collection", "page", etc.
            if any(pat in t_str for pat in FB_TYPE_PATTERNS):
                fbs.append(obj)
            else:
                non_fbs.append(obj)
        
        non_fb_types = set()
        for obj in non_fbs:
            t = obj.get("type", obj.get("type_key", ""))
            if isinstance(t, dict): t = t.get("key", t.get("name", ""))
            non_fb_types.add(str(t))
        
        print(f"\n  {label}: {len(fbs)} FBs to delete")
        print(f"           {len(non_fbs)} non-FBs PRESERVED: {sorted(non_fb_types)}")
        
        for i, obj in enumerate(fbs):
            oid = obj.get("id", "")
            raw_name = obj.get("name", "")
            if isinstance(raw_name, dict):
                raw_name = raw_name.get("name", str(raw_name))
            
            if delete_object(space_id, oid, str(raw_name)):
                deleted += 1
            else:
                failed += 1
            
            if (i + 1) % 50 == 0:
                print(f"    Progress: {i+1}/{len(fbs)} | ✓{deleted} ✗{failed}")
            
            time.sleep(0.1)  # Rate limit
    
    print(f"\n  Deleted: {deleted} | Failed: {failed}")
    
    # Clear ledger
    if deleted > 0:
        LEDGER.write_text("")
        print(f"\nPush ledger cleared: {LEDGER}")
    
    print(f"\n{'='*60}")
    print("NUKE COMPLETE (FBs only)")
    print(f"  Deleted: {deleted} FBs")
    print(f"  Failed:  {failed}")
    print(f"  Preserved: {skipped} non-FB objects")
    print(f"  Ledger: cleared")
    print(f"  Next: Align S7 → push fresh from clean state")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
