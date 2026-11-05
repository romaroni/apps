import base64
import calendar
import hmac
import html
import json
import os
import threading
import time
import urllib.request
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from zoneinfo import ZoneInfo


def esc(value):
    return html.escape(str(value), quote=True)


def rich(items):
    output = []
    for item in items:
        value = esc(item.get('plain_text', item.get('text', {}).get('content', '')))
        annotations = item.get('annotations', {})
        for key, tag in [('bold', 'strong'), ('italic', 'em'), ('strikethrough', 's'), ('underline', 'u'), ('code', 'code')]:
            if annotations.get(key):
                value = '<%s>%s</%s>' % (tag, value, tag)
        # External links intentionally remain text on this fixed display.
        output.append(value)
    return ''.join(output)


class Notion:
    def __init__(self, token, page):
        self.token, self.page = token, page

    def get(self, path):
        request = urllib.request.Request('https://api.notion.com/v1/' + path, headers={
            'Authorization': 'Bearer ' + self.token, 'Notion-Version': '2022-06-28'})
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.load(response)

    def blocks(self, block_id, depth=0):
        if depth > 30:
            raise ValueError('Page nesting limit exceeded')
        result, cursor = [], None
        while True:
            path = 'blocks/%s/children?page_size=100' % block_id
            if cursor:
                path += '&start_cursor=' + urllib.parse.quote(cursor)
            batch = self.get(path)
            for block in batch['results']:
                if block.get('has_children'):
                    block['children'] = self.blocks(block['id'], depth + 1)
                result.append(block)
            if not batch.get('has_more'):
                return result
            cursor = batch['next_cursor']

    def render(self):
        page = self.get('pages/' + self.page)
        title = next((rich(p['title']) for p in page.get('properties', {}).values() if p['type'] == 'title'), 'Status')
        return '<h1>%s</h1>%s' % (title, render_blocks(self.blocks(self.page)))


def render_blocks(blocks):
    result, listing = [], None
    for block in blocks:
        kind = block['type']
        data = block.get(kind, {})
        target = {'bulleted_list_item': 'ul', 'numbered_list_item': 'ol'}.get(kind)
        if target != listing:
            if listing:
                result.append('</%s>' % listing)
            if target:
                result.append('<%s>' % target)
            listing = target
        value = rich(data.get('rich_text', []))
        children = render_blocks(block.get('children', []))
        if target:
            result.append('<li>%s%s</li>' % (value, children))
        elif kind.startswith('heading_'):
            level = int(kind[-1]) + 1
            result.append('<h%d>%s</h%d>%s' % (level, value, level, children))
        elif kind == 'to_do':
            result.append('<div class="todo">%s %s%s</div>' % ('&#9745;' if data.get('checked') else '&#9744;', value, children))
        elif kind == 'divider':
            result.append('<hr>')
        elif kind == 'table':
            result.append('<div class="table-wrap"><table>%s</table></div>' % children)
        elif kind == 'table_row':
            result.append('<tr>%s</tr>' % ''.join('<td>%s</td>' % rich(cell) for cell in data['cells']))
        elif kind in ('paragraph', 'quote', 'callout', 'toggle', 'code'):
            tag = {'quote': 'blockquote', 'code': 'pre'}.get(kind, 'div')
            result.append('<%s class="block">%s%s</%s>' % (tag, value, children, tag))
        elif kind in ('column_list', 'column', 'synced_block'):
            result.append(children)
        else:
            result.append('<p class="notice">[Notion block: %s]%s</p>%s' % (esc(kind), value, children))
    if listing:
        result.append('</%s>' % listing)
    return ''.join(result)


STYLE = '''body{margin:0;background:#111820;color:#f2f0e9;font-family:Arial,Helvetica,sans-serif;font-size:26px;line-height:1.45}main{max-width:1100px;margin:auto;padding:30px}a{color:#b8dce5}nav{font-size:18px;margin-bottom:22px}h1{font-size:42px}h2{font-size:34px}h3{font-size:30px}.block,.todo{white-space:pre-wrap;margin:12px 0}li{margin:8px 0}td,th{padding:8px;border:1px solid #46515d}table{border-collapse:collapse;width:100%}.table-wrap{overflow:auto}pre{white-space:pre-wrap}blockquote{border-left:4px solid #b8dce5;padding-left:20px}.notice,footer{color:#b9c1ca;font-size:18px}.clock{text-align:center}.time{font-size:140px;line-height:1.1;font-variant-numeric:tabular-nums;margin:30px 0 12px}.date{font-size:30px}.calendar{max-width:650px;margin:30px auto}.calendar caption{font-size:28px;margin-bottom:12px}.calendar td,.calendar th{text-align:center;width:14.28%;padding:8px 0}.today{background:#b8dce5;color:#111820;font-weight:bold}@media(max-width:600px){main{padding:18px}.time{font-size:84px}.date{font-size:24px}body{font-size:23px}}'''


