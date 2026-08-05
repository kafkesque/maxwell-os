#!/usr/bin/env python3
"""A/B test: Original EPUB/PDF → stage0_convert.py vs pre-converted MD quality."""

import json, re, subprocess, sys, tempfile, shutil
from pathlib import Path
from collections import Counter

ORIGINALS_BASE = Path("/Users/barn/Library/CloudStorage/Dropbox/education/books")
PIPELINE_BASE = Path("/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0/knowledge pipeline/books")
STAGE0_SCRIPT = Path("/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0/pipeline/stage0_convert.py")

# ── 5 test candidates (diverse domains + formats) ──
TEST_BOOKS = [
    {
        "label": "D0_Decisive_EPUB",
        "orig": "epub/DOMAIN 0 Systems + Decision/decision-making+psychology/Decisive How to Make Better Choices in Life and Work (Chip Heath) (z-library.sk, 1lib.sk, z-lib.sk).epub",
        "md": "DOMAIN 0 Systems + Decision/decision-making+psychology/Decisive How to Make Better Choices in Life and Work (Chip Heath) (z-library.sk, 1lib.sk, z-lib.sk).md",
    },
    {
        "label": "D2_UIPedia_PDF",
        "orig": "pdf/DOMAIN 2 Design/ui+ux/UI Pedia - A Complete UI Design Guide (Pixsel Academy) (z-library.sk, 1lib.sk, z-lib.sk).pdf",
        "md": "DOMAIN 2 Design/ui+ux/UI Pedia - A Complete UI Design Guide (Pixsel Academy) (z-library.sk, 1lib.sk, z-lib.sk).md",
    },
    {
        "label": "D4_ProductLed_EPUB",
        "orig": "epub/DOMAIN 4 Business/marketing+growth/Product-Led Growth How to Build a Product That Sells Itself (Wes Bush ) (z-library.sk, 1lib.sk, z-lib.sk).epub",
        "md": "DOMAIN 4 Business/marketing+growth/Product-Led Growth How to Build a Product That Sells Itself (Wes Bush ) (z-library.sk, 1lib.sk, z-lib.sk).md",
    },
    {
        "label": "D6_StableDiffusion_PDF",
        "orig": "pdf/DOMAIN 6 AI + Computing/ai agents/Stable Diffusion Prompt Book From OpenArt (Mohamad Diab, Julian Herrera, Bob Chernow, Assem Utelbayeva, Michelle Lee) (z-library.sk, 1lib.sk, z-lib.sk).pdf",
        "md": "DOMAIN 6 AI + Computing/ai agents/Stable Diffusion Prompt Book From OpenArt (Mohamad Diab, Julian Herrera, Bob Chernow, Assem Utelbayeva, Michelle Lee) (z-library.sk, 1lib.sk, z-lib.sk).md",
    },
    {
        "label": "D1_WaysOfSeeing_EPUB",
        "orig": "epub/DOMAIN 1 Substrate — Mind, Math, Meaning/semiotics+language/Ways of Seeing John Berger liber3.epub",
        "md": "DOMAIN 1 Substrate — Mind, Math, Meaning/semiotics+language/Ways of Seeing John Berger liber3.md",
    },
]


