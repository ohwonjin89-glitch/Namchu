import { NextResponse, NextRequest } from "next/server";
import { corsHeaders } from "@/lib/utils";
import { exec } from "child_process";
import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";

const LOG_PATH = path.join(
  process.env.LOCALAPPDATA || "C:\\Users\\오원진\\AppData\\Local",
  "dgm_pipeline_status.json"
);

export async function POST(req: NextRequest) {
  try {
    const { channel = "DGM" } = await req.json().catch(() => ({}));

    // Check if already running
    if (fs.existsSync(LOG_PATH)) {
      const status = JSON.parse(fs.readFileSync(LOG_PATH, "utf-8"));
      if (status.running) {
        return new NextResponse(
          JSON.stringify({ already_running: true, pid: status.pid }),
          { status: 200, headers: { "Content-Type": "application/json", ...corsHeaders } }
        );
      }
    }

    const apiKey = process.env.ANTHROPIC_API_KEY || "";
    const cmd = [
      "wsl",
      "--",
      "bash",
      "-c",
      `"export ANTHROPIC_API_KEY=${apiKey} && export SUNO_API_BASE=http://172.28.32.1:3000 && cd /home/wonjin/agents && python3 py_orchestrator.py ${channel} >> /home/wonjin/agents/logs/pipeline_run.log 2>&1 & echo $!"`,
    ].join(" ");

    const child = exec(cmd, { windowsHide: true });
    const pid = child.pid || 0;

    fs.writeFileSync(
      LOG_PATH,
      JSON.stringify({ running: true, pid, channel, startedAt: new Date().toISOString() }),
      "utf-8"
    );

    // Watch for completion
    child.on("exit", (code) => {
      const statusData = JSON.parse(fs.readFileSync(LOG_PATH, "utf-8"));
      fs.writeFileSync(
        LOG_PATH,
        JSON.stringify({ ...statusData, running: false, exitCode: code, finishedAt: new Date().toISOString() }),
        "utf-8"
      );
    });

    return new NextResponse(
      JSON.stringify({ started: true, pid, channel }),
      { status: 200, headers: { "Content-Type": "application/json", ...corsHeaders } }
    );
  } catch (e: any) {
    return new NextResponse(
      JSON.stringify({ error: e.message }),
      { status: 500, headers: { "Content-Type": "application/json", ...corsHeaders } }
    );
  }
}

export async function GET() {
  try {
    // Return pipeline status
    const statusPath = LOG_PATH;
    const statePath = process.env.TEMP
      ? path.join(process.env.TEMP, "dgm_state_DGM.json")
      : "C:\\Windows\\Temp\\dgm_state_DGM.json";

    let pipelineStatus = { running: false };
    let state = null;

    if (fs.existsSync(statusPath)) {
      pipelineStatus = JSON.parse(fs.readFileSync(statusPath, "utf-8"));
    }
    // State is in /tmp on WSL — read via UNC path
    const wslStatePath = "\\\\wsl$\\Ubuntu\\tmp\\dgm_state_DGM.json";
    if (fs.existsSync(wslStatePath)) {
      state = JSON.parse(fs.readFileSync(wslStatePath, "utf-8"));
    }

    // Recent log tail
    const logPath = "\\\\wsl$\\Ubuntu\\home\\wonjin\\agents\\logs\\pipeline_run.log";
    let logTail = "";
    if (fs.existsSync(logPath)) {
      const lines = fs.readFileSync(logPath, "utf-8").split("\n");
      logTail = lines.slice(-20).join("\n");
    }

    return new NextResponse(
      JSON.stringify({ pipelineStatus, state, logTail }),
      { status: 200, headers: { "Content-Type": "application/json", ...corsHeaders } }
    );
  } catch (e: any) {
    return new NextResponse(
      JSON.stringify({ error: e.message }),
      { status: 500, headers: { "Content-Type": "application/json", ...corsHeaders } }
    );
  }
}

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: corsHeaders });
}
