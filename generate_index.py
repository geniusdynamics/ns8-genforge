"from pathlib import Path
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
                content_blocks.append(f"<section id='{section_id}'><h2>{heading}</h2><input class='table-search' placeholder='🔍 Filter apps...'><div class='table-wrapper'><table class='sortable filterable'>{table_html}</table></div></section>")

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

    readme_hash = hash_file(readme_file)
    script_hash = hash_file(script_file)
    combined_hash = hashlib.md5((readme_hash + script_hash).encode()).hexdigest()

    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    readme_text = readme_file.read_text(encoding="utf-8")
    content_html = extract_tables_by_section(readme_text)

    output = f"""<!DOCTYPE html>
<html lang='en'>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>NS8 AppForge Index</title>
  <link rel='stylesheet' href='https://cdn.jsdelivr.net/npm/simpledotcss/simple.min.css'>
  <script src='https://cdn.jsdelivr.net/npm/tablesort@5.3.0/dist/tablesort.min.js'></script>
  <style>
    body {{ margin: 0; font-family: system-ui, sans-serif; }}
    header {{ background: #0b7285; color: white; padding: 1.5rem; text-align: center; }}
    .metadata-note {{ font-size: 0.9rem; background: #e3fafc; color: #0b7285; padding: 0.5rem; margin-bottom: 1.5rem; border-left: 4px solid #0b7285; }}
    .sidebar {{ position: fixed; top: 0; left: 0; width: 220px; height: 100vh; overflow-y: auto; background: #f8f9fa; padding: 1rem; border-right: 1px solid #dee2e6; }}
    .sidebar h2 {{ font-size: 1.1rem; margin-bottom: 0.5rem; }}
    .sidebar ul {{ list-style: none; padding-left: 0; }}
    .sidebar li {{ margin-bottom: 0.4rem; }}
    .sidebar a {{ text-decoration: none; color: #0b7285; }}
    main {{ margin-left: 240px; padding: 2rem; }}
    section {{ margin-bottom: 3rem; }}
    .table-wrapper {{ overflow-x: auto; }}
    .table-search {{ width: 100%; padding: 0.5rem; margin-bottom: 0.5rem; }}
    .theme-toggle {{ position: fixed; top: 1rem; right: 1rem; background: #0b7285; color: white; border: none; padding: 0.5rem 1rem; cursor: pointer; }}
    .dark-mode {{ background-color: #1e1e1e; color: #f1f1f1; }}
    .dark-mode .sidebar {{ background: #292929; border-color: #444; }}
    .dark-mode .sidebar a {{ color: #91d1ff; }}
    .dark-mode .theme-toggle {{ background: #91d1ff; color: #111; }}
  </style>
</head>
<body>
  <button class='theme-toggle' onclick='toggleTheme()'>🌙 Toggle Theme</button>
  <aside class='sidebar'>
    <h2>📚 Contents</h2>
    <ul>
      {''.join([f'<li><a href="#'+sec.strip().splitlines()[0].lower().replace(' ', '-')+'">'+sec.strip().splitlines()[0]+'</a></li>' for sec in re.split(r'^##\s+', readme_text, flags=re.MULTILINE) if sec.strip()])}
    </ul>
  </aside>
  <main>
    <header>
      <h1>NS8 AppForge</h1>
      <p class='metadata-note'>📅 Metadata are built every 4 hours at 00:25, 06:25, 12:25, 18:25 UTC and on each commit to the main branch.</p>
    </header>
    <section id='apps'>
      <h2>🧩 Application List</h2>
      {content_html}
    </section>
    <footer>
      <small>Hash: {combined_hash} | Last generated on {timestamp}</small>
    </footer>
  </main>
  <script>
    document.querySelectorAll('table.sortable').forEach(t => new Tablesort(t));
    document.querySelectorAll('input.table-search').forEach(input => {
      input.addEventListener('input', e => {
        const filter = e.target.value.toLowerCase();
        const rows = e.target.nextElementSibling.querySelectorAll('tbody tr');
        rows.forEach(row => {
          row.style.display = [...row.children].some(td => td.textContent.toLowerCase().includes(filter)) ? '' : 'none';
        });
      });
    });
    function toggleTheme() {
      document.body.classList.toggle('dark-mode');
    }
  </script>
</body>
</html>"""

    index_file.write_text(output, encoding="utf-8")
    print("✅ index.html regenerated with timestamp and script hash.")


if __name__ == "__main__":
    main()
