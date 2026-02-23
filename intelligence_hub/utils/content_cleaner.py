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

    soup = BeautifulSoup(html_content, "html.parser")

    # 1. STRIP BOILERPLATE & NOISE
    # Remove boilerplate elements
    boilerplate_selectors = [
        "header",
        "footer",
        "nav",
        "aside",
        ".nav",
        ".footer",
        ".header",
        ".sidebar",
        ".menu",
        ".ads",
        ".advertisement",
        ".social-share",
        ".adx-market-watch",
        ".breadcrumbs-nav",
        ".company-profile-nav",
        ".pagination",
        ".adx-pagination",
        ".newsletter-section",
        "script",
        "style",
        "meta",
        "noscript",
        "iframe",
        "object",
        "embed",
        "applet",
        "svg",
        "button",
        "input",
        "form",
        "select",
        "option",
    ]
    for selector in boilerplate_selectors:
        for element in soup.select(selector):
            element.decompose()

    # Remove elements by class/id heuristics (common boilerplate)
    # Be careful not to remove content.
    # Safe to remove: cookie-banner, popup, advertisement, social-share
    # Updated: changed 'share' to 'share-'/ 'share_' to avoid matching 'shareholders'
    for element in soup.find_all(
        attrs={
            "class": re.compile(
                r"cookie|popup|ad-|advert|banner|social|share-|share_|sidebar|widget|menu|navigation",
                re.I,
            )
        }
    ):
        element.decompose()

    # 2. FLATTEN TABLES (Handle colspan/rowspan)
    # We process tables *before* markdownify to ensure correct grid structure
    for table in soup.find_all("table"):
        _flatten_table(table, soup)

    # 3. UNSTRUCTURED DATA HANDLING (Heuristic)
    # Convert <dl> (Definition Lists) to Tables (e.g. Corporate Actions)
    for dl in soup.find_all("dl"):
        _process_dl_to_table(dl, soup)

    # DFM SPECIFIC: Flex Tables and Grid Structures
    _process_dfm_flex_table(soup)
    _process_dfm_grid_to_table(soup)

    # ADX SPECIFIC: Orderbook Grid
    _process_adx_orderbook_grid(soup)

    # Convert <pre> blocks with CSV/Tab data to tables
    for pre in soup.find_all(["pre", "code"]):
        text = pre.get_text()
        if _is_likely_table_data(text):
            new_table = _text_to_html_table(text, soup)
            pre.replace_with(new_table)

    # 4. REMOVE FONT STYLES (Clean Prose)
    # We want to strip formatting tags but keep structural ones.
    # After our custom processors have converted flex/grid to <table>,
    # we can safely strip <div> and <span> to get clean text inside table cells.
    # Note: markdownify can sometimes jumble text if div/span are stripped without spaces.
    # We'll add a space before and after block-like tags to prevent merging.
    for tag in soup.find_all(["div", "span", "p"]):
        if tag.get_text(strip=True):
            tag.insert_before(soup.new_string(" "))
            tag.insert_after(soup.new_string(" "))

    strip_tags = [
        "b",
        "strong",
        "i",
        "em",
        "u",
        "s",
        "strike",
        "font",
        "sup",
        "sub",
        "big",
        "small",
        "mark",
        "ins",
        "del",
        "img",
        "div",
        "span",
    ]

    # 5. CONVERT TO MARKDOWN
    # heading_style="ATX" -> # Header
    markdown_text = md(str(soup), heading_style="ATX", strip=strip_tags)

    # 6. POST-PROCESSING
    # Remove excessive newlines
    markdown_text = re.sub(r"\n{3,}", "\n\n", markdown_text).strip()

    return markdown_text


