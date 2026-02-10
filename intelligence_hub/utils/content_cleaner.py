
import re
from bs4 import BeautifulSoup, NavigableString
from markdownify import markdownify as md

def clean_html_to_markdown(html_content: str) -> str:
    """
    Cleans HTML content by removing noise (scripts, styles, nav) and converts it to strict Markdown.
    
    Rules:
    - Strip boilerplate (nav, footer, header, scripts, styles).
    - Flatten tables (handle rowspan/colspan).
    - Convert unstructured CSV/tab data to tables (heuristic).
    - Remove font styles (bold, italic, colors).
    - Use headers (#) and lists (-).
    """
    if not html_content:
        return ""
        
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 1. STRIP BOILERPLATE & NOISE
    # Remove standard non-content tags
    for element in soup(["script", "style", "nav", "footer", "header", "aside", "meta", "noscript", "iframe", "object", "embed", "applet", "svg", "button", "input", "form", "select", "option"]):
        element.decompose()
        
    # Remove elements by class/id heuristics (common boilerplate)
    # Be careful not to remove content.
    # Safe to remove: cookie-banner, popup, advertisement, social-share
    for element in soup.find_all(attrs={"class": re.compile(r"cookie|popup|ad-|advert|banner|social|share|sidebar|widget|menu|navigation", re.I)}):
        element.decompose()
        
    # 2. FLATTEN TABLES (Handle colspan/rowspan)
    # We process tables *before* markdownify to ensure correct grid structure
    for table in soup.find_all("table"):
        _flatten_table(table, soup)
        
    # 3. UNSTRUCTURED DATA HANDLING (Heuristic)
    # Convert <dl> (Definition Lists) to Tables (e.g. Corporate Actions)
    for dl in soup.find_all("dl"):
        _process_dl_to_table(dl, soup)

    # Convert <pre> blocks with CSV/Tab data to tables
    for pre in soup.find_all(["pre", "code"]):
        text = pre.get_text()
        if _is_likely_table_data(text):
            new_table = _text_to_html_table(text, soup)
            pre.replace_with(new_table)

    # 4. REMOVE FONT STYLES (Clean Prose)
    # We want to strip formatting tags but keep structural ones (h1-h6, p, ul, ol, li, table, tr, td, th, blockquote, pre, code)
    # Tags to strip (keep content): b, strong, i, em, u, s, strike, font, span, div, a (maybe keep links? User said "Output text as clean, unformatted prose", usually implies links are ok as text, but "Remove all font styles" might mean just styles. Links are structural in web. Let's keep links but strip styling tags.)
    # Strip tags list for markdownify:
    strip_tags = ['b', 'strong', 'i', 'em', 'u', 's', 'strike', 'font', 'span', 'div', 'sup', 'sub', 'big', 'small', 'mark', 'ins', 'del', 'img'] 
    
    # 5. CONVERT TO MARKDOWN
    # heading_style="ATX" -> # Header
    markdown_text = md(str(soup), heading_style="ATX", strip=strip_tags)
    
    # 6. POST-PROCESSING
    # Remove excessive newlines
    markdown_text = re.sub(r'\n{3,}', '\n\n', markdown_text).strip()
    
    return markdown_text

