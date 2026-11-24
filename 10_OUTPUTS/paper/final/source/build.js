const fs = require("fs");
const sz = require("path");
const { Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, BorderStyle,
  AlignmentType, HeadingLevel, Footer, PageNumber, FootnoteReferenceRun, TabStopType, PageBreak, VerticalAlign } = require("docx");
const C = require("./content.js");
const APP = require("./appendix.js");
const { imageSize } = (() => { try { return require("image-size"); } catch (e) { return {}; } })();

const FONT = "Times New Roman";
const BODY = 24;            // 12 pt
const TEXTW = 9026;         // A4 minus 1" margins
const DOUBLE = { line: 480, before: 0, after: 0 };

// ---------- inline markup -> runs
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|_\{[^}]+\}|\^\{[^}]+\}|\[\[fn:\d+\]\])/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), font: FONT, ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, font: FONT, ...base }));
    else if (t.startsWith("*")) out.push(new TextRun({ text: t.slice(1, -1), italics: true, font: FONT, ...base }));
    else if (t.startsWith("_{")) out.push(new TextRun({ text: t.slice(2, -1), subScript: true, font: FONT, ...base }));
    else if (t.startsWith("^{")) out.push(new TextRun({ text: t.slice(2, -1), superScript: true, font: FONT, ...base }));
    else out.push(new FootnoteReferenceRun(parseInt(t.match(/\d+/)[0], 10)));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), font: FONT, ...base }));
  return out;
}

const P = (t) => new Paragraph({ children: runs(t, { size: BODY }), alignment: AlignmentType.JUSTIFIED,
  spacing: { line: 480, before: 0, after: 200 } });

const H = (t, lvl) => {
  const map = { h1: HeadingLevel.HEADING_1, h1u: HeadingLevel.HEADING_1, h2: HeadingLevel.HEADING_2, h3: HeadingLevel.HEADING_3 };
  return new Paragraph({ heading: map[lvl], keepNext: true, keepLines: true,
    children: [new TextRun({ text: t, font: FONT, size: BODY, bold: true, italics: lvl === "h2" })],
    spacing: { before: lvl === "h1" || lvl === "h1u" ? 360 : 240, after: 160, line: 360 } });
};

function colWidths(header, rows) {
  const n = header.length;
  const w = new Array(n).fill(0);
  rows.forEach(r => r.forEach((c, i) => { w[i] = Math.max(w[i], Math.min(String(c).replace(/\*/g, "").length, i === 0 ? 46 : 30)); }));
  header.forEach((c, i) => { const longest = Math.max(...String(c).split(/\s+/).map(x => x.length)); w[i] = Math.max(w[i], Math.min(Math.ceil(String(c).length / 2), 30), longest); });
  const ww = w.map(x => Math.max(x, 9));
  const s = ww.reduce((a, b) => a + b, 0);
  const cols = ww.map(x => Math.floor(TEXTW * x / s));
  cols[n - 1] += TEXTW - cols.reduce((a, b) => a + b, 0);
  return cols;
}

const NONE = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const LINE = (sz) => ({ style: BorderStyle.SINGLE, size: sz, color: "000000" });

function table(title, header, rows, note) {
  const cols = colWidths(header, rows);
  const keep = rows.length <= 25;
  const mkCell = (text, i, isHead, isLast) => new TableCell({
    width: { size: cols[i], type: WidthType.DXA },
    margins: { top: 40, bottom: 40, left: 80, right: 80 },
    verticalAlign: VerticalAlign.CENTER,
    borders: { left: NONE, right: NONE, top: isHead ? LINE(8) : NONE, bottom: isHead ? LINE(4) : (isLast ? LINE(8) : NONE) },
    children: [new Paragraph({ keepNext: keep && !isLast, keepLines: true, alignment: (i === 0 || String(text).length > 45) ? AlignmentType.LEFT : AlignmentType.CENTER, spacing: { line: 240, before: 0, after: 0 },
      children: runs(String(text), { size: 19, bold: isHead || undefined }) })],
  });
  const trs = [new TableRow({ tableHeader: true, cantSplit: true, children: header.map((h, i) => mkCell(h, i, true, false)) })];
  rows.forEach((r, ri) => trs.push(new TableRow({ cantSplit: true, children: r.map((c, i) => mkCell(c, i, false, ri === rows.length - 1)) })));
  const out = [
    new Paragraph({ keepNext: true, spacing: { before: 240, after: 100, line: 276 },
      children: [new TextRun({ text: title, bold: true, font: FONT, size: 21 })] }),
    new Table({ width: { size: TEXTW, type: WidthType.DXA }, columnWidths: cols, rows: trs,
      borders: { top: NONE, bottom: NONE, left: NONE, right: NONE, insideHorizontal: NONE, insideVertical: NONE } }),
  ];
  if (note) out.push(new Paragraph({ spacing: { before: 80, after: 280, line: 240 }, alignment: AlignmentType.JUSTIFIED,
    children: [new TextRun({ text: "Note: ", italics: true, font: FONT, size: 18 }), ...runs(note, { size: 18 })] }));
  else out.push(new Paragraph({ spacing: { before: 0, after: 200 }, children: [] }));
  return out;
}

