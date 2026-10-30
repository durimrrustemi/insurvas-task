from app.discovery.extract import extract_text, extract_title
from app.discovery.fetch import find_inner_urls


def test_extract_text_from_html():
    html = """
    <html><body>
    <nav>Skip this</nav>
    <main><p>Hello world from the main content.</p></main>
    <footer>Skip this too</footer>
    </body></html>
    """
    text = extract_text(html)
    assert "Hello world" in text


def test_extract_text_empty():
    assert extract_text("") == ""
    assert extract_text(None) == ""


def test_extract_title():
    html = "<html><head><title>BPO Corp</title></head><body></body></html>"
    assert extract_title(html) == "BPO Corp"


def test_extract_title_missing():
    html = "<html><head></head><body></body></html>"
    assert extract_title(html) == ""


def test_find_inner_urls():
    html = """
    <html><body>
    <a href="/about">About Us</a>
    <a href="/services">Our Services</a>
    <a href="/careers">Careers</a>
    <a href="/blog">Blog</a>
    <a href="https://other.com/about">External About</a>
    </body></html>
    """
    urls = find_inner_urls(html, "https://example.com", max_pages=3)
    assert len(urls) <= 3
    assert "https://example.com/about" in urls
    assert "https://example.com/services" in urls
    assert "https://example.com/careers" in urls
    # External link should be excluded
    assert "https://other.com/about" not in urls


def test_find_inner_urls_no_matches():
    html = '<html><body><a href="/blog">Blog</a></body></html>'
    urls = find_inner_urls(html, "https://example.com", max_pages=3)
    assert len(urls) == 0
