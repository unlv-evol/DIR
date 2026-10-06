#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";
import JSZip from "jszip";

const root = path.resolve(process.argv[2] || ".");
const reviewers = ["A", "B"];
const validations = {
  E: ["yes", "no", "uncertain"],
  F: ["yes", "no", "uncertain"],
  G: ["yes", "no", "uncertain"],
  H: ["correct", "partially_correct", "incorrect", "uncertain"],
  I: ["correct", "partially_correct", "incorrect", "uncertain"],
  J: ["correct", "partially_correct", "incorrect", "uncertain"],
  K: ["none", "context", "specificity", "verification", "multiple", "uncertain"],
  L: ["no", "yes", "uncertain"],
  M: ["correct", "needs_correction", "uncertain"],
};

const instructionRows = [
  ["Stage D human validation", "Frozen blank reviewer instrument generated from the canonical CSV."],
  ["Primary evidence", "case_details is the primary Stage D evidence package."],
  ["Conversation boundary", "Only pre-boundary conversation information is admissible for Context, Specificity, and Verification. The first-generation artifacts and response may be inspected only for first-generation, target-prompt, boundary, and tFG validation. Later turns must not influence C/S/V judgments."],
  ["PR restriction", "PR content is not admissible evidence for independent Context, Specificity, or Verification validation. Do not use implementation, changed files, commits, comments, reviews, CI results, merge status, final outcome, or later development information."],
  ["Independent review", "Do not consult or copy the other reviewer's judgments. Leave a field blank until the case is reviewed."],
  ["first_generation_correct", "yes | no | uncertain"],
  ["target_prompt_correct", "yes | no | uncertain"],
  ["boundary_tFG_correct", "yes | no | uncertain"],
  ["context_extraction", "correct | partially_correct | incorrect | uncertain"],
  ["specificity_extraction", "correct | partially_correct | incorrect | uncertain"],
  ["verification_extraction", "correct | partially_correct | incorrect | uncertain"],
  ["missing_information", "none | context | specificity | verification | multiple | uncertain"],
  ["post_boundary_leakage", "no | yes | uncertain"],
  ["overall_extraction", "correct | needs_correction | uncertain"],
  ["correction_notes", "Free text. Describe omitted information and supporting evidence when missing_information is not none."],
  ["reviewer_notes", "Optional free text."],
];

function xmlEscape(value) {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

async function repairHyperlinkCaches(filePath) {
  const zip = await JSZip.loadAsync(await fs.readFile(filePath));
  const sheetPath = "xl/worksheets/sheet1.xml";
  let sheetXml = await zip.file(sheetPath).async("string");
  sheetXml = sheetXml.replace(
    /<x:c r="([CD]\d+)" s="(\d+)" t="e"><x:f>HYPERLINK\("([^"]+)","[^"]+"\)<\/x:f><x:v>[^<]*<\/x:v><\/x:c>/g,
    (_, cell, style, url) => `<x:c r="${cell}" s="${style}" t="str"><x:f>HYPERLINK(&quot;${xmlEscape(url)}&quot;,&quot;${xmlEscape(url)}&quot;)</x:f><x:v>${xmlEscape(url)}</x:v></x:c>`,
  );
  zip.file(sheetPath, sheetXml);
  let workbookXml = await zip.file("xl/workbook.xml").async("string");
  workbookXml = workbookXml.replace("</x:workbook>", '<x:calcPr calcMode="auto" fullCalcOnLoad="1" forceFullCalc="1" /></x:workbook>');
  zip.file("xl/workbook.xml", workbookXml);
  await fs.writeFile(filePath, await zip.generateAsync({ type: "nodebuffer" }));
}

