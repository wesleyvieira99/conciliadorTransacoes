#!/usr/bin/env python3
"""Gera Markdown expandido, HTML independente e PDF a partir do manuscrito.
Requer Python 3.10+, reportlab e o executável pandoc no PATH.
"""
from pathlib import Path
from html import escape
import hashlib
import json
import re
import subprocess
import textwrap
import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
    Spacer, PageBreak, CondPageBreak, Preformatted, Table, TableStyle, KeepTogether, Flowable)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
SOURCE = ROOT / 'src/main/java/br/com/wesley/conciliacao'
FILES = {p.name: p for p in SOURCE.glob('*.java')}
FILES['pom.xml'] = ROOT / 'pom.xml'
PATTERN = r'\{\{SOURCE:([^}]+)\}\}'
NAVY = colors.HexColor('#102A43')
TEAL = colors.HexColor('#087F8C')
INK = colors.HexColor('#243B53')
MUTED = colors.HexColor('#526D82')
PAPER = colors.HexColor('#F2F6F8')
LIME = colors.HexColor('#D9F28C')
WIDTH, HEIGHT = A4
MARGIN = 48
CONTENT = WIDTH - MARGIN * 2

fonts = Path(reportlab.__file__).parent / 'fonts'
for name, filename in [('Book', 'Vera.ttf'), ('Book-Bold', 'VeraBd.ttf'), ('Book-Italic', 'VeraIt.ttf'), ('Book-BoldItalic', 'VeraBI.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(fonts / filename)))
pdfmetrics.registerFontFamily('Book', normal='Book', bold='Book-Bold', italic='Book-Italic', boldItalic='Book-BoldItalic')
STYLES = {
    'body': ParagraphStyle('body', fontName='Book', fontSize=10.1, leading=16.6, textColor=INK, spaceAfter=8, splitLongWords=True,allowWidows=0,allowOrphans=0),
    'h1': ParagraphStyle('h1', fontName='Book-Bold', fontSize=21, leading=27, textColor=NAVY, spaceBefore=8, spaceAfter=17, keepWithNext=True),
    'h2': ParagraphStyle('h2', fontName='Book-Bold', fontSize=13.5, leading=19, textColor=TEAL, spaceBefore=17, spaceAfter=10, keepWithNext=True),
    'h3': ParagraphStyle('h3', fontName='Book-Bold', fontSize=10.4, leading=15.5, textColor=NAVY, spaceBefore=11, spaceAfter=7, keepWithNext=True),
    'small': ParagraphStyle('small', fontName='Book', fontSize=8, leading=12, textColor=MUTED, spaceAfter=8),
    'cell': ParagraphStyle('cell', fontName='Book', fontSize=9.1, leading=14, textColor=INK, spaceAfter=3),
    'cellcode': ParagraphStyle('cellcode', fontName='Courier', fontSize=8.4, leading=12.2, textColor=TEAL, spaceAfter=4, splitLongWords=True),
    'code': ParagraphStyle('code', fontName='Courier', fontSize=8.2, leading=11, textColor=INK, backColor=PAPER, borderColor=colors.HexColor('#D7E2EA'), borderWidth=0.5, borderPadding=10, spaceBefore=8, spaceAfter=14),
    'quote': ParagraphStyle('quote', fontName='Book-Italic', fontSize=10.1, leading=16.6, textColor=TEAL, leftIndent=15, rightIndent=12, borderColor=TEAL, borderWidth=0.5, borderPadding=9, spaceBefore=7, spaceAfter=12),
}

def pandoc(text, output):
    return subprocess.run(['pandoc', '--from=gfm', '--to='+output, '--no-highlight'], input=text, text=True, encoding='utf-8', capture_output=True, check=True).stdout

def xml(text):
    return escape(str(text), quote=False).replace('\u2011','-').replace('\u2013','-').replace('\u2014','-').replace('\u00a0',' ')

def inlines(items):
    out=[]
    for item in items:
        kind=item['t']; c=item.get('c')
        if kind=='Str': out.append(xml(c))
        elif kind in ('Space','SoftBreak'): out.append(' ')
        elif kind=='LineBreak': out.append('<br/>')
        elif kind=='Strong': out.append('<b>'+inlines(c)+'</b>')
        elif kind=='Emph': out.append('<i>'+inlines(c)+'</i>')
        elif kind=='Code': out.append('<font name="Courier" size="8.8">'+xml(c[1])+'</font>')
        elif kind=='Link':
            label=inlines(c[1]); target=c[2][0]
            if target.startswith(('https://','http://')):
                out.append('<a color="#087F8C" href="'+escape(target,quote=True)+'">'+label+'</a>')
            else: out.append(label)
        elif kind in ('Span','Quoted'): out.append(inlines(c[1]))
        elif kind=='RawInline' and c[1] in ('<br>','<br/>'): out.append('<br/>')
    return ''.join(out)

def plain_blocks(blocks):
    parts=[]
    for block in blocks:
        if block['t'] in ('Para','Plain'): parts.append(inlines(block['c']))
        elif block['t']=='CodeBlock': parts.append(xml(block['c'][1]))
    return '<br/>'.join(parts)

def code_flows(text):
    # A long physical line wraps visually; its original source number remains visible.
    lines=[]
    for line in text.expandtabs(4).splitlines():
        lines.extend(textwrap.wrap(line, width=91, subsequent_indent='      ', replace_whitespace=False, drop_whitespace=False) or [''])
    out=[]
    for offset in range(0,len(lines),34):
        out.append(Preformatted('\n'.join(lines[offset:offset+34]),STYLES['code']))
    return out

annotations={}

def source_flows(filename):
    lines=FILES[filename].read_text(encoding='utf-8').splitlines()
    out=[Paragraph('Código completo: '+xml(filename),STYLES['h2']),
         Paragraph('Os números à esquerda são referências de leitura; não fazem parte do arquivo Java ou XML.',STYLES['small'])]
    out += code_flows('\n'.join(f'{i:>3}  {line}' for i,line in enumerate(lines,1)))
    out.append(CondPageBreak(150))
    out.append(Paragraph('Cada linha, uma intenção',ParagraphStyle('tableheading',parent=STYLES['h2'],keepWithNext=False)))
    rows=[[Paragraph('<b>Linha</b>',STYLES['cell']),Paragraph('<b>Instrução e explicação</b>',STYLES['cell'])]]
    for i,line in enumerate(lines,1):
        if not line.strip(): continue
        detail=[Paragraph(xml(line.strip()),STYLES['cellcode']),Paragraph(xml(annotations[filename][str(i)]),STYLES['cell'])]
        rows.append([Paragraph(str(i),STYLES['cell']),detail])
    table=Table(rows,colWidths=[46,CONTENT-46],repeatRows=1,hAlign='LEFT')
    table.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DDECEF')),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F5F8FA')]),
        ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
        ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
        ('LINEBELOW',(0,0),(-1,0),0.7,TEAL)
    ]))
    out.extend([table,Spacer(1,12)])
    return out

