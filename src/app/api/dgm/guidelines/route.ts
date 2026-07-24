import { NextResponse, NextRequest } from 'next/server';
import { corsHeaders } from '@/lib/utils';
import fs from 'fs';
import path from 'path';

export const dynamic = 'force-dynamic';

const INSTRUCTIONS_DIR = path.join(process.cwd(), 'agents', 'instructions');

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const file = searchParams.get('file');

    if (!file) {
      const files = fs.readdirSync(INSTRUCTIONS_DIR)
        .filter(f => f.endsWith('.md'))
        .map(f => ({
          name: f,
          label: f.replace('.md', ''),
          updatedAt: fs.statSync(path.join(INSTRUCTIONS_DIR, f)).mtime.toISOString(),
        }));
      return NextResponse.json({ files }, { headers: corsHeaders });
    }

    const filePath = path.resolve(INSTRUCTIONS_DIR, file);
    if (!filePath.startsWith(INSTRUCTIONS_DIR)) {
      return NextResponse.json({ error: '잘못된 경로' }, { status: 403, headers: corsHeaders });
    }
    if (!fs.existsSync(filePath)) {
      return NextResponse.json({ error: '파일 없음' }, { status: 404, headers: corsHeaders });
    }

    const content = fs.readFileSync(filePath, 'utf-8');
    return NextResponse.json({ content }, { headers: corsHeaders });
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500, headers: corsHeaders });
  }
}

export async function PUT(req: NextRequest) {
  try {
    const { file, content } = await req.json();
    if (!file || typeof content !== 'string') {
      return NextResponse.json({ error: '파라미터 오류' }, { status: 400, headers: corsHeaders });
    }

    const filePath = path.resolve(INSTRUCTIONS_DIR, file);
    if (!filePath.startsWith(INSTRUCTIONS_DIR)) {
      return NextResponse.json({ error: '잘못된 경로' }, { status: 403, headers: corsHeaders });
    }

    fs.writeFileSync(filePath, content, 'utf-8');
    return NextResponse.json({ success: true }, { headers: corsHeaders });
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500, headers: corsHeaders });
  }
}

export async function OPTIONS() {
  return new Response(null, { status: 200, headers: corsHeaders });
}
