import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import ts from "typescript";

const source = await readFile(new URL("../src/photo-url.ts", import.meta.url), "utf8");
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 },
});
const urls = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`);

test("photo URL templates require HTTPS and encode player IDs", () => {
  assert.equal(urls.securePhotoUrl("https://cdn.example/players/{id}.jpg", 42),
    "https://cdn.example/players/42.jpg");
  assert.equal(urls.securePhotoUrl("https://cdn.example/{id}/{id}.jpg", "1/../x"),
    "https://cdn.example/1%2F..%2Fx/1%2F..%2Fx.jpg");
  assert.equal(urls.securePhotoUrl("http://cdn.example/{id}.jpg", 42), null);
  assert.equal(urls.securePhotoUrl("javascript:alert(1)", 42), null);
  assert.equal(urls.securePhotoUrl(undefined, 42), null);
});
