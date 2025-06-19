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
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GenForge App Directory</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; line-height: 1.6; color: #24292e; background-color: #f6f8fa; margin: 0; }
            .container { max-width: 1200px; margin: auto; padding: 20px; }
            header { text-align: center; padding: 20px 0 40px 0; }
            header h1 { font-size: 2.5em; color: #0366d6; }
            header p { font-size: 1.1em; color: #586069; }
            .category-section h2 { padding-bottom: 12px; border-bottom: 2px solid #e1e4e8; margin-top: 40px; color: #0366d6; font-size: 1.8em; }
            .app-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }
            .app-card { background-color: #fff; border: 1px solid #d1d5da; border-radius: 6px; padding: 20px; transition: box-shadow 0.2s, transform 0.2s; }
            .app-card:hover { box-shadow: 0 5px 15px rgba(0,0,0,0.1); transform: translateY(-3px); }
            .app-card h3 { margin: 0 0 12px 0; font-size: 1.4em; }
            .app-card h3 a { text-decoration: none; color: #005cc5; font-weight: 600; }
            .app-links { display: flex; flex-wrap: wrap; gap: 10px; margin: 15px 0; }
            .app-links a { display: inline-block; padding: 6px 12px; border-radius: 4px; text-decoration: none; font-size: 0.9em; font-weight: 500; }
            .app-links a.github { background-color: #24292e; color: #fff; }
            .app-links a.nethserver { background-color: #28a745; color: #fff; }
            .alternatives { font-size: 0.95em; color: #586069; }
            footer { text-align: center; margin-top: 50px; padding-top: 20px; border-top: 1px solid #e1e4e8; font-size: 0.9em; color: #6a737d; }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>GenForge App Directory</h1>
                <p>A community-curated list of applications available for NethServer 8</p>
                <p><small>Metadata generated on {{ timestamp }}</small></p>
            </header>

            <main>
                {% for category in categories %}
                <section class="category-section" id="{{ category|lower|replace(' ', '-') }}">
                    <h2>{{ category }}</h2>
                    <div class="app-grid">
                        {% for app in json_cards|from_json if app.category == category %}
                        <div class="app-card">
                            <h3><a href="{{ app.link }}" target="_blank">{{ app.name }}</a></h3>
                            <p>{{ app.desc }}</p>
                            <div class="app-links">
                                {% if app.repo_link %}<a href="{{ app.repo_link }}" class="github" target="_blank">⭐ {{ app.stars }} Stars</a>{% endif %}
                                <a href="https://github.com/geniusdynamics/ns8-{{ app.name|lower|replace(' ', '-') }}" class="nethserver" target="_blank">NS8 Module</a>
                            </div>
                            {% if app.alt %}<div class="alternatives"><strong>Alternatives:</strong> {{ app.alt }}</div>{% endif %}
                        </div>
                        {% endfor %}
                    </div>
                </section>
                {% endfor %}
            </main>

            <footer>
                <p>This page is automatically generated via GitHub Actions from the <a href="https://github.com/geniusdynamics/ns8-genforge/blob/main/README.md">README.md</a> file.</p>
            </footer>
        </div>
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
