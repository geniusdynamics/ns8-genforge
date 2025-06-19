from pathlib import Path
import re
from datetime import datetime, timezone
import json
import os
import requests
from jinja2 import Template

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def get_github_stars(repo_url, github_token=None):
    api_url = f"https://api.github.com/repos/{repo_url.replace('https://github.com/', '')}"
    headers = {'Accept': 'application/vnd.github.v3+json'}
    if github_token:
        headers['Authorization'] = f'token {github_token}'
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get('stargazers_count', 0)
    except:
        return 0

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
            rows = table.strip().splitlines()[2:]
            for row in rows:
                cols = [c.strip() for c in row.split('|') if c.strip()]
                if len(cols) >= 2:
                    name = cols[0]
                    m = re.match(r'\[(.*?)\]\((.*?)\)', name)
                    app_name = m.group(1) if m else name
                    app_link = m.group(2) if m else ""

                    description = cols[1] if len(cols) > 1 else ""
                    icon = cols[3] if len(cols) > 3 else ""
                    stars_raw = cols[4] if len(cols) > 4 else ""
                    stars = get_github_stars(stars_raw, GITHUB_TOKEN) if stars_raw.startswith("http") else stars_raw
                    alt = cols[5] if len(cols) > 5 else ""

                    app_cards.append({
                        "category": category,
                        "name": app_name,
                        "desc": description,
                        "link": app_link,
                        "repo_link": stars_raw if stars_raw.startswith("http") else "",
                        "stars": stars,
                        "alt": alt
                    })
    return app_cards

def generate_html(cards):
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
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
        <script>tailwind.config = { darkMode: 'class' }</script>
        <style>
            .card { background: white; border-radius: 0.5rem; padding: 1.25rem; box-shadow: 0 2px 6px rgba(0,0,0,0.1); display: flex; flex-direction: column; justify-content: space-between; height: 100%; }
            .dark .card { background-color: #1e293b; color: #e2e8f0; }
            .modal { background-color: rgba(0,0,0,0.5); position: fixed; top:0; left:0; right:0; bottom:0; display: flex; justify-content: center; align-items: center; }
            .modal-content { background: white; padding: 1.5rem; border-radius: 8px; max-width: 600px; width: 90%; }
            .dark .modal-content { background: #1e293b; color: #e2e8f0; }
        </style>
    </head>
    <body class=\"bg-gray-100 dark:bg-gray-900 text-gray-800 dark:text-gray-200\">
        <div class=\"flex\">
            <aside class=\"w-64 min-h-screen p-4 border-r border-gray-300 dark:border-gray-700\">
                <h2 class=\"text-lg font-semibold mb-4\">🧭 Categories</h2>
                <ul id=\"category-list\" class=\"space-y-2\">
                    <li><a href=\"#\" data-filter=\"All\" class=\"text-blue-600 hover:underline\">All</a></li>
                    {% for cat in categories %}<li><a href=\"#\" data-filter=\"{{ cat }}\" class=\"hover:underline\">{{ cat }}</a></li>{% endfor %}
                </ul>
                <div class=\"mt-6\">
                    <button onclick=\"toggleTheme()\" class=\"bg-gray-700 text-white px-3 py-1 rounded\">🌓 Toggle Theme</button>
                </div>
            </aside>
            <main class=\"flex-1 p-6\">
                <h1 class=\"text-3xl font-bold mb-2\">NS8 AppForge</h1>
                <p class=\"text-sm text-gray-500 mb-6\">Metadata built at {{ timestamp }}</p>
                <input id=\"search\" type=\"text\" placeholder=\"🔍 Search apps...\" class=\"w-full px-4 py-2 mb-6 border rounded\"/>
                <div id=\"app-grid\" class=\"grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4\"></div>
            </main>
        </div>
        <div id=\"modal\" class=\"modal hidden\">
            <div class=\"modal-content\">
                <h3 class=\"text-xl font-semibold mb-2\">App Details</h3>
                <div id=\"modal-text\"></div>
                <button onclick=\"closeModal()\" class=\"mt-4 px-4 py-2 bg-blue-500 text-white rounded\">Close</button>
            </div>
        </div>
        <script>
          const apps = {{ json_cards|safe }};
          const grid = document.getElementById('app-grid');
          const search = document.getElementById('search');
          const links = document.querySelectorAll('#category-list a');
          const modal = document.getElementById('modal');
          const modalText = document.getElementById('modal-text');
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
                <h3 class='text-lg font-bold mb-1'><a href='${app.link}' target='_blank' rel='noopener'>${app.name}</a></h3>
                <p class='text-sm text-gray-400 dark:text-gray-500 mb-2 italic'>${app.category}</p>
                <p class='text-sm mb-2'>${app.desc}</p>
                ${app.stars ? `<p class='text-xs mb-1 text-yellow-500'>⭐ GitHub Stars: ${app.stars}</p>` : ''}
                ${app.alt ? `<p class='text-xs text-gray-500 dark:text-gray-400 mb-2'>🧭 Alternative to: ${app.alt}</p>` : ''}
                <div class='flex gap-2 mt-auto'>
                  ${app.link ? `<a href="${app.link}" class="text-sm bg-blue-500 text-white px-3 py-1 rounded hover:bg-blue-600" target="_blank">🌐 Visit Website</a>` : ''}
                  ${app.repo_link ? `<a href="${app.repo_link}" class="text-sm bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700" target="_blank">🧩 NS8 Module</a>` : ''}
                  <button onclick="openModal('🔗 <a href='${app.link}' target='_blank'>${app.name}</a><br/><br/>📄 ${app.desc}')" class="text-sm bg-gray-200 dark:bg-gray-700 px-3 py-1 rounded">📄 Details</button>
                </div>`;
              grid.appendChild(el);
            }
          }

          function openModal(text) {
            modalText.innerHTML = text;
            modal.classList.remove('hidden');
          }
          function closeModal() {
            modal.classList.add('hidden');
          }

          links.forEach(link => link.addEventListener('click', e => { e.preventDefault(); currentFilter = e.target.dataset.filter; render(); }));
          search.addEventListener('input', render);
          render();
          function toggleTheme() { document.body.classList.toggle('dark'); }
        </script>
    </body>
    </html>
    """)

    return html_template.render(timestamp=timestamp, categories=categories, json_cards=json_cards)

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