def _flatten_table(table, soup):
    """
    Modifies the table in-place to remove rowspan/colspan by duplicating cells.
    """
    rows = table.find_all('tr')
    if not rows:
        return

    # Calculate grid dimensions
    # This is complex because of rowspans. 
    # Simplified approach: Render to list of lists, then rebuild table.
    
    # 1. Build grid
    grid = []
    
    # Pre-calculate simple max width/height is hard. Dynamic expansion.
    # We iterate rows and track occupied cells.
    
    # Map (row_idx, col_idx) -> cell_soup
    occupied = {} # (r, c) -> True
    
    max_col = 0
    row_idx = 0
    
    new_rows = []
    
    # First pass: Determine grid structure and content
    # We need to parse strictly.
    
    # Better approach for "Flattening":
    # Just ensure every cell is <td> or <th> and has no span attributes.
    # If colspan=2, replace with <td>content</td><td>content</td> (or empty).
    # If rowspan=2, insert cell in next row.
    
    # Validating full table logic in BS4 is heavyweight. 
    # Let's try a robust "expand spans" strategy.
    
    # We'll use a virtual grid.
    virtual_grid = [] # list of lists of (tag_name, text)
    
    # We need to know how many rows first?
    row_c = len(rows)
    # We don't know cols yet.
    
    # Initialize grid with None
    # We'll expand rows as needed.
    
    for r_idx, row in enumerate(rows):
        # Ensure row exists in grid
        while len(virtual_grid) <= r_idx:
            virtual_grid.append([])
            
        cells = row.find_all(['td', 'th'])
        c_idx = 0
        
        for cell in cells:
            # Skip occupied cells (from rowspans above)
            while _is_occupied(virtual_grid, r_idx, c_idx):
                c_idx += 1
            
            # Get clean content
            text = cell.get_text(" ", strip=True)
            tag = cell.name
            
            rowspan = int(cell.get('rowspan', 1))
            colspan = int(cell.get('colspan', 1))
            
            # Fill the main cell
            _set_cell(virtual_grid, r_idx, c_idx, tag, text)
            
            # Handle Spans
            # Fill right (colspan)
            for c_offset in range(1, colspan):
                _set_cell(virtual_grid, r_idx, c_idx + c_offset, tag, text) # Repeat content or Empty? User said "flatten into repeating cells"
            
            # Fill down (rowspan)
            for r_offset in range(1, rowspan):
                # Ensure rows exist
                while len(virtual_grid) <= r_idx + r_offset:
                    virtual_grid.append([])
                    
                _set_cell(virtual_grid, r_idx + r_offset, c_idx, tag, text) # Repeat content for merged vertical
                
                # And if it has colspan too?
                for c_offset in range(1, colspan):
                     _set_cell(virtual_grid, r_idx + r_offset, c_idx + c_offset, tag, text)
            
            c_idx += colspan

    # Rebuild Table HTML
    new_tbody = soup.new_tag("tbody")
    
    # Header logic: If original had <thead>, we might want to preserve it, but flattening mixes it up.
    # Markdown tables need a header row. If the first row is TH, good.
    
    for r_data in virtual_grid:
        tr = soup.new_tag("tr")
        for (tag, text) in r_data:
            td = soup.new_tag(tag)
            td.string = text
            tr.append(td)
        new_tbody.append(tr)
        
    table.clear()
    table.append(new_tbody)

def _is_occupied(grid, r, c):
    if r < len(grid) and c < len(grid[r]) and grid[r][c] is not None:
        return True
    return False

def _set_cell(grid, r, c, tag, text):
    # Ensure row exists
    while len(grid) <= r:
        grid.append([])
    # Ensure col exists
    while len(grid[r]) <= c:
        grid[r].append(None)
        
    grid[r][c] = (tag, text)

def _is_likely_table_data(text):
    """
    Heuristic: Checks if text has multiple lines with consistent delimiters (comma or tab).
    """
    lines = text.strip().split('\n')
    if len(lines) < 2:
        return False
        
    commas = [line.count(',') for line in lines if line.strip()]
    tabs = [line.count('\t') for line in lines if line.strip()]
    
    # Check consistency
    if len(commas) > 0 and all(c == commas[0] and c > 0 for c in commas):
        return True
    if len(tabs) > 0 and all(t == tabs[0] and t > 0 for t in tabs):
        return True
        
    return False

def _text_to_html_table(text, soup):
    """
    Converts CSV/TSV text to an HTML table soup.
    """
    lines = text.strip().split('\n')
    delimiter = ',' if lines[0].count(',') > lines[0].count('\t') else '\t'
    
    table = soup.new_tag("table")
    tbody = soup.new_tag("tbody")
    table.append(tbody)
    
    # Assume first line is header? Or just data?
    # Markdown tables require header. Let's assume first line is header.
    
    for i, line in enumerate(lines):
        if not line.strip(): continue
        row = soup.new_tag("tr")
        cells = line.split(delimiter)
        tag = "th" if i == 0 else "td"
        
        for cell in cells:
            td = soup.new_tag(tag)
            td.string = cell.strip()
            row.append(td)
        tbody.append(row)
        
    return table

def _process_dl_to_table(dl, soup):
    """
    Converts a <dl> list (often used for responsive tables) into a standard <table>.
    Creates a proper two-column table with headers for better markdown rendering.
    """
    items = dl.find_all(class_="t-row")
    if not items:
        # Fallback: standard DT/DD
        return
        
    table = soup.new_tag("table")
    
    # Add explicit thead for proper markdown table
    thead = soup.new_tag("thead")
    header_row = soup.new_tag("tr")
    
    th1 = soup.new_tag("th")
    th1.string = "Field"
    header_row.append(th1)
    
    th2 = soup.new_tag("th")
    th2.string = "Value"
    header_row.append(th2)
    
    thead.append(header_row)
    table.append(thead)
    
    # Add tbody with data
    tbody = soup.new_tag("tbody")
    table.append(tbody)
    
    for item in items:
        cells = item.find_all(class_="t-cell")
        if len(cells) >= 2:
            tr = soup.new_tag("tr")
            
            # First cell is the field/key
            td1 = soup.new_tag("td")
            td1.string = cells[0].get_text(strip=True)
            tr.append(td1)
            
            # Second cell is the value
            td2 = soup.new_tag("td")
            td2.string = cells[1].get_text(strip=True)
            tr.append(td2)
            
            tbody.append(tr)
            
    dl.replace_with(table)


