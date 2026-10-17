import os
import re
import shutil
import subprocess
import markdown



REFERENCE_CSS = """
    @page {
        size: A4;
        margin: 2cm;
        @top-right {
            content: "Page " counter(page);
        }
    }
    * { box-sizing: border-box; }
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        line-height: 1.6;
        color: #333;
        max-width: 100%;
        margin: 0;
        padding: 20px;
        font-size: 10pt;
    }
    h1 {
        color: #046B99;
        font-size: 24pt;
        margin-top: 30px;
        margin-bottom: 15px;
        border-bottom: 3px solid #046B99;
        padding-bottom: 10px;
        page-break-before: always;
    }
    h1:first-of-type { page-break-before: auto; }
    h2 {
        color: #2E6995;
        font-size: 18pt;
        margin-top: 25px;
        margin-bottom: 12px;
        border-bottom: 2px solid #2E6995;
        padding-bottom: 8px;
    }
    h3 { color: #046B99; font-size: 14pt; margin-top: 20px; margin-bottom: 10px; }
    h4 { color: #555; font-size: 12pt; margin-top: 15px; margin-bottom: 8px; }
    p { margin: 10px 0; text-align: justify; }
    code {
        background-color: #f4f4f4;
        padding: 2px 6px;
        border-radius: 3px;
        font-family: "Courier New", Courier, monospace;
        font-size: 9pt;
        color: #c7254e;
    }
    pre {
        background-color: #f8f8f8;
        border: 1px solid #ddd;
        border-left: 4px solid #046B99;
        padding: 12px;
        overflow-x: auto;
        margin: 15px 0;
        border-radius: 4px;
        font-size: 8pt;
        line-height: 1.4;
        page-break-inside: avoid;
    }
    pre code { background-color: transparent; padding: 0; color: #333; font-size: 8pt; }
    table {
        border-collapse: collapse;
        width: 100%;
        margin: 15px 0;
        font-size: 9pt;
        page-break-inside: avoid;
    }
    table th {
        background-color: #046B99;
        color: white;
        padding: 10px;
        text-align: left;
        font-weight: bold;
    }
    table td { border: 1px solid #ddd; padding: 8px; }
    table tr:nth-child(even) { background-color: #f9f9f9; }
    ul, ol { margin: 10px 0; padding-left: 30px; }
    li { margin: 5px 0; }
    blockquote {
        border-left: 4px solid #046B99;
        padding-left: 15px;
        margin: 15px 0;
        color: #666;
        font-style: italic;
    }
    hr { border: none; border-top: 2px solid #ddd; margin: 25px 0; }
    a { color: #046B99; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .toc { background-color: #f8f8f8; padding: 20px; border-radius: 5px; margin: 20px 0; }
    h2, h3, h4 { page-break-after: avoid; }
    ul, ol, table { page-break-inside: avoid; }
    .cover { text-align: center; padding: 100px 0; }
    .cover h1 { font-size: 32pt; border-bottom: none; margin-bottom: 30px; }
    .metadata { color: #666; font-size: 11pt; margin: 10px 0; }
    .diagram {
        text-align: center;
        margin: 20px 0;
        max-width: 100%;
        overflow: auto;
        page-break-inside: avoid;
    }
    .diagram svg {
        max-width: 100%;
        height: auto;
    }
    .diagram-fallback {
        text-align: center;
        margin: 20px 0;
        color: #666;
        font-style: italic;
    }
"""


def _extract_mermaid_blocks(md_content: str) -> list:
    pattern = r"```mermaid\s*\n(.*?)```"
    return re.findall(pattern, md_content, re.DOTALL)


def _mmd_to_svg(job_dir: str, name: str) -> None:
    """
    Render name.mmd -> name.svg using Mermaid CLI if available locally.
    Does not run slow npm downloads. Saves .mmd in job_dir.
    """
    mmd_path = os.path.join(job_dir, f"{name}.mmd")
    svg_path = os.path.join(job_dir, f"{name}.svg")
    if os.path.isfile(svg_path):
        return
    if not os.path.isfile(mmd_path):
        return

    mmdc_bin = shutil.which("mmdc")
    if not mmdc_bin:
        return

    try:
        subprocess.run(
            [
                mmdc_bin, "-i", f"{name}.mmd", "-o", f"{name}.svg",
                "-t", "neutral", "-b", "transparent", "--scale", "2", "-q",
            ],
            cwd=job_dir,
            capture_output=True,
            timeout=10,
        )
    except Exception:
        pass


