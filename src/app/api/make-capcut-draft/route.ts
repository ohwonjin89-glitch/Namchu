import { NextResponse, NextRequest } from 'next/server';
import { corsHeaders } from '@/lib/utils';
import { spawn } from 'child_process';
import * as fs from 'fs';
import * as https from 'https';
import * as http from 'http';
import * as path from 'path';
import { isRunningInsideWSL, getPythonCommand } from '@/lib/pythonEnv';

export const dynamic = 'force-dynamic';

const IS_WSL = isRunningInsideWSL();
const SCRIPT_PATH = path.join(process.cwd(), 'scripts', 'make_capcut_draft.py');

/** HTTP(S) URL을 브라우저처럼 보이는 헤더로 다운로드 */
function downloadWithBrowserHeaders(url: string, dest: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const options = {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
        'Referer': 'http://localhost:3000/',
      },
    };
    const protocol = url.startsWith('https') ? https : http;
    const file = fs.createWriteStream(dest);
    protocol.get(url, options, (res) => {
      if (res.statusCode === 301 || res.statusCode === 302) {
        file.close();
        fs.unlink(dest, () => {});
        return downloadWithBrowserHeaders(res.headers.location!, dest).then(resolve).catch(reject);
      }
      if (res.statusCode !== 200) {
        file.close();
        fs.unlink(dest, () => {});
        return reject(new Error(`HTTP ${res.statusCode} — ${url}`));
      }
      res.pipe(file);
      file.on('finish', () => file.close(() => resolve()));
    }).on('error', (err) => {
      fs.unlink(dest, () => {});
      reject(err);
    });
  });
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { outputDir, draftName, bgImageUrl, musicFiles, tracklistText, channel } = body;

    if (!outputDir) {
      return new NextResponse(JSON.stringify({ error: 'outputDir is required' }), {
        status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }
    if (!bgImageUrl) {
      return new NextResponse(JSON.stringify({ error: 'bgImageUrl is required' }), {
        status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }
    if (!musicFiles || !musicFiles.length) {
      return new NextResponse(JSON.stringify({ error: 'musicFiles is required' }), {
        status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders },
      });
    }

    if (IS_WSL) {
      return new NextResponse(
        JSON.stringify({ error: 'WSL 환경에서는 CapCut 초안 생성 불가. Windows 네이티브에서 실행해주세요.' }),
        { status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
      );
    }

    fs.mkdirSync(outputDir, { recursive: true });

    // HTTP URL이면 브라우저 헤더로 서버에서 직접 다운로드
    let resolvedBgPath = bgImageUrl;
    if (bgImageUrl.startsWith('http')) {
      const ext = path.extname(bgImageUrl.split('?')[0]) || '.png';
      const localPath = path.join(outputDir, `bg_image${ext}`);
      try {
        await downloadWithBrowserHeaders(bgImageUrl, localPath);
        resolvedBgPath = localPath;
        console.log('[make-capcut-draft] BG 이미지 다운로드 완료:', localPath);
      } catch (dlErr: any) {
        console.error('[make-capcut-draft] BG 이미지 다운로드 실패:', dlErr.message);
        return new NextResponse(
          JSON.stringify({ error: `배경 이미지 다운로드 실패: ${dlErr.message}` }),
          { status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
        );
      }
    }

    // _config.json 생성
    const configPath = path.join(outputDir, '_capcut_config.json');
    const config = {
      bgImageUrl: resolvedBgPath,
      musicFiles,
      tracklistOverlay: { text: tracklistText || '' },
      outputDir,
    };
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2), 'utf-8');

    const args = [SCRIPT_PATH, '--config', configPath];
    if (draftName) args.push('--name', draftName);
    if (channel)   args.push('--channel', channel);

    const result = await new Promise<{ success: boolean; output: string; error?: string }>(
      (resolve) => {
        const child = spawn(getPythonCommand(), args, {
          windowsHide: true,
          stdio: ['ignore', 'pipe', 'pipe'],
          env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' },
        });

        let stdout = '';
        let stderr = '';
        child.stdout.on('data', (d: Buffer) => { stdout += d.toString('utf8'); });
        child.stderr.on('data', (d: Buffer) => { stderr += d.toString('utf8'); });
        child.on('error', (err: Error) => {
          resolve({ success: false, output: '', error: err.message });
        });
        child.on('close', (code: number) => {
          resolve({
            success: code === 0,
            output: stdout,
            error: code !== 0 ? (stderr || `exit code ${code}`) : undefined,
          });
        });
        setTimeout(() => {
          child.kill();
          resolve({ success: false, output: stdout, error: 'timeout (30s)' });
        }, 30_000);
      }
    );

    if (!result.success) {
      console.error('[make-capcut-draft] 실패:', result.error);
      return new NextResponse(
        JSON.stringify({ error: result.error, output: result.output }),
        { status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
      );
    }

    const folderMatch = result.output.match(/폴더\s*:\s*(.+)/);
    const draftFolder = folderMatch ? folderMatch[1].trim() : '';

    return new NextResponse(
      JSON.stringify({ success: true, output: result.output, draftPath: draftFolder }),
      { status: 200, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
    );
  } catch (e: any) {
    return new NextResponse(JSON.stringify({ error: e.message }), {
      status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders },
    });
  }
}

export async function OPTIONS() {
  return new Response(null, { status: 200, headers: corsHeaders });
}
