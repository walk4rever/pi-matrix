#!/usr/bin/env node
// Runs one TokenEconBench task against one (model, harness) pair and writes a result JSON.
// v0: harness is fixed to Claude Code (`claude -p`); the harness abstraction gets built
// out once a second harness is added (see docs/METHODOLOGY.md).

import { execFileSync } from "node:child_process";
import { cpSync, mkdtempSync, mkdirSync, readFileSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { parse as parseYaml } from "yaml";

function parseArgs(argv) {
  const [taskDir, ...rest] = argv;
  if (!taskDir) {
    console.error("Usage: node runner/run.mjs <task-dir> [--model <alias>] [--permission-mode <mode>]");
    process.exit(1);
  }
  const opts = { taskDir, model: "sonnet", permissionMode: "acceptEdits" };
  for (let i = 0; i < rest.length; i++) {
    if (rest[i] === "--model") opts.model = rest[++i];
    else if (rest[i] === "--permission-mode") opts.permissionMode = rest[++i];
  }
  return opts;
}

function loadTask(taskDir) {
  const manifestPath = path.join(taskDir, "task.yaml");
  const task = parseYaml(readFileSync(manifestPath, "utf8"));
  task._dir = taskDir;
  return task;
}

function runAgent({ workspace, prompt, model, permissionMode }) {
  const args = [
    "-p", prompt,
    "--output-format", "json",
    "--model", model,
    "--permission-mode", permissionMode,
  ];
  const startedAt = Date.now();
  const raw = execFileSync("claude", args, {
    cwd: workspace,
    encoding: "utf8",
    maxBuffer: 1024 * 1024 * 64,
  });
  const wallClockMs = Date.now() - startedAt;
  const result = JSON.parse(raw);
  return { result, wallClockMs };
}

function runOracleTest({ workspace, task }) {
  const oracleDir = path.join(task._dir, "oracle");
  for (const relPath of task.oracle.held_out_paths) {
    const src = path.join(oracleDir, relPath);
    const dest = path.join(workspace, relPath);
    mkdirSync(path.dirname(dest), { recursive: true });
    cpSync(src, dest);
  }
  execFileSync("npm", ["install", "--silent", "--no-fund", "--no-audit"], { cwd: workspace, stdio: "pipe" });
  try {
    execFileSync("npm", ["test", "--silent"], { cwd: workspace, stdio: "pipe" });
    return { pass: true };
  } catch (err) {
    return { pass: false, output: (err.stdout?.toString() ?? "") + (err.stderr?.toString() ?? "") };
  }
}

function main() {
  const opts = parseArgs(process.argv.slice(2));
  const task = loadTask(path.resolve(opts.taskDir));

  if (task.oracle.type !== "test") {
    console.error(`Oracle type "${task.oracle.type}" not yet supported by this runner (v0 supports "test" only).`);
    process.exit(1);
  }

  const workspace = mkdtempSync(path.join(tmpdir(), "token-econ-bench-"));
  cpSync(path.join(task._dir, "fixture"), workspace, { recursive: true });

  console.log(`[${task.id}] workspace: ${workspace}`);
  console.log(`[${task.id}] running agent (model=${opts.model})...`);
  const { result: agentResult, wallClockMs } = runAgent({
    workspace,
    prompt: task.prompt,
    model: opts.model,
    permissionMode: opts.permissionMode,
  });

  console.log(`[${task.id}] grading...`);
  const grade = runOracleTest({ workspace, task });

  const runId = new Date().toISOString().replace(/[:.]/g, "-");
  const outDir = path.join("reports", runId);
  mkdirSync(outDir, { recursive: true });
  const outPath = path.join(outDir, `${task.id}__${opts.model}.json`);

  const record = {
    task_id: task.id,
    category: task.category,
    oracle_confidence: task.oracle.confidence,
    model: opts.model,
    harness: "claude-code",
    pass: grade.pass,
    cost_usd: agentResult.total_cost_usd,
    wall_clock_ms: wallClockMs,
    agent_duration_ms: agentResult.duration_ms,
    num_turns: agentResult.num_turns,
    usage: agentResult.usage,
    is_error: agentResult.is_error,
    workspace,
    graded_at: new Date().toISOString(),
  };
  writeFileSync(outPath, JSON.stringify(record, null, 2));

  console.log(`[${task.id}] ${grade.pass ? "PASS" : "FAIL"} — $${agentResult.total_cost_usd.toFixed(4)}, ${wallClockMs}ms, ${agentResult.usage.input_tokens + agentResult.usage.output_tokens} tokens (+cache)`);
  console.log(`[${task.id}] result written to ${outPath}`);

  rmSync(workspace, { recursive: true, force: true });
}

main();
