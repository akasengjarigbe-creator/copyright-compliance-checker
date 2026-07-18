from bs4 import BeautifulSoup
from app.models.schemas import ParsedHtml

def parse_html(html: str, base_url: str | None = None) -> ParsedHtml:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)
    return ParsedHtml(html=str(soup), text=text, base_url=base_url)