class Cover(Flowable):
    def __init__(self): super().__init__(); self.width=CONTENT; self.height=HEIGHT-112
    def draw(self):
        c=self.canv
        c.saveState(); x,y=c.absolutePosition(0,0); c.translate(-x,-y)
        c.setFillColor(NAVY); c.rect(0,0,WIDTH,HEIGHT,fill=1,stroke=0)
        c.setFillColor(TEAL); c.rect(0,HEIGHT-12,WIDTH,12,fill=1,stroke=0)
        c.setFillColor(LIME); c.setFont('Book-Bold',9); c.drawString(48,HEIGHT-77,'CADERNO DE ENGENHARIA  /  03')
        c.setFillColor(colors.white); c.setFont('Book-Bold',32)
        c.drawString(48,HEIGHT-151,'Conciliação')
        c.drawString(48,HEIGHT-192,'de pagamentos')
        c.setFillColor(LIME); c.setFont('Book',19); c.drawString(48,HEIGHT-234,'Do enunciado ao código.')
        c.setFillColor(colors.HexColor('#C1D5E3')); c.setFont('Book',11)
        for j,line in enumerate(['Uma solução pequena, explicada por dentro.', 'Java 17, estruturas de dados, testes e raciocínio.', 'Para construir, entender e conseguir explicar.']):c.drawString(48,HEIGHT-282-j*21,line)
        y=HEIGHT-443
        c.setFillColor(colors.HexColor('#193B54')); c.roundRect(48,y-144,CONTENT,170,12,fill=1,stroke=0)
        c.setFillColor(LIME);c.setFont('Book-Bold',9);c.drawString(66,y+4,'UM LOTE. QUATRO RESPOSTAS.')
        rows=[('pag-2','CONCILIADO'),('pag-1','VALOR_DIVERGENTE'),('pag-3','NAO_LIQUIDADO'),('pag-4','NAO_PREVISTO')]
        for j,(reference,status) in enumerate(rows):
            yy=y-26-j*28
            c.setFillColor(colors.HexColor('#C1D5E3'));c.setFont('Courier',10);c.drawString(67,yy,reference)
            c.setFillColor(colors.white);c.setFont('Book-Bold',9);c.drawString(165,yy,status)
        c.setFillColor(colors.HexColor('#7EA7BD'));c.setFont('Book',8)
        c.drawString(48,95,'EDIÇÃO 29.10.2026   |   WESLEY VIEIRA')
        c.drawString(48,77,'Exercício educacional fictício. Não é uma questão oficial do Nubank.')
        c.restoreState()

