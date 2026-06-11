import { NextResponse, NextRequest } from "next/server";
import { corsHeaders } from "@/lib/utils";
import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";

const CACHE_PATH = path.join("D:\\AI Agent\\Claude", "trend_cache.json");

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const payload = {
      ...body,
      savedAt: new Date().toISOString(),
      source: "n8n",
    };
    fs.writeFileSync(CACHE_PATH, JSON.stringify(payload, null, 2), "utf-8");
    console.log("[trend-cache] saved:", CACHE_PATH);
    return new NextResponse(
      JSON.stringify({ success: true, savedAt: payload.savedAt }),
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
    if (!fs.existsSync(CACHE_PATH)) {
      return new NextResponse(
        JSON.stringify({ exists: false }),
        { status: 200, headers: { "Content-Type": "application/json", ...corsHeaders } }
      );
    }
    const raw = fs.readFileSync(CACHE_PATH, "utf-8");
    const data = JSON.parse(raw);
    return new NextResponse(
      JSON.stringify({ exists: true, ...data }),
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