for (const reviewer of reviewers) {
  const directory = path.join(root, "cases", "stage_d", `reviewer_${reviewer}`);
  const csvPath = path.join(directory, "stage_d_review.csv");
  const csvText = await fs.readFile(csvPath, "utf8");
  const workbook = await Workbook.fromCSV(csvText, { sheetName: "Review" });
  workbook.setColorScheme({
    name: "DIR Stage D",
    themeColors: { accent1: "#1F4E78", accent2: "#D9EAF7", dk1: "#1F2937",
      lt1: "#FFFFFF", lt2: "#F3F4F6", hlink: "#0563C1", folHlink: "#954F72" },
  });
  const review = workbook.worksheets.getItem("Review");
  review.showGridLines = false;
  review.freezePanes.freezeRows(1);
  review.freezePanes.freezeColumns(2);
  review.getRange("A1:O34").format.font = { name: "Arial", size: 10, color: "#1F2937" };
  review.getRange("A1:O1").format = {
    fill: "#1F4E78", font: { name: "Arial", size: 10, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center", verticalAlignment: "center", wrapText: true,
    borders: { preset: "inside", style: "thin", color: "#FFFFFF" },
  };
  review.getRange("A2:D34").format.fill = "#F3F6F8";
  review.getRange("E2:O34").format.fill = "#FFF4CC";
  review.getRange("A2:O34").format.verticalAlignment = "top";
  review.getRange("A2:O34").format.borders = { preset: "inside", style: "thin", color: "#D9E2F3" };
  review.getRange("A1:O34").format.rowHeight = 30;
  review.getRange("A:A").format.columnWidth = 22;
  review.getRange("B:B").format.columnWidth = 44;
  review.getRange("C:D").format.columnWidth = 45;
  review.getRange("E:M").format.columnWidth = 20;
  review.getRange("N:O").format.columnWidth = 38;
  review.getRange("B2:D34").format.wrapText = true;
  review.getRange("N2:O34").format.wrapText = true;
  for (const [column, values] of Object.entries(validations)) {
    review.getRange(`${column}2:${column}34`).dataValidation = { rule: { type: "list", values } };
  }
  const rows = csvText.trimEnd().split(/\r?\n/).slice(1);
  const instructions = workbook.worksheets.add("Instructions");
  instructions.showGridLines = false;
  instructions.getRange("A1:B16").values = instructionRows;
  instructions.getRange("A1:B16").format.font = { name: "Arial", size: 10, color: "#1F2937" };
  instructions.getRange("A1:B1").format = {
    fill: "#1F4E78", font: { name: "Arial", size: 14, bold: true, color: "#FFFFFF" },
  };
  instructions.getRange("A2:A16").format = { fill: "#D9EAF7", font: { name: "Arial", size: 10, bold: true, color: "#1F2937" }, verticalAlignment: "top" };
  instructions.getRange("B2:B16").format = { wrapText: true, verticalAlignment: "top" };
  instructions.getRange("A:A").format.columnWidth = 28;
  instructions.getRange("B:B").format.columnWidth = 100;
  instructions.getRange("A1:B16").format.rowHeight = 34;
  instructions.getRange("A1:B16").format.borders = { preset: "inside", style: "thin", color: "#D9E2F3" };
  workbook.recalculate();
  const preview = await workbook.render({ sheetName: "Review", range: "A1:O8", scale: 1 });
  await fs.writeFile(`/tmp/stage_d_reviewer_${reviewer}_preview.png`, new Uint8Array(await preview.arrayBuffer()));
  const instructionsPreview = await workbook.render({ sheetName: "Instructions", range: "A1:B16", scale: 1 });
  await fs.writeFile(`/tmp/stage_d_reviewer_${reviewer}_instructions.png`, new Uint8Array(await instructionsPreview.arrayBuffer()));
  const inspected = await workbook.inspect({ kind: "table", sheetId: "Review", range: "A1:O3", include: "values,formulas", tableMaxRows: 3, tableMaxCols: 15, maxChars: 3000 });
  console.log(`reviewer_${reviewer} ${inspected.ndjson}`);
  // URLs contain no CSV metacharacters in this corpus; extract columns C/D only
  // after the generator's Python validation has confirmed the canonical schema.
  for (let index = 0; index < rows.length; index++) {
    const cells = rows[index].split(",");
    for (const column of ["C", "D"]) {
      const url = cells[column === "C" ? 2 : 3];
      review.getRange(`${column}${index + 2}`).formulas = [[`=HYPERLINK("${url}","${url}")`]];
    }
  }
  const output = await SpreadsheetFile.exportXlsx(workbook);
  const outputPath = path.join(directory, "stage_d_review.xlsx");
  await output.save(outputPath);
  await repairHyperlinkCaches(outputPath);
}