class BookDoc(BaseDocTemplate):
    def __init__(self,path):
        super().__init__(str(path),pagesize=A4,leftMargin=MARGIN,rightMargin=MARGIN,topMargin=54,bottomMargin=53,
            title='Conciliação de pagamentos: do enunciado ao código',author='Wesley Vieira',subject='Java 17 e conciliação de um lote, passo a passo')
        frame=Frame(MARGIN,53,CONTENT,HEIGHT-107,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
        self.addPageTemplates(PageTemplate(id='book',frames=frame,onPage=self.page_header))
    def page_header(self,c,doc):
        if doc.page==1:return
        c.saveState();c.setStrokeColor(colors.HexColor('#D9E5EC'));c.setLineWidth(.5);c.line(MARGIN,HEIGHT-36,WIDTH-MARGIN,HEIGHT-36)
        c.setFont('Book-Bold',7);c.setFillColor(MUTED);c.drawString(MARGIN,HEIGHT-27,'CONCILIAÇÃO DE PAGAMENTOS  /  JAVA 17')
        c.setFont('Book',7);c.drawString(MARGIN,27,'Desafio 03 · Do enunciado ao código');c.drawRightString(WIDTH-MARGIN,27,f'{doc.page:02d}');c.restoreState()
    def afterFlowable(self,flowable):
        if hasattr(flowable,'bookmark'):
            text=flowable.getPlainText(); key=flowable.bookmark
            self.canv.bookmarkPage(key);self.canv.addOutlineEntry(text,key,0,False)
            self.notify('TOCEntry',(0,text,self.page,key))

def render_blocks(blocks, nested=False):
    out=[]
    for b in blocks:
        kind=b['t']; c=b.get('c')
        if kind in ('Para','Plain'): out.append(Paragraph(inlines(c),STYLES['body']))
        elif kind=='Header':
            level,attr,items=c
            if level==1:continue
            style='h1' if level==2 else 'h2' if level==3 else 'h3'
            if level==2 and not nested:out.extend([CondPageBreak(250),Spacer(1,14)])
            p=Paragraph(inlines(items),STYLES[style])
            if level==2:p.bookmark=attr[0]
            out.append(p)
        elif kind=='CodeBlock':
            if 'source-ref' in c[0][1]:out+=source_flows(c[1].strip())
            else:out+=code_flows(c[1])
        elif kind in ('BulletList','OrderedList'):
            items=c if kind=='BulletList' else c[1]
            start=1 if kind=='BulletList' else c[0][0]
            for i,item in enumerate(items,start):
                bullet='•' if kind=='BulletList' else f'{i}.'
                content=render_blocks(item,True)
                table=Table([[Paragraph(bullet,STYLES['body']),content]],colWidths=[18,CONTENT-18])
                table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),2)]))
                out.append(table)
        elif kind=='BlockQuote':out.append(Paragraph(plain_blocks(c),STYLES['quote']))
        elif kind=='HorizontalRule':out.append(Spacer(1,10))
        elif kind=='Table':
            head=c[3][1];body=[]
            for group in c[4]:body += group[2]+group[3]
            allrows=head+body+c[5][1]
            rows=[]
            for row in allrows:
                rows.append([Paragraph(plain_blocks(cell[4]),STYLES['cell']) for cell in row[1]])
            if rows:
                t=Table(rows,colWidths=[CONTENT/len(rows[0])]*len(rows[0]),repeatRows=len(head),hAlign='LEFT')
                t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,len(head)-1),colors.HexColor('#DDECEF')),('ROWBACKGROUNDS',(0,len(head)),(-1,-1),[colors.white,PAPER]),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
                out.extend([t,Spacer(1,12)])
    return out