function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}

function figure(file, caption, note, inches) {
  const { w, h } = pngSize(file);
  const W = Math.round(inches * 96), Hh = Math.round(W * h / w);
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 240, after: 80 },
      children: [new ImageRun({ type: "png", data: fs.readFileSync(file), transformation: { width: W, height: Hh } })] }),
    new Paragraph({ keepNext: true, spacing: { before: 0, after: 40, line: 240 },
      children: [new TextRun({ text: caption, bold: true, font: FONT, size: 20 })] }),
    new Paragraph({ spacing: { before: 0, after: 280, line: 240 }, alignment: AlignmentType.JUSTIFIED,
      children: runs(note, { size: 18 }) }),
  ];
}

function equation(text, num) {
  return new Paragraph({ spacing: { before: 120, after: 240, line: 360 },
    tabStops: [{ type: TabStopType.CENTER, position: Math.round(TEXTW / 2) }, { type: TabStopType.RIGHT, position: TEXTW }],
    children: [new TextRun({ text: "\t", font: FONT }), ...runs(text, { size: BODY, italics: false }),
      new TextRun({ text: "\t" + (num || ""), font: FONT, size: BODY })] });
}

function render(items) {
  const out = [];
  for (const it of items) {
    const [k] = it;
    if (k === "p") out.push(P(it[1]));
    else if (k.startsWith("h")) {
      if (k === "h1" && /^Appendix/.test(it[1])) out.push(new Paragraph({ children: [new PageBreak()] }));
      out.push(H(it[1], k));
    }
    else if (k === "table") out.push(...table(it[1], it[2], it[3], it[4]));
    else if (k === "fig") out.push(...figure(sz.join(__dirname, it[1]), it[2], it[3], it[4]));
    else if (k === "eq") out.push(equation(it[1], it[2]));
  }
  return out;
}

// ---------- title page
const titlePage = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 240, line: 300 },
    children: [new TextRun({ text: C.title, bold: true, font: FONT, size: 30 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 360 },
    children: [new TextRun({ text: C.author, font: FONT, size: BODY }), new FootnoteReferenceRun(1)] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 },
    children: [new TextRun({ text: "Abstract", bold: true, font: FONT, size: BODY })] }),
  new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { line: 276, after: 240 }, children: runs(C.abstract, { size: 22 }) }),
  new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { line: 276, after: 120 },
    children: [new TextRun({ text: "Keywords: ", bold: true, font: FONT, size: 22 }), new TextRun({ text: C.keywords, font: FONT, size: 22 })] }),
  new Paragraph({ spacing: { line: 276, after: 120 },
    children: [new TextRun({ text: "JEL Code: ", bold: true, font: FONT, size: 22 }), new TextRun({ text: C.jel, font: FONT, size: 22 })] }),
  new Paragraph({ children: [new PageBreak()] }),
];

const refs = [new Paragraph({ children: [new PageBreak()] }), H("References", "h1u"),
  ...C.refs.map(r => new Paragraph({ alignment: AlignmentType.JUSTIFIED, indent: { left: 720, hanging: 720 },
    spacing: { line: 276, after: 160 }, children: runs(r, { size: 22 }) }))];

const footnotes = { 1: { children: [new Paragraph({ children: [new TextRun({ text: C.affil, font: FONT, size: 18 })] })] } };
for (const [k, v] of Object.entries(C.footnotes)) footnotes[k] = { children: [new Paragraph({ alignment: AlignmentType.JUSTIFIED, children: runs(v, { size: 18 }) })] };

const doc = new Document({
  creator: C.author, title: C.title,
  styles: {
    default: { document: { run: { font: FONT, size: BODY } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: BODY, bold: true, color: "000000" }, paragraph: { spacing: { before: 360, after: 160 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: BODY, bold: true, italics: true, color: "000000" }, paragraph: { spacing: { before: 240, after: 160 }, keepNext: true, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: BODY, bold: true, color: "000000" }, paragraph: { spacing: { before: 240, after: 160 }, keepNext: true, outlineLevel: 2 } },
    ],
  },
  footnotes,
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 20 })] })] }) },
    children: [...titlePage, ...render(C.body), ...refs, ...render(APP)],
  }],
});

Packer.toBuffer(doc).then(b => { fs.writeFileSync(process.argv[2] || "paper.docx", b); console.log("written"); });