def analyze_md_quality(text: str, label: str) -> dict:
    """Compute quality metrics for an MD file."""
    lines = text.split('\n')
    total_chars = len(text)
    total_lines = len(lines)
    
    # Section headers
    h1 = sum(1 for l in lines if re.match(r'^#\s+\S', l))
    h2 = sum(1 for l in lines if re.match(r'^##\s+\S', l))
    h3 = sum(1 for l in lines if re.match(r'^###\s+\S', l))
    
    # Noise
    page_nums = len(re.findall(r'^\s*\d{1,4}\s*$', text, re.MULTILINE))
    copyright_lines = sum(1 for l in lines if re.search(r'Copyright|All rights reserved|ISBN', l, re.I))
    toc_lines = sum(1 for l in lines if re.search(r'^\s*(Table of Contents|Contents)\s*$', l, re.I))
    short_lines = sum(1 for l in lines if 0 < len(l.strip()) < 10)
    
    # Paragraphs
    paras = [l.strip() for l in lines if len(l.strip()) > 40]
    avg_para_len = sum(len(p) for p in paras) / len(paras) if paras else 0
    median_para = sorted([len(p) for p in paras])[len(paras)//2] if paras else 0
    
    # Chunk boundary quality: 300-word windows starting at section boundaries
    # Count how many 300-word windows start at/after a header
    header_positions = [i for i, l in enumerate(lines) if re.match(r'^#{1,3}\s', l)]
    total_possible_boundaries = total_chars // 200  # rough chunk count at 200 chars avg
    header_boundary_ratio = len(header_positions) / max(total_possible_boundaries, 1)
    
    return {
        "label": label,
        "chars": total_chars,
        "lines": total_lines,
        "h1": h1, "h2": h2, "h3": h3,
        "total_headers": h1 + h2 + h3,
        "page_nums": page_nums,
        "copyright": copyright_lines,
        "toc": toc_lines,
        "short_lines": short_lines,
        "short_pct": round(short_lines / max(total_lines, 1) * 100, 1),
        "avg_para_len": int(avg_para_len),
        "median_para": median_para,
        "header_boundary_ratio": round(header_boundary_ratio, 3),
    }


def convert_original(orig_path: Path, output_dir: Path) -> Path | None:
    """Convert original EPUB/PDF to MD using stage0_convert.py --book flag."""
    cmd = [
        sys.executable, str(STAGE0_SCRIPT),
        "--book", str(orig_path),
    ]
    # We'll run it in a temp dir to avoid polluting the main pipeline
    env = {**__import__('os').environ}
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True,
            timeout=120,
            cwd=str(STAGE0_SCRIPT.parent.parent),
            env=env,
        )
        # stage0_convert writes to BOOKS_DIR/stage0_convert/...
        # Let's find the output
        stage0_out = STAGE0_SCRIPT.parent.parent / "knowledge pipeline" / "stage0_convert"
        # Find the most recently created .md file
        md_files = list(stage0_out.rglob("*.md"))
        if md_files:
            newest = max(md_files, key=lambda p: p.stat().st_mtime)
            # Copy to output dir
            dest = output_dir / f"{orig_path.stem}_stage0.md"
            shutil.copy(newest, dest)
            return dest
    except subprocess.TimeoutExpired:
        print(f"    ⏰ Timeout converting {orig_path.name}")
    except Exception as e:
        print(f"    ❌ Error: {e}")
    
    return None