HTML_CSS='''
:root{--navy:#102a43;--ink:#243b53;--teal:#087f8c;--muted:#526d82;--paper:#f6f8fa;--line:#d9e5ec;color-scheme:light}*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:32px}body{margin:0;background:var(--paper);color:var(--ink);font:17px/1.8 system-ui,-apple-system,"Segoe UI",sans-serif}a{color:var(--teal);text-underline-offset:4px}nav{position:fixed;inset:0 auto 0 0;width:280px;overflow:auto;background:var(--navy);color:white;padding:32px 23px}nav strong{font-size:21px;display:block;line-height:1.3}nav small{color:#a7c7d8}nav a{display:block;color:#c9dbe5;text-decoration:none;line-height:1.5;padding:9px 0;font-size:13px}nav a:hover,nav a:focus{color:#d9f28c}nav ol{list-style:none;padding-left:0;margin-top:25px}nav li::marker{color:#6e9fb8;font-size:11px}main{margin-left:280px;max-width:1180px;padding:0 64px 90px}.cover{margin:0 -64px 55px;padding:70px 64px;background:var(--navy);color:white;border-top:7px solid var(--teal)}.cover small{letter-spacing:2px;color:#d9f28c}.cover h1{font-size:clamp(36px,5vw,57px);letter-spacing:-2px;line-height:1.08;margin:25px 0}.cover p{color:#c1d5e3;max-width:650px;font-size:18px}.pill{display:inline-block;border:1px solid #436277;border-radius:30px;padding:4px 14px;margin:10px 8px 0 0;font-size:12px}.cover a{color:#d9f28c}article>h1{display:none}h1,h2,h3,h4{overflow-wrap:anywhere}h2{border-top:1px solid var(--line);padding-top:36px;margin-top:65px;font-size:29px;line-height:1.25;color:var(--navy);letter-spacing:-.7px}h3{font-size:23px;color:var(--teal);margin-top:34px}h4{font-size:19px;color:var(--navy)}article{overflow-wrap:anywhere}p,li{max-width:78ch}pre{overflow:auto;line-height:1.55;font-size:13px;padding:23px;border:1px solid var(--line);border-radius:12px;background:#eaf0f4}code{font-family:"SFMono-Regular",Consolas,monospace;font-size:.86em;background:#eaf0f4;padding:2px 4px;border-radius:3px}pre code{padding:0;background:none}table{border-collapse:collapse;width:100%;font-size:14px;margin:24px 0;background:white}thead{background:#ddecef;text-align:left}td,th{padding:12px;border-bottom:1px solid var(--line);vertical-align:top}td:first-child{min-width:45px}td code{white-space:normal;overflow-wrap:anywhere;line-height:1.5}td{overflow-wrap:anywhere}tr:nth-child(even){background:#f4f8fa}blockquote{border-left:3px solid var(--teal);background:#e6f2f2;margin:25px 0;padding:8px 24px}#progress{position:fixed;top:0;left:280px;height:4px;background:var(--teal);z-index:2;width:0}.toolbar{display:flex;gap:12px;flex-wrap:wrap;margin-top:20px}.toolbar button,.toolbar a{background:transparent;color:#d9f28c;border:1px solid #527285;padding:8px 14px;border-radius:6px;font:inherit;font-size:13px;cursor:pointer;text-decoration:none}:focus-visible{outline:3px solid #c39733;outline-offset:4px}.skip{position:absolute;left:300px;top:-80px;background:white;z-index:4;padding:12px}.skip:focus{top:10px}body.large article{font-size:20px}@media(max-width:1000px){nav{position:static;width:auto;max-height:290px}nav ol{columns:2}main{margin-left:0;padding:0 25px 70px}.cover{margin:0 -25px 30px;padding:45px 25px}#progress{left:0}.skip{left:10px}body{font-size:16px}table{font-size:13px}td,th{padding:8px}}@media(max-width:560px){nav ol{columns:1}.cover h1{letter-spacing:-1px}table{display:block;overflow-x:auto}td{min-width:110px}td:first-child{min-width:46px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}@media print{nav,.toolbar,#progress{display:none}main{margin:0;max-width:none;padding:0}.cover{margin:0;padding:25px;background:white;color:#102a43}.cover p,.cover small{color:#243b53}pre{white-space:pre-wrap;overflow-wrap:anywhere}h2{break-before:page}tr{break-inside:avoid}a{color:inherit}}
'''

