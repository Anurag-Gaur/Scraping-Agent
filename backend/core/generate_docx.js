const fs   = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, LevelFormat, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, PageBreak
} = require("docx");

// ── Read args ──────────────────────────────────────────────────────
const specPath = process.argv[2];
const outPath  = process.argv[3];
if (!specPath || !outPath) {
  console.error("Usage: node generate_docx.js <build_spec.json> <output.docx>");
  process.exit(1);
}

const data = JSON.parse(fs.readFileSync(specPath, "utf8"));
const bs   = data.build_spec   || {};
const cs   = data.competitor_summary || {};
const req  = data.requirement  || "Unknown requirement";

// ── Style helpers ──────────────────────────────────────────────────
const BLUE    = "1F4E79";
const LBLUE   = "2E75B6";
const TBLUE   = "D6E4F0";
const GRAY    = "595959";
const LGRAY   = "F2F2F2";
const border  = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 320, after: 160 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: LBLUE, space: 4 } },
    children: [new TextRun({ text, bold: true, size: 36, color: BLUE, font: "Arial" })]
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 240, after: 100 },
    children: [new TextRun({ text, bold: true, size: 28, color: LBLUE, font: "Arial" })]
  });
}

function body(text, opts = {}) {
  return new Paragraph({
    spacing: { before: 60, after: 60 },
    children: [new TextRun({ text: text || "—", size: 22, font: "Arial", color: "222222", ...opts })]
  });
}

function labelValue(label, value) {
  return new Paragraph({
    spacing: { before: 80, after: 60 },
    children: [
      new TextRun({ text: label + ": ", bold: true, size: 22, font: "Arial", color: BLUE }),
      new TextRun({ text: value || "—", size: 22, font: "Arial", color: "222222" })
    ]
  });
}

function bullet(text) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { before: 40, after: 40 },
    children: [new TextRun({ text: text || "", size: 22, font: "Arial", color: "222222" })]
  });
}

function numbered(text) {
  return new Paragraph({
    numbering: { reference: "numbers", level: 0 },
    spacing: { before: 40, after: 40 },
    children: [new TextRun({ text: text || "", size: 22, font: "Arial", color: "222222" })]
  });
}

function spacer() {
  return new Paragraph({ spacing: { before: 80, after: 80 }, children: [new TextRun("")] });
}

function headerCell(text, width) {
  return new TableCell({
    borders, width: { size: width, type: WidthType.DXA },
    shading: { fill: TBLUE, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({
      children: [new TextRun({ text, bold: true, size: 20, font: "Arial", color: BLUE })]
    })]
  });
}

function dataCell(text, width, shade) {
  return new TableCell({
    borders, width: { size: width, type: WidthType.DXA },
    shading: { fill: shade || "FFFFFF", type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({
      children: [new TextRun({ text: text || "—", size: 20, font: "Arial", color: "222222" })]
    })]
  });
}

// ── Cover / title block ────────────────────────────────────────────
const titleBlock = [
  new Paragraph({
    spacing: { before: 0, after: 120 },
    children: [new TextRun({ text: "AI Agent Build Specification", bold: true, size: 56, font: "Arial", color: BLUE })]
  }),
  new Paragraph({
    spacing: { before: 0, after: 80 },
    children: [new TextRun({ text: req.toUpperCase(), bold: true, size: 32, font: "Arial", color: LBLUE })]
  }),
  new Paragraph({
    spacing: { before: 0, after: 40 },
    children: [new TextRun({
      text: "Generated: " + new Date().toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" }),
      size: 20, font: "Arial", color: GRAY
    })]
  }),
  new Paragraph({
    border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: LBLUE, space: 1 } },
    spacing: { before: 0, after: 360 },
    children: [new TextRun("")]
  }),
];

// ── Summary table (agent at a glance) ─────────────────────────────
const summaryRows = [
  ["Agent name",         bs.agent_name          || "—"],
  ["Target user",        bs.target_user         || "—"],
  ["Build complexity",   bs.build_complexity    || "—"],
  ["Estimated days",     String(bs.estimated_build_days || "—")],
  ["LLM",                bs.suggested_tech_stack?.llm          || "—"],
  ["Orchestration",      bs.suggested_tech_stack?.orchestration || "—"],
  ["Database",           bs.suggested_tech_stack?.database      || "—"],
].map(([label, value], i) => new TableRow({
  children: [
    headerCell(label, 2800),
    dataCell(value, 6560, i % 2 === 0 ? "FFFFFF" : LGRAY),
  ]
}));

const summaryTable = new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [2800, 6560],
  rows: summaryRows,
});

