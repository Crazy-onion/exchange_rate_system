"""
将 用户手册.md 转换为 dist/manual.html（看板使用手册网页版）
在看板页头通过「使用手册」链接打开，与看板一起部署。
"""
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MD_PATH = os.path.join(BASE_DIR, "用户手册.md")
OUT_PATH = os.path.join(BASE_DIR, "dist", "manual.html")


def inline(text):
    """处理行内加粗 **xxx**"""
    return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)


def md_to_html(md):
    lines = md.split('\n')
    html = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if line.startswith('# '):
            html.append('<h1>%s</h1>' % inline(line[2:]))
            i += 1
        elif line.startswith('## '):
            html.append('<h2>%s</h2>' % inline(line[3:]))
            i += 1
        elif line.startswith('### '):
            html.append('<h3>%s</h3>' % inline(line[4:]))
            i += 1
        elif line.startswith('> '):
            quote = []
            while i < n and lines[i].startswith('> '):
                quote.append(inline(lines[i][2:]))
                i += 1
            html.append('<blockquote>%s</blockquote>' % '<br>'.join(quote))
        elif line.startswith('|') and line.strip().endswith('|'):
            header = [c.strip() for c in line.strip().strip('|').split('|')]
            i += 1
            if i < n and '-' in lines[i] and re.match(r'^\s*\|?[\s:|-]+\|?\s*$', lines[i]):
                i += 1
            rows = []
            while i < n and lines[i].startswith('|') and lines[i].strip().endswith('|'):
                rows.append([inline(c.strip()) for c in lines[i].strip().strip('|').split('|')])
                i += 1
            thead = '<tr>' + ''.join('<th>%s</th>' % h for h in header) + '</tr>'
            tbody = ''.join('<tr>' + ''.join('<td>%s</td>' % c for c in r) + '</tr>' for r in rows)
            html.append('<table><thead>%s</thead><tbody>%s</tbody></table>' % (thead, tbody))
        elif re.match(r'^\s*-\s+', line):
            items = []
            while i < n and re.match(r'^\s*-\s+', lines[i]):
                items.append(inline(re.sub(r'^\s*-\s+', '', lines[i])))
                i += 1
            html.append('<ul>' + ''.join('<li>%s</li>' % it for it in items) + '</ul>')
        elif re.match(r'^\s*\d+\.\s+', line):
            items = []
            while i < n and re.match(r'^\s*\d+\.\s+', lines[i]):
                items.append(inline(re.sub(r'^\s*\d+\.\s+', '', lines[i])))
                i += 1
            html.append('<ol>' + ''.join('<li>%s</li>' % it for it in items) + '</ol>')
        elif line.strip() == '':
            i += 1
        else:
            para = [inline(line)]
            i += 1
            while (i < n and lines[i].strip() != ''
                   and not lines[i].startswith(('#', '>', '|', '-'))
                   and not re.match(r'^\s*\d+\.\s+', lines[i])):
                para.append(inline(lines[i]))
                i += 1
            html.append('<p>%s</p>' % '<br>'.join(para))
    return '\n'.join(html)


CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, "Microsoft YaHei", sans-serif; background: #f0f2f5; color: #333; line-height: 1.75; }
.header { background: linear-gradient(135deg, #1a237e 0%, #283593 100%); color: white; padding: 20px 30px; }
.header h1 { font-size: 22px; font-weight: 500; }
.header .subtitle { font-size: 13px; opacity: 0.85; margin-top: 6px; }
.header a { color: #fff; text-decoration: underline; }
.container { max-width: 900px; margin: 0 auto; padding: 24px 20px 60px; }
.section { background: white; border-radius: 12px; padding: 24px 28px; margin-bottom: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
h1 { font-size: 24px; color: #1a237e; border-left: 5px solid #1a237e; padding-left: 14px; margin: 8px 0 18px; }
h2 { font-size: 19px; color: #283593; margin: 22px 0 12px; border-bottom: 2px solid #e3e6f3; padding-bottom: 6px; }
h3 { font-size: 16px; color: #1a237e; margin: 16px 0 8px; }
p { margin: 8px 0; font-size: 14.5px; }
ul, ol { margin: 8px 0 8px 24px; font-size: 14.5px; }
li { margin: 4px 0; }
blockquote { background: #fff8e1; border-left: 4px solid #ffb300; padding: 10px 16px; margin: 10px 0; border-radius: 4px; font-size: 14px; color: #5d4037; }
table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13.5px; }
table th, table td { padding: 8px 12px; border: 1px solid #e0e0e0; text-align: left; }
table th { background: #e8eaf6; color: #1a237e; font-weight: 600; }
table tr:nth-child(even) td { background: #f8f9ff; }
.back-link { display: inline-block; margin-top: 4px; padding: 6px 14px; background: #1a237e; color: #fff; text-decoration: none; border-radius: 6px; font-size: 13px; }
.back-link:hover { background: #283593; }
.footer { text-align: center; padding: 20px; font-size: 12px; color: #999; }
"""


def build_manual():
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(MD_PATH, 'r', encoding='utf-8') as f:
        md = f.read()
    body = md_to_html(md)
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>汇率波动看板 · 使用手册</title>
<style>%s</style>
</head>
<body>
<div class="header">
  <h1>汇率波动看板 · 使用手册</h1>
  <div class="subtitle"><a href="index.html" class="back-link">← 返回看板</a></div>
</div>
<div class="container">
%s
</div>
<div class="footer">汇率底稿自动化系统 | 数据仅供参考，以官方发布为准</div>
</body>
</html>""" % (CSS, body)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        f.write(html)
    print("[手册] 使用手册网页版已生成: %s" % OUT_PATH)


if __name__ == '__main__':
    build_manual()
