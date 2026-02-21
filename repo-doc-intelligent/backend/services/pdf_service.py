import os
import re
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
    Render name.mmd -> name.svg using Mermaid CLI.
    Raises RuntimeError if mmdc fails. Saves .mmd in job_dir.
    """
    mmd_path = os.path.join(job_dir, f"{name}.mmd")
    svg_path = os.path.join(job_dir, f"{name}.svg")
    if not os.path.isfile(mmd_path):
        raise RuntimeError(f"Mermaid source not found: {mmd_path}")
    result = subprocess.run(
        [
            "npx", "-y", "@mermaid-js/mermaid-cli",
            "mmdc", "-i", f"{name}.mmd", "-o", f"{name}.svg",
            "-t", "neutral", "-b", "transparent", "--scale", "2", "-q",
        ],
        cwd=job_dir,
        capture_output=True,
        timeout=90,
    )
    if result.returncode != 0:
        stderr = (result.stderr or b"").decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Mermaid CLI (mmdc) failed: {stderr or 'unknown error'}")
    if not os.path.isfile(svg_path):
        raise RuntimeError(f"SVG output not found after mmdc: {svg_path}")


def _read_svg_inline(svg_path: str) -> str:
    """Read SVG file and return raw content for inline embed."""
    if not os.path.isfile(svg_path):
        return ""
    with open(svg_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read().strip()


def _markdown_to_html_inline_svg(md_content: str, job_dir: str) -> str:
    """
    Extract each ```mermaid block, save as diagram_{i}.mmd, render to SVG via mmdc,
    read SVG and inline embed into HTML. No raw Mermaid in output, no img tags.
    """
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
                    '<div class="diagram-fallback">Diagram not available.</div>'
                )
        except RuntimeError:
            inline_diagrams.append(
                '<div class="diagram-fallback">Diagram could not be rendered.</div>'
            )
        except OSError:
            inline_diagrams.append(
                '<div class="diagram-fallback">Diagram file error.</div>'
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
        for pattern in (f"<p>{token}</p>", token):
            html_body = html_body.replace(pattern, div_html, 1)
    return _wrap_html(html_body)


def _wrap_html(html_body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Codebase Documentation</title>
  <style>
{REFERENCE_CSS}
  </style>
</head>
<body>
  <div class="content">{html_body}</div>
</body>
</html>"""


def _markdown_to_html_legacy(md_content: str, job_dir: str) -> str:
    """Single diagram.mmd -> diagram.svg, inline embed for PDF. Skip with message if mmdc fails or SVG missing."""
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
                diagram_block = '<div class="diagram-fallback">Diagram not available.</div>'
        except RuntimeError:
            diagram_block = '<div class="diagram-fallback">Diagram could not be rendered.</div>'
    return _wrap_html(html_body + diagram_block)


def ensure_pdf(job_dir: str) -> None:
    pdf_path = os.path.join(job_dir, "final.pdf")
    if os.path.isfile(pdf_path):
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
    base_url = os.path.dirname(os.path.abspath(doc_path))
    try:
        from weasyprint import HTML
    except OSError as e:
        raise RuntimeError(
            "PDF generation requires WeasyPrint system libraries (Pango, GLib). "
            "On macOS: brew install pango glib. See https://doc.courtbouillon.org/weasyprint/stable/first_steps.html"
        ) from e
    HTML(string=html_str, base_url=base_url).write_pdf(pdf_path)