def _read_svg_inline(svg_path: str) -> str:
    """Read SVG file and return raw content for inline embed."""
    if not os.path.isfile(svg_path):
        return ""
    with open(svg_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read().strip()


def _markdown_to_html_inline_svg(md_content: str, job_dir: str) -> str:
    blocks = _extract_mermaid_blocks(md_content)
    if not blocks:
        html_body = markdown.markdown(md_content, extensions=["extra"])
        return _wrap_html(html_body)

    inline_diagrams = []
    for i, code in enumerate(blocks):
        name = f"diagram_{i}"
        mmd_path = os.path.join(job_dir, f"{name}.mmd")
        svg_path = os.path.join(job_dir, f"{name}.svg")
        try:
            if not os.path.isfile(mmd_path):
                with open(mmd_path, "w", encoding="utf-8") as f:
                    f.write(code.strip())
            _mmd_to_svg(job_dir, name)
            svg_content = _read_svg_inline(svg_path)
            if svg_content:
                inline_diagrams.append(
                    f'<div class="diagram" style="text-align:center; margin: 20px 0;">{svg_content}</div>'
                )
            else:
                inline_diagrams.append(
                    f'<pre class="mermaid" style="text-align:center; margin: 20px 0;">{code.strip()}</pre>'
                )
        except Exception:
            inline_diagrams.append(
                f'<pre class="mermaid" style="text-align:center; margin: 20px 0;">{code.strip()}</pre>'
            )

    placeholder_fmt = "INLINE_SVG_BLOCK_{}"
    new_md = md_content
    pattern = r"```mermaid\s*\n.*?```"
    for i in range(len(blocks)):
        match = re.search(pattern, new_md, re.DOTALL)
        if match:
            new_md = new_md[: match.start()] + "\n\n" + placeholder_fmt.format(i) + "\n\n" + new_md[match.end() :]
    html_body = markdown.markdown(new_md, extensions=["extra"])
    for i, div_html in enumerate(inline_diagrams):
        token = placeholder_fmt.format(i)
        for pattern_str in (f"<p>{token}</p>", token):
            html_body = html_body.replace(pattern_str, div_html, 1)
    return _wrap_html(html_body)


def _wrap_html(html_body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Repository Architecture Documentation</title>
  <style>
{REFERENCE_CSS}
  </style>
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ startOnLoad: true, theme: 'neutral' }});
  </script>
</head>
<body>
  <div class="content">{html_body}</div>
</body>
</html>"""


def _markdown_to_html_legacy(md_content: str, job_dir: str) -> str:
    html_body = markdown.markdown(md_content, extensions=["extra"])
    diagram_block = ""
    mmd_path = os.path.join(job_dir, "diagram.mmd")
    svg_path = os.path.join(job_dir, "diagram.svg")
    if os.path.isfile(mmd_path):
        try:
            _mmd_to_svg(job_dir, "diagram")
            svg_content = _read_svg_inline(svg_path)
            if svg_content:
                diagram_block = f'<div class="diagram" style="text-align:center; margin: 20px 0;">{svg_content}</div>'
            else:
                with open(mmd_path, "r", encoding="utf-8", errors="replace") as f:
                    diagram_block = f'<pre class="mermaid" style="text-align:center; margin: 20px 0;">{f.read().strip()}</pre>'
        except Exception:
            pass
    return _wrap_html(html_body + diagram_block)


def _find_browser_executable() -> str | None:
    custom_path = os.environ.get("CHROME_BIN") or os.environ.get("BROWSER_PATH")
    if custom_path and os.path.isfile(custom_path):
        return custom_path

    for name in ["msedge", "chrome", "google-chrome", "chromium", "brave"]:
        found = shutil.which(name)
        if found:
            return found

    candidates = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def _render_html_to_pdf_browser(browser_path: str, html_str: str, pdf_path: str, job_dir: str) -> bool:
    temp_html = os.path.join(job_dir, "temp_print.html")
    try:
        with open(temp_html, "w", encoding="utf-8") as f:
            f.write(html_str)
        abs_html = os.path.abspath(temp_html)
        abs_pdf = os.path.abspath(pdf_path)

        cmd = [
            browser_path,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            "--run-all-compositor-stages-before-draw",
            f"--print-to-pdf={abs_pdf}",
            abs_html,
        ]
        subprocess.run(cmd, cwd=job_dir, capture_output=True, timeout=60)
        return os.path.isfile(pdf_path) and os.path.getsize(pdf_path) > 0
    except Exception:
        return False
    finally:
        if os.path.isfile(temp_html):
            try:
                os.remove(temp_html)
            except OSError:
                pass


def ensure_pdf(job_dir: str) -> None:
    pdf_path = os.path.join(job_dir, "final.pdf")
    if os.path.isfile(pdf_path) and os.path.getsize(pdf_path) > 0:
        return
    doc_path = os.path.join(job_dir, "documentation.md")
    if not os.path.isfile(doc_path):
        raise FileNotFoundError("documentation.md not found")
    with open(doc_path, "r", encoding="utf-8", errors="replace") as f:
        md_content = f.read()
    if _extract_mermaid_blocks(md_content):
        html_str = _markdown_to_html_inline_svg(md_content, job_dir)
    else:
        html_str = _markdown_to_html_legacy(md_content, job_dir)

    # 1. Primary: Use headless Chromium browser (Edge, Chrome, Chromium)
    browser = _find_browser_executable()
    if browser:
        ok = _render_html_to_pdf_browser(browser, html_str, pdf_path, job_dir)
        if ok and os.path.isfile(pdf_path) and os.path.getsize(pdf_path) > 0:
            return

    # 2. Secondary: Try WeasyPrint if available
    try:
        from weasyprint import HTML
        base_url = os.path.dirname(os.path.abspath(doc_path))
        HTML(string=html_str, base_url=base_url).write_pdf(pdf_path)
        if os.path.isfile(pdf_path) and os.path.getsize(pdf_path) > 0:
            return
    except Exception:
        pass

    if not os.path.isfile(pdf_path) or os.path.getsize(pdf_path) == 0:
        raise RuntimeError("PDF generation failed: Headless browser (Edge/Chrome) or WeasyPrint not available.")
