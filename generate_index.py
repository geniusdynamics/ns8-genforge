from pathlib import Path
import re
from datetime import datetime
import hashlib

def convert_markdown_table_to_html(md_table):
    lines = md_table.strip().split("\n")
    if len(lines) < 2:
        return ""

    headers = [col.strip() for col in lines[0].split('|') if col.strip()]
    rows = lines[2:]

    html = "<thead><tr>"
    for header in headers:
        html += f"<th>{header}</th>"
    html += "</tr></thead><tbody>"

    for row in rows:
        cols = [col.strip() for col in row.split('|') if col.strip()]
        if len(cols) != len(headers):
            continue
        html += "<tr>"
        for col in cols:
            html += f"<td>{col}</td>"
        html += "</tr>"

    html += "</tbody>"
    return html

def extract_tables_by_section(readme_text):
    sections = re.split(r'^##\s+', readme_text, flags=re.MULTILINE)
    content_blocks = []

    for section in sections:
        if not section.strip():
            continue

        lines = section.strip().splitlines()
        heading = lines[0].strip()
        body = '\n'.join(lines[1:])

        tables = re.findall(r'(\|.*\n\|[-|: ]+\n(?:\|.*\n?)*)', body)
        for table in tables:
            table_html = convert_markdown_table_to_html(table)
            if table_html:
                section_id = heading.lower().replace(" ", "-")
                content_blocks.append(f"<section id='{section_id}'><h2>{heading}</h2><table class='sortable'>{table_html}</table></section>")

    return "\n".join(content_blocks)

def hash_file(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        hasher.update(f.read())
    return hasher.hexdigest()

def main():
    readme_file = Path("README.md")
    script_file = Path(__file__)
    index_file = Path("index.html")

    if not readme_file.exists():
        print("README.md not found.")
        return

    # Check for changes in script or README
    readme_hash = hash_file(readme_file)
    script_hash = hash_file(script_file)
    combined_hash = hashlib.md5((readme_hash + script_hash).encode()).hexdigest()

    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    readme_text = readme_file.read_text(encoding="utf-8")
    content_html = extract_tables_by_section(readme_text)

    output = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>NS8 AppForge Index</title>
  <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/simpledotcss/simple.min.css\">
  <script src=\"https://cdn.jsdelivr.net/npm/tablesort@5.3.0/dist/tablesort.min.js\"></script>
  <style>
    body {{ max-width: 1200px; margin: auto; }}
    nav {{ position: sticky; top: 0; background: #fff; padding: 1rem; border-bottom: 1px solid #eee; }}
    nav ul {{ list-style: none; display: flex; flex-wrap: wrap; gap: 1rem; padding: 0; }}
    section {{ padding-top: 2rem; }}
    table.sortable {{ width: 100%; border-collapse: collapse; }}
    table.sortable th, table.sortable td {{ padding: 0.5em; border: 1px solid #ddd; }}
  </style>
</head>
<body>
  <header>
    <h1>NS8 AppForge App Index</h1>
    <p>Generated on {timestamp}</p>
  </header>
  <nav>
    <ul>
      {''.join([f'<li><a href="#'+sec.strip().splitlines()[0].lower().replace(' ', '-')+'">'+sec.strip().splitlines()[0]+'</a></li>' for sec in re.split(r'^##\s+', readme_text, flags=re.MULTILINE) if sec.strip()])}
    </ul>
  </nav>
  {content_html}
  <footer>
    <small>Hash: {combined_hash} | Last generated on {timestamp}</small>
  </footer>
  <script>
    document.querySelectorAll('table').forEach(t => new Tablesort(t));
  </script>
</body>
</html>"""

    index_file.write_text(output, encoding="utf-8")
    print("✅ index.html regenerated with timestamp and script hash.")

if __name__ == "__main__":
    main()
