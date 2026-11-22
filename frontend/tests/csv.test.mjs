import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import ts from "typescript";

const source = await readFile(new URL("../src/csv.ts", import.meta.url), "utf8");
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 },
});
const csv = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`);

test("CSV cells neutralize spreadsheet formulas and preserve CSV quoting", () => {
  for (const value of ["=1+1", "+SUM(A1:A2)", "-1", "@cmd", "\t=1"]) {
    assert.equal(csv.csvCell(value), `'${value}`);
  }
  assert.equal(csv.csvCell("\r=1"), "\"'\r=1\"");
  assert.equal(csv.csvCell('text,"value"'), '"text,""value"""');
  assert.equal(csv.csvCell("plain text"), "plain text");
});
