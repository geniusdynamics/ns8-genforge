from pathlib import Path
import re
from datetime import datetime
from string import Template
import json


def parse_readme_tables(readme_text):
    sections = re.split(r'^##\s+', readme_text, flags=re.MULTILINE)
    app_cards = []

    for section in sections:
        lines = section.strip().splitlines()
        if not lines:
            continue

        category = lines[0].strip()
        body = '\n'.join(lines[1:])

        tables = re.findall(r'(\|.*\n\|[-|: ]+\n(?:\|.*\n?)*)', body)
        for table in tables:
            rows = table.strip().splitlines()[2:]  # Skip headers
            for row in rows:
                cols = [c.strip() for c in row.split('|') if c.strip()]
                if len(cols) >= 2:
                    app_name = cols[0]
                    description = cols[1] if len(cols) > 1 else ""
                    link = cols[2] if len(cols) > 2 else ""
                    icon = cols[3] if len(cols) > 3 else ""
                    app_cards.append({
                        "category": category,
                        "name": app_name,
                        "desc": description,
                        "link": link,
                        "icon": icon
                    })
    return app_cards


def generate_html(cards):
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    categories = sorted(set(card['category'] for card in cards))
    json_cards = json.dumps(cards)

    html_template = Template("""
    <!DOCTYPE html>
    <html lang=\"en\">
    <head>
        <meta charset=\"UTF-8\">
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
        <title>NS8 AppForge</title>
        <script src=\"https://cdn.tailwindcss.com\"></script>
        <script>
          tailwind.config = { darkMode: 'class' }
        </script>
        <style>
            .card {
                background: white;
                border-radius: 0.5rem;
                padding: 1rem;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .dark .card {
                background-color: #1e293b;
                color: #e2e8f0;
            }
        </style>
    </head>
    <body class=\"bg-gray-100 dark:bg-gray-900 text-gray-800 dark:text-gray-200\">
        <div class=\"flex\">
            <aside class=\"w-64 min-h-screen p-4 border-r border-gray-300 dark:border-gray-700\">
                <h2 class=\"text-lg font-semibold mb-4\">🧭 Categories</h2>
                <ul id=\"category-list\" class=\"space-y-2\">
                    <li><a href=\"#\" data-filter=\"All\" class=\"text-blue-600 hover:underline\">All</a></li>
                    $category_links
                </ul>
                <div class=\"mt-6\">
                    <button onclick=\"toggleTheme()\" class=\"bg-gray-700 text-white px-3 py-1 rounded\">Toggle Theme</button>
                </div>
            </aside>
            <main class=\"flex-1 p-6\">
                <h1 class=\"text-3xl font-bold mb-2\">NS8 AppForge</h1>
                <p class=\"text-sm text-gray-500 mb-6\">Metadata built at $timestamp UTC</p>

                <input id=\"search\" type=\"text\" placeholder=\"🔍 Search apps...\" class=\"w-full px-4 py-2 mb-6 border rounded\"/>

                <div id=\"app-grid\" class=\"grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4\"></div>
            </main>
        </div>

        <script>
          const apps = $json_cards;
          const grid = document.getElementById('app-grid');
          const search = document.getElementById('search');
          const links = document.querySelectorAll('#category-list a');

          let currentFilter = 'All';

          function render() {
            grid.innerHTML = '';
            const query = search.value.toLowerCase();
            const filtered = apps.filter(app => {
              const matchFilter = currentFilter === 'All' || app.category === currentFilter;
              const matchQuery = app.name.toLowerCase().includes(query) || app.desc.toLowerCase().includes(query);
              return matchFilter && matchQuery;
            });
            for (const app of filtered) {
              const el = document.createElement('div');
              el.className = 'card';
              el.innerHTML = `
                ${app.icon ? `<img src="${app.icon}" alt="${app.name}" class="h-10 w-10 mb-2">` : ''}
                <h3 class='text-xl font-semibold mb-1'>${app.name}</h3>
                <p class='text-sm text-gray-600 dark:text-gray-400 mb-2'>${app.category}</p>
                <p class='mb-2 line-clamp-3'>${app.desc}</p>
                <div class='flex gap-2 mt-2'>
                  ${app.link ? `<a href="${app.link}" class="text-sm bg-blue-500 text-white px-3 py-1 rounded hover:bg-blue-600" target="_blank">📥 Download</a>` : ''}
                  <button onclick="alert(\"${app.desc.replace(/'/g, "\'")}\")" class="text-sm bg-gray-200 dark:bg-gray-700 px-3 py-1 rounded">📄 Details</button>
                </div>
              `;
              grid.appendChild(el);
            }
          }

          links.forEach(link => link.addEventListener('click', e => {
            e.preventDefault();
            currentFilter = e.target.dataset.filter;
            render();
          }));

          search.addEventListener('input', render);
          render();

          function toggleTheme() {
            document.body.classList.toggle('dark');
          }
        </script>
    </body>
    </html>
    """)

    category_links = '\n'.join(
        f'<li><a href="#" data-filter="{c}" class="hover:underline">{c}</a></li>' for c in categories
    )

    return html_template.substitute(
        timestamp=timestamp,
        category_links=category_links,
        json_cards=json_cards
    )


def main():
    readme_path = Path("README.md")
    output_path = Path("index.html")

    if not readme_path.exists():
        print("❌ README.md not found")
        return

    readme_content = readme_path.read_text(encoding="utf-8")
    cards = parse_readme_tables(readme_content)
    html_output = generate_html(cards)
    output_path.write_text(html_output, encoding="utf-8")
    print("✅ index.html generated successfully.")


if __name__ == '__main__':
    main()
