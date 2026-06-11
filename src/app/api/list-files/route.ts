import { NextResponse, NextRequest } from 'next/server';
import { corsHeaders } from '@/lib/utils';
import * as fs from 'fs';

export const dynamic = 'force-dynamic';

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const dir = url.searchParams.get('dir');
  const filter = url.searchParams.get('filter') || '';

  if (!dir) {
    return new NextResponse(JSON.stringify({ error: 'dir parameter required' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json', ...corsHeaders },
    });
  }

  try {
    if (!fs.existsSync(dir)) {
      return new NextResponse(JSON.stringify({ files: [], dirs: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }

    const entries = fs.readdirSync(dir, { withFileTypes: true });

    const exts = filter ? filter.split(',').map(f => '.' + f.trim().toLowerCase()) : [];
    const files = entries
      .filter(e => e.isFile() && (!filter || exts.some(ext => e.name.toLowerCase().endsWith(ext))))
      .map(e => e.name)
      .sort();

    const dirs = entries
      .filter(e => e.isDirectory() && !e.name.startsWith('_') && !e.name.startsWith('.'))
      .map(e => e.name)
      .sort();

    return new NextResponse(JSON.stringify({ files, dirs }), {
      status: 200,
      headers: { 'Content-Type': 'application/json', ...corsHeaders },
    });
  } catch (e: any) {
    return new NextResponse(JSON.stringify({ error: e.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json', ...corsHeaders },
    });
  }
}

export async function OPTIONS() {
  return new Response(null, { status: 200, headers: corsHeaders });
}
