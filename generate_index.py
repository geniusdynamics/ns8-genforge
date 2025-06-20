from pathlib import Path
import re
from datetime import datetime, timezone
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
    intro = ""
    app_cards = []
    lines = readme_text.splitlines()
    intro_lines = []
    found_app_list = False

    for line in lines:
        if not found_app_list:
            if "application list" in line.strip().lower():
                found_app_list = True
            else:
                intro_lines.append(line)
        else:
            break

    intro = "\n".join(intro_lines).strip()

    sections = re.split(r'^##\s+', readme_text, flags=re.MULTILINE)
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
    return intro, app_cards


def generate_html(intro_text, cards):
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    categories = sorted(set(card['category'] for card in cards))

    sidebar_links = "".join([f'<li><a href="#{cat.lower().replace(" ", "-")}">{cat}</a></li>' for cat in categories])

    html_template = Template("""
    <!DOCTYPE html>
    <html lang=\"en\">
    <head>
        <meta charset=\"UTF-8\">
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
        <title>GenForge App Directory</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Helvetica, Arial, sans-serif; margin: 0; background: #f6f8fa; }
            .sidebar { position: fixed; top: 0; left: 0; width: 220px; height: 100vh; overflow-y: auto; background: #fff; border-right: 1px solid #ddd; padding: 20px; }
            .sidebar h3 { margin-top: 0; }
            .sidebar ul { list-style: none; padding: 0; }
            .sidebar li { margin-bottom: 10px; }
            .sidebar a { color: #0366d6; text-decoration: none; font-weight: 500; }
            .container { margin-left: 240px; padding: 20px; }
            header h1 { font-size: 2em; color: #0366d6; }
            .category-section h2 { border-bottom: 2px solid #e1e4e8; margin-top: 40px; color: #0366d6; font-size: 1.6em; }
            .app-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
            .app-card { background: #fff; border: 1px solid #ddd; border-radius: 6px; padding: 15px; }
            .app-card h3 { margin: 0; font-size: 1.2em; }
            .app-card h3 a { color: #005cc5; text-decoration: none; }
            .app-links { margin-top: 10px; }
            .app-links a { margin-right: 8px; padding: 4px 8px; font-size: 0.85em; background: #0366d6; color: white; text-decoration: none; border-radius: 4px; }
            .alternatives { font-size: 0.85em; margin-top: 8px; color: #586069; }
            .intro { margin-bottom: 20px; padding: 10px; background: #fffbea; border: 1px solid #f0e6d2; border-radius: 6px; }
            footer { text-align: center; margin-top: 40px; font-size: 0.9em; color: #6a737d; }
        </style>
    </head>
    <body>
        <div class=\"sidebar\">
            <h3>Categories</h3>
            <ul>
                {{ sidebar_links|safe }}
            </ul>
        </div>
        <div class=\"container\">
            <header>
                <h1>GenForge App Directory</h1>
                <p><small>Metadata generated on {{ timestamp }}</small></p>
            </header>
            <div class=\"intro\">{{ intro_text|safe }}</div>
            <main>
                {% for category in categories %}
                <section class=\"category-section\" id=\"{{ category|lower|replace(' ', '-') }}\">
                    <h2>{{ category }}</h2>
                    <div class=\"app-grid\">
                        {% for app in cards if app.category == category %}
                        <div class=\"app-card\">
                            <h3><a href=\"{{ app.link }}\" target=\"_blank\">{{ app.name }}</a></h3>
                            <p>{{ app.desc }}</p>
                            <div class=\"app-links\">
                                {% if app.repo_link %}<a href=\"{{ app.repo_link }}\" target=\"_blank\">⭐ {{ app.stars }}</a>{% endif %}
                                <a href=\"https://github.com/geniusdynamics/ns8-{{ app.name|lower|replace(' ', '-') }}\" target=\"_blank\">NS8</a>
                            </div>
                            {% if app.alt %}<div class=\"alternatives\"><strong>Alt:</strong> {{ app.alt }}</div>{% endif %}
                        </div>
                        {% endfor %}
                    </div>
                </section>
                {% endfor %}
            </main>
            <footer>
                <p>This page is generated via GitHub Actions from the <a href=\"https://github.com/geniusdynamics/ns8-genforge/blob/main/README.md\">README.md</a>.</p>
            </footer>
        </div>
    </body>
    </html>
    """)

    return html_template.render(timestamp=timestamp, intro_text=intro_text, categories=categories, cards=cards, sidebar_links=sidebar_links)


def main():
    readme_path = Path("README.md")
    output_path = Path("index.html")

    if not readme_path.exists():
        print("❌ README.md not found")
        return

    readme_content = readme_path.read_text(encoding="utf-8")
    intro, cards = parse_readme_tables(readme_content)
    html_output = generate_html(intro, cards)
    output_path.write_text(html_output, encoding="utf-8")
    print("✅ index.html generated successfully.")


if __name__ == '__main__':
    main()
