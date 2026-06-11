import { NextResponse, NextRequest } from 'next/server';
import { corsHeaders } from '@/lib/utils';
import * as fs from 'fs';
import * as path from 'path';
import * as https from 'https';
import * as http from 'http';

export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  try {
    const { audioUrl, fileName, savePath } = await req.json();

    if (!audioUrl || !fileName || !savePath) {
      return new NextResponse(
        JSON.stringify({ error: 'audioUrl, fileName, savePath 모두 필요합니다.' }),
        { status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
      );
    }

    // 저장 폴더 없으면 자동 생성
    fs.mkdirSync(savePath, { recursive: true });

    const fullPath = path.join(savePath, fileName);

    // URL에서 파일 다운로드 후 저장
    await downloadFile(audioUrl, fullPath);

    return new NextResponse(
      JSON.stringify({ success: true, savedPath: fullPath }),
      { status: 200, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
    );
  } catch (error: any) {
    console.error('Download error:', error);
    return new NextResponse(
      JSON.stringify({ error: error.message || '다운로드 실패' }),
      { status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
    );
  }
}

function downloadFile(url: string, dest: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(dest);
    const protocol = url.startsWith('https') ? https : http;

    protocol.get(url, (response) => {
      // 리다이렉트 처리
      if (response.statusCode === 301 || response.statusCode === 302) {
        file.close();
        fs.unlink(dest, () => {});
        return downloadFile(response.headers.location!, dest).then(resolve).catch(reject);
      }
      if (response.statusCode !== 200) {
        file.close();
        fs.unlink(dest, () => {});
        return reject(new Error(`HTTP ${response.statusCode}`));
      }
      response.pipe(file);
      file.on('finish', () => file.close(() => resolve()));
    }).on('error', (err) => {
      fs.unlink(dest, () => {});
      reject(err);
    });
  });
}

export async function OPTIONS() {
  return new Response(null, { status: 200, headers: corsHeaders });
}