def _flatten_table(table, soup):
    """
    Modifies the table in-place to remove rowspan/colspan by duplicating cells.
    """
    rows = table.find_all("tr")
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
    occupied = {}  # (r, c) -> True

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
    virtual_grid = []  # list of lists of (tag_name, text)

    # We need to know how many rows first?
    row_c = len(rows)
    # We don't know cols yet.

    # Initialize grid with None
    # We'll expand rows as needed.

    for r_idx, row in enumerate(rows):
        # Ensure row exists in grid
        while len(virtual_grid) <= r_idx:
            virtual_grid.append([])

        cells = row.find_all(["td", "th"])
        c_idx = 0

        for cell in cells:
            # Skip occupied cells (from rowspans above)
            while _is_occupied(virtual_grid, r_idx, c_idx):
                c_idx += 1

            # Get clean content
            text = cell.get_text(" ", strip=True)
            tag = cell.name

            rowspan = int(cell.get("rowspan", 1))
            colspan = int(cell.get("colspan", 1))

            # Fill the main cell
            _set_cell(virtual_grid, r_idx, c_idx, tag, text)

            # Handle Spans
            # Fill right (colspan)
            for c_offset in range(1, colspan):
                _set_cell(
                    virtual_grid, r_idx, c_idx + c_offset, tag, text
                )  # Repeat content or Empty? User said "flatten into repeating cells"

            # Fill down (rowspan)
            for r_offset in range(1, rowspan):
                # Ensure rows exist
                while len(virtual_grid) <= r_idx + r_offset:
                    virtual_grid.append([])

                _set_cell(
                    virtual_grid, r_idx + r_offset, c_idx, tag, text
                )  # Repeat content for merged vertical

                # And if it has colspan too?
                for c_offset in range(1, colspan):
                    _set_cell(
                        virtual_grid, r_idx + r_offset, c_idx + c_offset, tag, text
                    )

            c_idx += colspan

    # Rebuild Table HTML
    new_tbody = soup.new_tag("tbody")

    # Header logic: If original had <thead>, we might want to preserve it, but flattening mixes it up.
    # Markdown tables need a header row. If the first row is TH, good.

    for r_data in virtual_grid:
        tr = soup.new_tag("tr")
        for tag, text in r_data:
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
    lines = text.strip().split("\n")
    if len(lines) < 2:
        return False

    commas = [line.count(",") for line in lines if line.strip()]
    tabs = [line.count("\t") for line in lines if line.strip()]

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
    lines = text.strip().split("\n")
    delimiter = "," if lines[0].count(",") > lines[0].count("\t") else "\t"

    table = soup.new_tag("table")
    tbody = soup.new_tag("tbody")
    table.append(tbody)

    # Assume first line is header? Or just data?
    # Markdown tables require header. Let's assume first line is header.

    for i, line in enumerate(lines):
        if not line.strip():
            continue
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


def _process_dfm_flex_table(soup):
    """
    Detects and converts DFM flex-tables (table-flex, t-row, t-col/t-cell) to HTML tables.
    """
    # 1. Handle .table-flex with .t-row and .t-cell (Simple list-like tables)
    for flex_table in soup.find_all(class_="table-flex"):
        # If it has .t-row and .t-cell structure
        rows = flex_table.find_all(class_="t-row")
        if not rows:
            continue

        html_table = soup.new_tag("table")
        tbody = soup.new_tag("tbody")
        html_table.append(tbody)

        for row in rows:
            tr = soup.new_tag("tr")
            # Headers might be specified via class or just first row
            cells = row.find_all(class_="t-cell")
            if not cells:
                continue

            for cell in cells:
                td = soup.new_tag("td")
                td.string = cell.get_text(separator=" ", strip=True)
                tr.append(td)
            tbody.append(tr)

        flex_table.replace_with(html_table)

    # 2. Handle .table-flex-vertical with .t-row and .t-col (Grid-like key-value tables)
    for flex_table in soup.find_all(class_="table-flex-vertical"):
        rows = flex_table.find_all(class_="t-row")
        if not rows:
            continue

        html_table = soup.new_tag("table")
        tbody = soup.new_tag("tbody")
        html_table.append(tbody)

        for row in rows:
            cols = row.find_all(class_="t-col")
            if not cols:
                # Sometimes t-row has t-cell directly
                cols = row.find_all(class_="t-cell")
                if not cols:
                    continue

            for col in cols:
                # Find label
                label_el = col.find(class_=re.compile(r"t-head|text-muted|text-xs"))
                label = label_el.get_text(strip=True) if label_el else "Info"

                # Clone col and remove label to get value
                from copy import copy

                col_copy = BeautifulSoup(str(col), "html.parser").find()
                l_copy = col_copy.find(class_=re.compile(r"t-head|text-muted|text-xs"))
                if l_copy:
                    l_copy.decompose()

                value = col_copy.get_text(separator=" ", strip=True)

                if label and value:
                    tr = soup.new_tag("tr")
                    th = soup.new_tag("th")
                    th.string = label
                    td = soup.new_tag("td")
                    td.string = value
                    tr.append(th)
                    tr.append(td)
                    tbody.append(tr)

        flex_table.replace_with(html_table)


