from pathlib import Path
import re
from datetime import datetime
from string import Template


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
                    app_cards.append({
                        "category": category,
                        "name": app_name,
                        "desc": description,
                        "link": link
                    })
    return app_cards


def generate_html(cards):
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    card_html = ""
    for app in cards:
        card_html += f"""
        <div class='card'>
            <h3>{app['name']}</h3>
            <p><strong>Category:</strong> {app['category']}</p>
            <p>{app['desc']}</p>
            {'<a href="'+app['link']+'" target="_blank">🔗 Visit</a>' if app['link'] else ''}
        </div>
        """

    html_template = Template("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NS8 AppForge</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        <style>
            body { padding: 2rem; font-family: system-ui, sans-serif; background-color: #f8fafc; }
            .card {
                background: white;
                border-radius: 0.5rem;
                padding: 1rem;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin-bottom: 1.5rem;
            }
            .card a {
                color: #2563eb;
                font-weight: 500;
            }
        </style>
    </head>
    <body>
        <h1 class="text-3xl font-bold mb-4">🧩 NS8 AppForge</h1>
        <p class="text-sm text-gray-500 mb-8">Metadata built at $timestamp UTC</p>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            $card_html
        </div>
    </body>
    </html>
    """)

    return html_template.substitute(card_html=card_html, timestamp=timestamp)


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