def document(title, body, refresh, other, label):
    clock_fit = '@media(max-height:800px){.clock .time{font-size:110px;margin:12px 0 8px}.clock .calendar{margin:16px auto 0}.clock .calendar td,.clock .calendar th{padding:5px 0}.clock .calendar caption{margin-bottom:8px}}'
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="refresh" content="%d"><title>%s</title><style>%s</style>'
            '</head><body><main><nav><a href="%s">%s</a></nav>%s</main></body></html>'
            % (refresh, esc(title), STYLE + clock_fit, other, label, body))


def clock_body(now=None):
    now = (now or datetime.now(ZoneInfo('America/New_York'))).astimezone(ZoneInfo('America/New_York'))
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    month = months[now.month - 1]
    rows = []
    for week in calendar.Calendar(firstweekday=6).monthdayscalendar(now.year, now.month):
        rows.append('<tr>' + ''.join('<td%s>%s</td>' % (' class="today" aria-current="date"' if day == now.day else '', day or '') for day in week) + '</tr>')
    return ('<div class="clock"><div class="time">%s</div><div class="date">%s, %d %s %d</div>'
            '<div class="notice">New York</div><table class="calendar"><caption>%s %d</caption>'
            '<thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' %
            (now.strftime('%I:%M %p').lstrip('0'), weekdays[now.weekday()], now.day, month, now.year,
             month, now.year, ''.join('<th scope="col">%s</th>' % d for d in ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']), ''.join(rows)))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # Do not log request headers or URLs.

    def do_GET(self):
        expected = 'Basic ' + base64.b64encode((self.server.username + ':' + self.server.password).encode()).decode()
        if not hmac.compare_digest(self.headers.get('Authorization', ''), expected):
            self.reply(401, 'Authentication required', {'WWW-Authenticate': 'Basic realm="Juliana display", charset="UTF-8"'})
            return
        path = self.path.split('?', 1)[0]
        if path in ('/', '/clock'):
            self.reply(200, document('New York clock', clock_body(), 60, '/status', 'Status'))
        elif path == '/status':
            with self.server.cache_lock:
                try:
                    if time.monotonic() - self.server.fetched > self.server.refresh:
                        self.server.cached = self.server.notion.render()
                        self.server.fetched = time.monotonic()
                    content = self.server.cached
                    status = 200
                except Exception:
                    # Never show stale client information as if it were current.
                    content = '<h1>Status unavailable</h1><p>Notion could not be read. This page will retry automatically.</p>'
                    status = 503
            self.reply(status, document('Status', content, self.server.refresh, '/clock', 'Clock'))
        else:
            self.reply(404, 'Not found')

    def reply(self, status, body, extra=None):
        data = body.encode('utf-8')
        self.send_response(status)
        for key, value in {'Content-Type': 'text/html; charset=utf-8', 'Content-Length': str(len(data)),
                           'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer',
                           'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY',
                           'Content-Security-Policy': "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'", **(extra or {})}.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)


def create_server(address=None):
    required = ['DISPLAY_USER', 'DISPLAY_PASSWORD', 'NOTION_TOKEN', 'NOTION_PAGE_ID']
    if any(not os.environ.get(key) for key in required):
        raise ValueError('Set DISPLAY_USER, DISPLAY_PASSWORD, NOTION_TOKEN and NOTION_PAGE_ID')
    if ':' in os.environ['DISPLAY_USER'] or len(os.environ['DISPLAY_PASSWORD']) < 20:
        raise ValueError('Use a username without a colon and a password of at least 20 characters')
    page = os.environ['NOTION_PAGE_ID'].replace('-', '')
    if len(page) != 32 or any(c not in '0123456789abcdefABCDEF' for c in page):
        raise ValueError('NOTION_PAGE_ID must be the 32-character page ID (hyphens optional)')
    refresh = int(os.environ.get('STATUS_REFRESH_SECONDS', '180'))
    if not 60 <= refresh <= 300:
        raise ValueError('STATUS_REFRESH_SECONDS must be between 60 and 300')
    server = ThreadingHTTPServer(address or ('0.0.0.0', int(os.environ.get('PORT', '8080'))), Handler)
    server.username, server.password = os.environ['DISPLAY_USER'], os.environ['DISPLAY_PASSWORD']
    server.notion = Notion(os.environ['NOTION_TOKEN'], page)
    server.refresh, server.fetched, server.cached = refresh, float('-inf'), ''
    server.cache_lock = threading.Lock()
    return server


if __name__ == '__main__':
    create_server().serve_forever()