def _process_dfm_grid_to_table(soup):
    """
    Detects and converts DFM grid-based key-value pairs into HTML tables.
    Matches classes like grid-cols-1, md:grid-cols-2, etc.
    """
    for grid in soup.find_all(class_=re.compile(r"grid-cols-\d+")):
        # Skip if already inside a table we created
        if grid.find_parent("table"):
            continue

        items = grid.find_all(recursive=False)
        if not items:
            continue

        processed_pairs = []
        for item in items:
            # Look for spans/divs with specific DFM classes or structural patterns
            # Pattern 1: Labels with text-xs, text-muted, font-medium
            label_el = item.find(
                class_=re.compile(r"text-xs|text-muted|font-medium|uppercase")
            )
            if label_el:
                label = label_el.get_text(strip=True)
                # Value is the rest of the text
                from copy import copy

                item_copy = BeautifulSoup(str(item), "html.parser").find()
                l_copy = item_copy.find(
                    class_=re.compile(r"text-xs|text-muted|font-medium|uppercase")
                )
                if l_copy:
                    l_copy.decompose()
                value = item_copy.get_text(separator=" ", strip=True)

                if label and value:
                    processed_pairs.append((label, value))
            else:
                # Pattern 2: Two children, first is label
                children = item.find_all(recursive=False)
                if len(children) >= 2:
                    label = children[0].get_text(strip=True)
                    value = children[1].get_text(separator=" ", strip=True)
                    if label and value:
                        processed_pairs.append((label, value))

        if len(processed_pairs) > 1:
            html_table = soup.new_tag("table")
            tbody = soup.new_tag("tbody")
            html_table.append(tbody)

            for label, value in processed_pairs:
                tr = soup.new_tag("tr")
                th = soup.new_tag("th")
                th.string = label
                td = soup.new_tag("td")
                td.string = value
                tr.append(th)
                tr.append(td)
                tbody.append(tr)

            grid.replace_with(html_table)


def _process_adx_orderbook_grid(soup):
    """
    Detects and converts ADX orderbook grid structures to HTML tables.
    Focuses on col-6 BID/ASK PRICE containers and data rows.
    """
    # 1. Look for BID PRICE / ASK PRICE headers
    # These are usually in row -> col-6 -> report-title
    rows = soup.find_all(class_="row")
    for row in rows:
        titles = row.find_all(class_="report-title")
        if any("BID PRICE" in t.get_text().upper() for t in titles) and any(
            "ASK PRICE" in t.get_text().upper() for t in titles
        ):

            # Found the orderbook section.
            # We need to find the data rows sibling to this or within the same container.
            # ADX orderbooks often have a specific parent for the data.
            container = row.find_parent(class_="component-table-style") or row.parent

            # Find all data cells. They might be in a list or another grid.
            # Typical structure: a series of divs with bid and ask values.
            # Including 'price-info_count' which was identified in manual inspection.
            data_cells = container.find_all(
                class_=re.compile(r"price-info|record|price-info_count", re.I)
            )
            if not data_cells:
                continue

            html_table = soup.new_tag("table")
            thead = soup.new_tag("thead")
            tbody = soup.new_tag("tbody")
            html_table.append(thead)
            html_table.append(tbody)

            # Header
            h_row = soup.new_tag("tr")
            for h in ["Bid Price", "Ask Price"]:
                th = soup.new_tag("th")
                th.string = h
                h_row.append(th)
            thead.append(h_row)

            # This is a bit tricky as BID/ASK are often side-by-side in HTML or alternating.
            # Let's group them or just list them.
            # Heuristic: Find all numeric strings in this container and pair them.
            values = []
            for cell in data_cells:
                # Some cells might contain labels, we want pure numbers
                txt = cell.get_text(strip=True).replace(",", "")
                if re.match(r"^\d+\.?\d*$", txt):
                    values.append(txt)

            # Pair them (assuming Bid-Ask, Bid-Ask...)
            for i in range(0, len(values) - 1, 2):
                tr = soup.new_tag("tr")
                td1 = soup.new_tag("td")
                td1.string = values[i]
                td2 = soup.new_tag("td")
                td2.string = values[i + 1]
                tr.append(td1)
                tr.append(td2)
                tbody.append(tr)

            if len(tbody.find_all("tr")) > 0:
                row.replace_with(html_table)
                # Decompose the original container if it's still there
                # container.decompose() # Risky, let's just replace the header row for now.