def main():
    output_dir = Path(tempfile.mkdtemp(prefix="md_quality_test_"))
    print(f"Test output dir: {output_dir}")
    
    results = []
    
    for book in TEST_BOOKS:
        label = book["label"]
        print(f"\n{'='*60}")
        print(f"  {label}")
        print(f"{'='*60}")
        
        orig_path = ORIGINALS_BASE / book["orig"]
        md_path = PIPELINE_BASE / book["md"]
        
        # ── Analyze pre-converted MD ──
        if md_path.exists():
            pre_text = md_path.read_text(errors='replace')
            pre_metrics = analyze_md_quality(pre_text, f"{label}_PRECONVERTED")
            pre_metrics['source'] = 'pre-converted'
            pre_metrics['path'] = str(md_path)
            print(f"  📄 Pre-converted: {pre_metrics['chars']:,}c, h#={pre_metrics['total_headers']}, "
                  f"noise(p#={pre_metrics['page_nums']},©={pre_metrics['copyright']},toc={pre_metrics['toc']}), "
                  f"short={pre_metrics['short_pct']}%, ¶avg={pre_metrics['avg_para_len']}c")
            results.append(pre_metrics)
        else:
            print(f"  ❌ Pre-converted MD not found: {md_path}")
        
        # ── Convert original ──
        if orig_path.exists():
            print(f"  🔄 Converting {orig_path.suffix} → MD via stage0_convert.py...")
            converted = convert_original(orig_path, output_dir)
            if converted and converted.exists():
                conv_text = converted.read_text(errors='replace')
                conv_metrics = analyze_md_quality(conv_text, f"{label}_STAGE0")
                conv_metrics['source'] = 'stage0_convert'
                conv_metrics['path'] = str(converted)
                conv_metrics['orig_fmt'] = orig_path.suffix
                print(f"  ✨ Stage0 output:  {conv_metrics['chars']:,}c, h#={conv_metrics['total_headers']}, "
                      f"noise(p#={conv_metrics['page_nums']},©={conv_metrics['copyright']},toc={conv_metrics['toc']}), "
                      f"short={conv_metrics['short_pct']}%, ¶avg={conv_metrics['avg_para_len']}c")
                results.append(conv_metrics)
            else:
                print(f"  ❌ Conversion failed or no output")
        else:
            print(f"  ❌ Original not found: {orig_path}")
    
    # ── Summary Comparison ──
    print(f"\n{'='*60}")
    print(f"  COMPARISON SUMMARY")
    print(f"{'='*60}")
    print(f"{'Book':<30} {'Source':<15} {'Chars':>8} {'H#':>4} {'Page#':>5} {'©':>3} {'¶avg':>6} {'short%':>6}")
    print(f"{'-'*30} {'-'*15} {'-'*8} {'-'*4} {'-'*5} {'-'*3} {'-'*6} {'-'*6}")
    
    for r in sorted(results, key=lambda x: (x['label'], x['source'])):
        label_short = r['label'][:28]
        src_short = r['source'][:13]
        print(f"{label_short:<30} {src_short:<15} {r['chars']:>8,} {r['total_headers']:>4} "
              f"{r['page_nums']:>5} {r['copyright']:>3} {r['avg_para_len']:>6} {r['short_pct']:>5}%")
    
    # Aggregate
    pre = [r for r in results if r['source'] == 'pre-converted']
    s0 = [r for r in results if r['source'] == 'stage0_convert']
    
    if pre and s0:
        print(f"\n  AVERAGES:")
        print(f"  {'':30} {'Headers':>8} {'Page#':>6} {'Copyr':>6} {'¶avg':>7} {'short%':>7}")
        print(f"  {'Pre-converted':30} {sum(r['total_headers'] for r in pre)/len(pre):>8.1f} "
              f"{sum(r['page_nums'] for r in pre)/len(pre):>6.1f} "
              f"{sum(r['copyright'] for r in pre)/len(pre):>6.1f} "
              f"{sum(r['avg_para_len'] for r in pre)/len(pre):>7.0f} "
              f"{sum(r['short_pct'] for r in pre)/len(pre):>7.1f}")
        print(f"  {'Stage0 convert':30} {sum(r['total_headers'] for r in s0)/len(s0):>8.1f} "
              f"{sum(r['page_nums'] for r in s0)/len(s0):>6.1f} "
              f"{sum(r['copyright'] for r in s0)/len(s0):>6.1f} "
              f"{sum(r['avg_para_len'] for r in s0)/len(s0):>7.0f} "
              f"{sum(r['short_pct'] for r in s0)/len(s0):>7.1f}")
        
        # Winner per metric
        h_pre = sum(r['total_headers'] for r in pre)/len(pre)
        h_s0 = sum(r['total_headers'] for r in s0)/len(s0)
        n_pre = sum(r['page_nums'] for r in pre)/len(pre)
        n_s0 = sum(r['page_nums'] for r in s0)/len(s0)
        
        print(f"\n  🏆 Headers: {'Stage0' if h_s0 > h_pre else 'Pre-converted'} ({max(h_pre, h_s0):.1f} vs {min(h_pre, h_s0):.1f})")
        print(f"  🏆 Noise:   {'Stage0' if n_s0 < n_pre else 'Pre-converted'} (page#: {min(n_pre, n_s0):.1f} vs {max(n_pre, n_s0):.1f})")
    
    # Save results
    report_path = output_dir / "comparison_report.json"
    with open(report_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n📋 Full report: {report_path}")
    print(f"📁 Converted files: {output_dir}")


if __name__ == "__main__":
    main()