def main():
    global annotations
    manuscript=DOCS/'manuscrito.md'
    if not manuscript.exists():raise SystemExit('Crie docs/manuscrito.md antes de gerar.')
    text=manuscript.read_text(encoding='utf-8')
    annotations=json.loads((DOCS/'linhas.json').read_text(encoding='utf-8'))
    expected=json.loads((DOCS/'fontes-codigo.json').read_text(encoding='utf-8'))
    for name,path in FILES.items():
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if expected[name]!=digest:raise SystemExit(f'{name} mudou: revise anotações e o registro fontes-codigo.json.')
        keys={str(i) for i,line in enumerate(path.read_text(encoding='utf-8').splitlines(),1) if line.strip()}
        if set(annotations.get(name,{}))!=keys:raise SystemExit(f'Anotações incompletas ou divergentes: {name}')
    markers=re.findall(PATTERN,text)
    if set(markers)!=set(FILES) or len(markers)!=len(FILES):raise SystemExit('Cada arquivo deve ter exatamente um marcador SOURCE.')
    def expand(match):
        name=match.group(1);lines=FILES[name].read_text(encoding='utf-8').splitlines();lang='java' if name.endswith('.java') else 'xml'
        block='\n\n### Código completo: '+name+'\n\n```'+lang+'\n'+'\n'.join(lines)+'\n```\n\n### Cada linha, uma intenção\n\n| Linha | Instrução e explicação |\n| --- | --- |\n'
        for i,line in enumerate(lines,1):
            if line.strip():
                code=escape(line.strip()).replace('|','&#124;')
                explanation=escape(annotations[name][str(i)]).replace('|','&#124;')
                block+=f'| {i} | <code>{code}</code><br>{explanation} |\n'
        return block+'\n'
    expanded=re.sub(PATTERN,expand,text).rstrip()+'\n'
    (DOCS/'ebook.md').write_text(expanded, encoding='utf-8')
    body=pandoc(expanded,'html')
    headings=re.findall(r'<h2 id="([^"]+)">(.*?)</h2>',body,re.S)
    toc=''.join('<li><a href="#'+key+'">'+re.sub('<[^>]+>','',title)+'</a></li>' for key,title in headings)
    page='''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Conciliação de pagamentos · Ebook Java 17</title><style>'''+HTML_CSS+'''</style></head><body><a class="skip" href="#leitura">Ir para o conteúdo</a><div id="progress"></div><nav aria-label="Capítulos"><small>CADERNO DE ENGENHARIA / 03</small><strong>Conciliação<br>de pagamentos</strong><ol>'''+toc+'''</ol></nav><main><header class="cover"><small>DO ENUNCIADO AO CÓDIGO</small><h1>Um lote.<br>Quatro respostas.</h1><p>Entenda como pensar, construir e testar um conciliador de pagamentos em Java. Cada decisão tem um motivo; cada linha tem uma explicação.</p><span class="pill">Java 17</span><span class="pill">JUnit 5</span><span class="pill">29.10.2026</span><div class="toolbar"><button id="type" aria-pressed="false">Aumentar texto</button><button id="print">Imprimir leitura</button><a href="https://github.com/wesleyvieira99/conciliadorTransacoes">Código no GitHub ↗</a></div></header><article id="leitura" tabindex="-1">'''+body+'''</article></main><script>const t=document.querySelector('#type');t.onclick=()=>{const large=document.body.classList.toggle('large');t.setAttribute('aria-pressed',String(large));t.textContent=large?'Tamanho padrão':'Aumentar texto'};document.querySelector('#print').onclick=()=>window.print();function progress(){const room=document.documentElement.scrollHeight-innerHeight;document.querySelector('#progress').style.width=(room>0?Math.min(100,scrollY/room*100):0)+'%'};addEventListener('scroll',progress,{passive:true});addEventListener('resize',progress);progress();</script></body></html>'''
    (DOCS/'ebook.html').write_text(page, encoding='utf-8')
    pdf_text=re.sub(PATTERN,lambda m:'\n```source-ref\n'+m.group(1)+'\n```\n',text)
    ast=json.loads(pandoc(pdf_text,'json'))
    toc_pdf=TableOfContents();toc_pdf.levelStyles=[ParagraphStyle('toc',fontName='Book',fontSize=9.5,leading=15,textColor=INK,spaceBefore=5,rightIndent=25)]
    story=[Cover(),PageBreak(),Paragraph('Seu mapa de leitura',STYLES['h1']),Paragraph('Leia em sequência para construir a solução. Depois, volte aos capítulos pelo sumário ou pelos marcadores do PDF. As páginas de código e as explicações foram geradas a partir dos arquivos reais deste repositório.',STYLES['body']),Spacer(1,14),toc_pdf]
    story.append(PageBreak())
    story+=render_blocks(ast['blocks'])
    # A chapter always begins on its own page, avoiding a doubled break after the TOC.
    BookDoc(DOCS/'ebook.pdf').multiBuild(story)
    print(json.dumps({'files':len(FILES),'lines_explained':sum(len(v) for v in annotations.values()),'chapters':len(headings),'pdf':str(DOCS/'ebook.pdf')},ensure_ascii=False))

if __name__=='__main__':main()