// ── Capabilities table ─────────────────────────────────────────────
const capRows = [
  new TableRow({ children: [headerCell("Capability", 2800), headerCell("Description", 6560)] }),
  ...(bs.core_capabilities || []).map((c, i) => new TableRow({
    children: [
      dataCell(c.capability || "", 2800, i % 2 === 0 ? LGRAY : "FFFFFF"),
      dataCell(c.description || "", 6560, i % 2 === 0 ? LGRAY : "FFFFFF"),
    ]
  }))
];

const capTable = new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [2800, 6560],
  rows: capRows,
});

// ── Integrations table ─────────────────────────────────────────────
const intRows = [
  new TableRow({ children: [headerCell("System", 3000), headerCell("Purpose", 6360)] }),
  ...(bs.integrations || []).map((item, i) => new TableRow({
    children: [
      dataCell(item.system || "", 3000, i % 2 === 0 ? LGRAY : "FFFFFF"),
      dataCell(item.purpose || "", 6360, i % 2 === 0 ? LGRAY : "FFFFFF"),
    ]
  }))
];

const intTable = new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [3000, 6360],
  rows: intRows,
});

// ── Competitor summary table ───────────────────────────────────────
const compEntries = Object.entries(cs).filter(([, v]) => v && v !== "—");
const compRows = [
  new TableRow({ children: [headerCell("Platform", 2400), headerCell("What they offer", 6960)] }),
  ...compEntries.map(([platform, summary], i) => new TableRow({
    children: [
      dataCell(platform.charAt(0).toUpperCase() + platform.slice(1), 2400, i % 2 === 0 ? LGRAY : "FFFFFF"),
      dataCell(summary, 6960, i % 2 === 0 ? LGRAY : "FFFFFF"),
    ]
  }))
];

const compTable = new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [2400, 6960],
  rows: compRows,
});

// ── Workflow steps ─────────────────────────────────────────────────
const workflowParas = (bs.workflow_steps || []).map(s =>
  new Paragraph({
    numbering: { reference: "numbers", level: 0 },
    spacing: { before: 60, after: 40 },
    children: [
      new TextRun({ text: (s.action || "") + " — ", bold: true, size: 22, font: "Arial", color: BLUE }),
      new TextRun({ text: s.detail || "", size: 22, font: "Arial", color: "222222" })
    ]
  })
);

// ── Build the document ─────────────────────────────────────────────
const doc = new Document({
  numbering: {
    config: [
      { reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: "Arial", color: BLUE },
        paragraph: { spacing: { before: 320, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial", color: LBLUE },
        paragraph: { spacing: { before: 240, after: 100 }, outlineLevel: 1 } },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    children: [
      // ── Cover ──
      ...titleBlock,

      // ── At a glance ──
      h1("At a glance"),
      summaryTable,
      spacer(),

      // ── Purpose ──
      h1("Purpose"),
      body(bs.purpose),
      spacer(),

      // ── Core capabilities ──
      h1("Core capabilities"),
      capTable,
      spacer(),

      // ── Workflow ──
      h1("Workflow steps"),
      ...( workflowParas.length ? workflowParas : [body("No workflow steps defined.")] ),
      spacer(),

      // ── Data ──
      h1("Data"),
      h2("Inputs"),
      ...(bs.data_inputs || []).map(d => bullet(d)),
      spacer(),
      h2("Outputs"),
      ...(bs.data_outputs || []).map(d => bullet(d)),
      spacer(),

      // ── Integrations ──
      h1("Integrations"),
      intTable,
      spacer(),

      // ── Tech stack ──
      h1("Suggested tech stack"),
      labelValue("LLM",            bs.suggested_tech_stack?.llm),
      labelValue("Orchestration",  bs.suggested_tech_stack?.orchestration),
      labelValue("Database",       bs.suggested_tech_stack?.database),
      body("Additional integrations:"),
      ...(bs.suggested_tech_stack?.integrations || []).map(i => bullet(i)),
      spacer(),

      // ── Differentiation ──
      h1("Competitive differentiation"),
      h2("What competitors have"),
      body(bs.what_competitors_have),
      spacer(),
      h2("Our differentiation"),
      body(bs.our_differentiation),
      spacer(),

      // ── Competitor summary ──
      h1("Competitor analysis"),
      ...(compEntries.length ? [compTable] : [body("No competitor data available.")]),
      spacer(),
    ]
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(outPath, buf);
  console.log("OK:" + outPath);
}).catch(e => { console.error("ERR:" + e.message); process.exit(1); });
