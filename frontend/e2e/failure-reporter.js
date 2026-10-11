// Writes the details of every failed test to e2e-failures.txt, so one file can be shared when asking for help.
import fs from "node:fs";
import path from "node:path";

const strip = (text = "") => text.replace(/\u001b\[[0-9;]*m/g, "");
const firstLines = (text, count) => strip(text).split("\n").slice(0, count).join("\n");

export default class FailureReporter {
  constructor() {
    this.failures = new Map();
  }

  printsToStdio() {
    return false;
  }

  onTestEnd(test, result) {
    if (result.status === "passed") {
      this.failures.delete(test.id); // passed on a retry
      return;
    }
    if (result.status === "skipped") return;
    this.failures.set(test.id, {
      title: test.titlePath().slice(2).join(" > "),
      status: result.status === "timedOut" ? "TIMED OUT" : result.status,
      seconds: (result.duration / 1000).toFixed(1),
      errors: result.errors.map((e) => `${firstLines(e.message ?? e.stack ?? "", 30)}${e.snippet ? `\n${firstLines(e.snippet, 14)}` : ""}`),
    });
  }

  onEnd() {
    const file = path.resolve(process.cwd(), "e2e-failures.txt");
    if (this.failures.size === 0) {
      fs.rmSync(file, { force: true });
      return;
    }
    const header = [
      `${this.failures.size} browser test(s) failed.`,
      `node ${process.version} on ${process.platform}; ${new Date().toISOString()}`,
      "",
    ];
    const body = [...this.failures.values()].map((f, i) =>
      [`[${i + 1}] ${f.title}`, `    ${f.status} after ${f.seconds}s`, ...f.errors.map((e) => `\n${e}`), "", "-".repeat(80)].join("\n")
    );
    fs.writeFileSync(file, [...header, ...body].join("\n"));
    console.log(`\nFailure details saved to ${path.relative(process.cwd(), file) || file}: paste its contents when asking for help.`);
  }
}
