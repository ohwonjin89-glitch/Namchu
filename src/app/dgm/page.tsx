'use client';

import { useState, useEffect, useRef, useCallback } from 'react';

// ── Types ──────────────────────────────────────────────────────────────────
type StepStatus = 'pending' | 'done' | 'error';
type Steps = Record<string, StepStatus>;

interface Run {
  runId: string;
  channel: string;
  status: string;
  uploadedUrl: string | null;
  uploadTitle: string | null;
  startedAt: string | null;
  completedAt: string | null;
  steps: Steps;
  hasImage: boolean;
}

interface RunDetail {
  state: any;
  meetingLog: string | null;
}

// ── Constants ─────────────────────────────────────────────────────────────
const STEP_LABELS: Record<string, string> = {
  trend: '① 트렌드',
  prompt: '② 컨셉',
  music: '③ 음악',
  image: '④ 이미지',
  video: '⑤ 영상',
  upload: '⑥ 업로드',
};

const STEP_ORDER = ['trend', 'prompt', 'music', 'image', 'video', 'upload'];

// ── Helpers ───────────────────────────────────────────────────────────────
function StepBadge({ status }: { status: StepStatus | undefined }) {
  if (status === 'done') return <span className="text-green-400">✅</span>;
  if (status === 'error') return <span className="text-red-400">❌</span>;
  return <span className="text-gray-500">○</span>;
}

function fmtTime(iso: string | null) {
  if (!iso) return '-';
  return new Date(iso).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

// ── Main Component ─────────────────────────────────────────────────────────
export default function DGMDashboard() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [selectedRun, setSelectedRun] = useState<string | null>(null);
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [tab, setTab] = useState<'result' | 'log' | 'guidelines'>('result');
  const [liveLog, setLiveLog] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [guidelines, setGuidelines] = useState<{ name: string; label: string }[]>([]);
  const [selectedGuide, setSelectedGuide] = useState<string | null>(null);
  const [guideContent, setGuideContent] = useState('');
  const [guideSaving, setGuideSaving] = useState(false);
  const [guideSaved, setGuideSaved] = useState(false);
  const logRef = useRef<HTMLPreElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Fetch runs list ───────────────────────────────────────────────────
  const fetchRuns = useCallback(async () => {
    try {
      const r = await fetch('/api/dgm/runs?channel=DGM');
      const data = await r.json();
      if (data.runs) setRuns(data.runs);
    } catch {}
  }, []);

  // ── Fetch run detail ──────────────────────────────────────────────────
  const fetchDetail = useCallback(async (runId: string) => {
    try {
      const r = await fetch(`/api/dgm/runs?channel=DGM&runId=${runId}`);
      const data = await r.json();
      if (data.state) setDetail(data);
    } catch {}
  }, []);

  // ── Fetch pipeline status (live log) ─────────────────────────────────
  const fetchStatus = useCallback(async () => {
    try {
      const r = await fetch('/api/run-pipeline');
      const data = await r.json();
      setIsRunning(data.pipelineStatus?.running ?? false);
      if (data.logTail) setLiveLog(data.logTail);
    } catch {}
  }, []);

  // ── Fetch guidelines list ─────────────────────────────────────────────
  const fetchGuidelinesList = useCallback(async () => {
    try {
      const r = await fetch('/api/dgm/guidelines');
      const data = await r.json();
      if (data.files) setGuidelines(data.files);
    } catch {}
  }, []);

  // ── Fetch guideline file ──────────────────────────────────────────────
  const fetchGuidelineFile = useCallback(async (file: string) => {
    try {
      const r = await fetch(`/api/dgm/guidelines?file=${encodeURIComponent(file)}`);
      const data = await r.json();
      if (data.content !== undefined) setGuideContent(data.content);
    } catch {}
  }, []);

  // ── Save guideline file ───────────────────────────────────────────────
  const saveGuideline = async () => {
    if (!selectedGuide) return;
    setGuideSaving(true);
    try {
      await fetch('/api/dgm/guidelines', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file: selectedGuide, content: guideContent }),
      });
      setGuideSaved(true);
      setTimeout(() => setGuideSaved(false), 2000);
    } catch {}
    setGuideSaving(false);
  };

  // ── Run pipeline ──────────────────────────────────────────────────────
  const runPipeline = async (numTracks: number) => {
    if (isRunning) return;
    setIsRunning(true);
    setLiveLog('파이프라인 시작 중...');
    setTab('log');
    try {
      await fetch('/api/run-pipeline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel: 'DGM', num_tracks: numTracks }),
      });
    } catch {}
  };

  // ── Initial load ──────────────────────────────────────────────────────
  useEffect(() => {
    fetchRuns();
    fetchStatus();
    fetchGuidelinesList();

    pollRef.current = setInterval(() => {
      fetchStatus();
      if (isRunning) fetchRuns();
    }, 5000);

    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  // ── Auto-select latest run ────────────────────────────────────────────
  useEffect(() => {
    if (runs.length > 0 && !selectedRun) {
      setSelectedRun(runs[0].runId);
    }
  }, [runs]);

  // ── Load detail when run selected ────────────────────────────────────
  useEffect(() => {
    if (selectedRun) fetchDetail(selectedRun);
  }, [selectedRun]);

  // ── Auto-scroll log ───────────────────────────────────────────────────
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [liveLog]);

  // ── Load guideline on select ──────────────────────────────────────────
  useEffect(() => {
    if (selectedGuide) fetchGuidelineFile(selectedGuide);
  }, [selectedGuide]);

  const selectedRunData = runs.find(r => r.runId === selectedRun);
  const concept = detail?.state?.selectedPrompt;
  const stepData = detail?.state?.stepData || {};
  const steps: Steps = detail?.state?.steps || selectedRunData?.steps || {};

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 font-mono text-sm">
      {/* Header */}
      <div className="border-b border-gray-800 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold text-white">DGM Pipeline</span>
          {isRunning && (
            <span className="px-2 py-0.5 text-xs bg-yellow-500/20 text-yellow-400 rounded-full animate-pulse">
              실행 중
            </span>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => runPipeline(1)}
            disabled={isRunning}
            className="px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-xs font-medium"
          >
            ▶ 테스트 (1곡)
          </button>
          <button
            onClick={() => runPipeline(3)}
            disabled={isRunning}
            className="px-3 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-xs font-medium"
          >
            ▶ 테스트 (3곡)
          </button>
          <button
            onClick={() => runPipeline(20)}
            disabled={isRunning}
            className="px-3 py-1.5 rounded bg-purple-700 hover:bg-purple-600 disabled:opacity-40 text-xs font-medium"
          >
            ▶ 운영 (20곡)
          </button>
          <button
            onClick={() => { fetchRuns(); fetchStatus(); }}
            className="px-3 py-1.5 rounded bg-gray-700 hover:bg-gray-600 text-xs"
          >
            ↻ 새로고침
          </button>
        </div>
      </div>

      <div className="flex h-[calc(100vh-53px)]">
        {/* Left: Run History */}
        <div className="w-56 border-r border-gray-800 overflow-y-auto flex-shrink-0">
          <div className="px-3 py-2 text-xs text-gray-500 uppercase tracking-wide border-b border-gray-800">
            실행 기록
          </div>
          {runs.length === 0 && (
            <div className="p-3 text-xs text-gray-600">실행 기록 없음</div>
          )}
          {runs.map(run => (
            <button
              key={run.runId}
              onClick={() => setSelectedRun(run.runId)}
              className={`w-full text-left px-3 py-2.5 border-b border-gray-800/50 hover:bg-gray-800/50 transition-colors ${
                selectedRun === run.runId ? 'bg-gray-800 border-l-2 border-l-blue-500' : ''
              }`}
            >
              <div className="text-xs text-gray-300 mb-1">
                {run.runId.replace('_', ' ')}
              </div>
              <div className="flex gap-1 flex-wrap">
                {STEP_ORDER.map(s => (
                  <span key={s} title={STEP_LABELS[s]}>
                    <StepBadge status={run.steps[s]} />
                  </span>
                ))}
              </div>
              {run.uploadedUrl && (
                <div className="mt-1 text-xs text-blue-400 truncate">
                  ✅ 업로드됨
                </div>
              )}
            </button>
          ))}
        </div>

        {/* Main Content */}
        <div className="flex-1 overflow-hidden flex flex-col">
          {/* Tabs */}
          <div className="flex border-b border-gray-800 px-4 gap-1 pt-1">
            {(['result', 'log', 'guidelines'] as const).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-4 py-1.5 text-xs rounded-t transition-colors ${
                  tab === t
                    ? 'bg-gray-800 text-white'
                    : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                {t === 'result' ? '📊 결과 확인' : t === 'log' ? '📋 실행 로그' : '📝 지침서 편집'}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto">

            {/* ── Result Tab ─────────────────────────────────────────── */}
            {tab === 'result' && (
              <div className="p-4 space-y-4">
                {!selectedRun && (
                  <div className="text-gray-500 text-center py-10">
                    왼쪽에서 실행 기록을 선택하세요
                  </div>
                )}

                {/* Step overview */}
                {selectedRunData && (
                  <div className="bg-gray-900 rounded-lg p-4">
                    <div className="text-xs text-gray-500 mb-2">단계별 상태</div>
                    <div className="grid grid-cols-6 gap-2">
                      {STEP_ORDER.map(s => (
                        <div key={s} className="text-center">
                          <div className="text-lg"><StepBadge status={steps[s]} /></div>
                          <div className="text-xs text-gray-400 mt-1">{STEP_LABELS[s]}</div>
                        </div>
                      ))}
                    </div>
                    {selectedRunData.startedAt && (
                      <div className="mt-2 text-xs text-gray-600">
                        시작: {fmtTime(selectedRunData.startedAt)}
                        {selectedRunData.completedAt && ` → 완료: ${fmtTime(selectedRunData.completedAt)}`}
                      </div>
                    )}
                  </div>
                )}

                {/* Trend & Concept side by side */}
                {(stepData.trend || concept) && (
                  <div className="grid grid-cols-2 gap-3">
                    {stepData.trend?.titles && (
                      <div className="bg-gray-900 rounded-lg p-3">
                        <div className="text-xs text-gray-500 mb-2">① 트렌드 수집</div>
                        <ul className="space-y-1">
                          {stepData.trend.titles.map((t: string, i: number) => (
                            <li key={i} className="text-xs text-gray-300 truncate">
                              {i + 1}. {t}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {concept && (
                      <div className="bg-gray-900 rounded-lg p-3">
                        <div className="text-xs text-gray-500 mb-2">② 음악 컨셉</div>
                        <div className="space-y-1 text-xs">
                          <div><span className="text-gray-500">제목:</span> <span className="text-yellow-300">{concept.title}</span></div>
                          <div><span className="text-gray-500">스타일:</span> {concept.style}</div>
                          <div><span className="text-gray-500">분위기:</span> {concept.mood}</div>
                          <div><span className="text-gray-500">가이드:</span> {concept.guide}</div>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Music */}
                {stepData.music && (
                  <div className="bg-gray-900 rounded-lg p-3">
                    <div className="text-xs text-gray-500 mb-2">③ 음악 생성</div>
                    <div className="text-xs mb-1">
                      총 <span className="text-green-400">{stepData.music.numTracks}곡</span> 완성
                    </div>
                    <div className="flex gap-2 flex-wrap">
                      {stepData.music.tracks?.map((t: any) => (
                        <span key={t.num} className="px-2 py-0.5 bg-gray-800 rounded text-xs text-gray-300">
                          트랙{t.num} {t.fileSizeMB}MB
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Image + Video side by side */}
                <div className="grid grid-cols-2 gap-3">
                  {/* Image */}
                  <div className="bg-gray-900 rounded-lg p-3">
                    <div className="text-xs text-gray-500 mb-2">④ 배경 이미지</div>
                    {selectedRunData?.hasImage ? (
                      <>
                        <img
                          src={`/api/dgm/image?channel=DGM&runId=${selectedRun}`}
                          alt="배경"
                          className="w-full rounded aspect-video object-cover"
                        />
                        {stepData.image?.method === 'fallback' && (
                          <div className="mt-1 text-xs text-orange-400">
                            ⚠️ 폴백 (단색) — 이유: {stepData.image?.error}
                          </div>
                        )}
                        {stepData.image?.method === 'ai' && (
                          <div className="mt-1 text-xs text-green-400">✅ AI 생성</div>
                        )}
                      </>
                    ) : (
                      <div className="text-xs text-gray-600 py-4 text-center">이미지 없음</div>
                    )}
                  </div>

                  {/* Upload */}
                  <div className="bg-gray-900 rounded-lg p-3">
                    <div className="text-xs text-gray-500 mb-2">⑥ YouTube 업로드</div>
                    {detail?.state?.uploadedUrl ? (
                      <>
                        <div className="text-xs text-gray-300 mb-2">
                          {detail.state.stepData?.upload?.title || detail.state.uploadTitle}
                        </div>
                        <a
                          href={detail.state.uploadedUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-block px-3 py-1.5 bg-red-700 hover:bg-red-600 rounded text-xs text-white"
                        >
                          ▶ YouTube에서 보기
                        </a>
                        <div className="mt-2">
                          <iframe
                            src={`https://www.youtube.com/embed/${detail.state.uploadedVideoId}`}
                            className="w-full aspect-video rounded"
                            allow="autoplay"
                          />
                        </div>
                      </>
                    ) : detail?.state?.uploadError ? (
                      <div className="text-xs text-red-400">
                        ❌ {detail.state.uploadError}
                      </div>
                    ) : (
                      <div className="text-xs text-gray-600 py-4 text-center">업로드 미완료</div>
                    )}
                  </div>
                </div>

                {/* Meeting Log */}
                {detail?.meetingLog && (
                  <div className="bg-gray-900 rounded-lg p-3">
                    <div className="text-xs text-gray-500 mb-2">회의록 미리보기</div>
                    <pre className="text-xs text-gray-400 whitespace-pre-wrap max-h-40 overflow-y-auto">
                      {detail.meetingLog}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {/* ── Log Tab ────────────────────────────────────────────── */}
            {tab === 'log' && (
              <div className="p-4 h-full">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-gray-500">최근 실행 로그 (마지막 20줄)</span>
                  <button
                    onClick={fetchStatus}
                    className="text-xs text-gray-500 hover:text-gray-300"
                  >
                    ↻ 갱신
                  </button>
                </div>
                <pre
                  ref={logRef}
                  className="bg-gray-900 rounded-lg p-3 text-xs text-green-300 overflow-y-auto h-[calc(100vh-160px)] whitespace-pre-wrap"
                >
                  {liveLog || '로그 없음'}
                </pre>
              </div>
            )}

            {/* ── Guidelines Tab ──────────────────────────────────────── */}
            {tab === 'guidelines' && (
              <div className="p-4 flex gap-3 h-full">
                {/* File list */}
                <div className="w-44 flex-shrink-0">
                  <div className="text-xs text-gray-500 mb-2">에이전트 지침서</div>
                  <div className="space-y-1">
                    {guidelines.map(g => (
                      <button
                        key={g.name}
                        onClick={() => setSelectedGuide(g.name)}
                        className={`w-full text-left px-3 py-2 rounded text-xs transition-colors ${
                          selectedGuide === g.name
                            ? 'bg-blue-700 text-white'
                            : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                        }`}
                      >
                        {g.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Editor */}
                <div className="flex-1 flex flex-col">
                  {selectedGuide ? (
                    <>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs text-gray-400">{selectedGuide}</span>
                        <button
                          onClick={saveGuideline}
                          disabled={guideSaving}
                          className={`px-3 py-1 rounded text-xs font-medium ${
                            guideSaved
                              ? 'bg-green-700 text-white'
                              : 'bg-blue-600 hover:bg-blue-500 text-white'
                          }`}
                        >
                          {guideSaving ? '저장 중...' : guideSaved ? '✅ 저장됨' : '💾 저장'}
                        </button>
                      </div>
                      <textarea
                        value={guideContent}
                        onChange={e => setGuideContent(e.target.value)}
                        className="flex-1 bg-gray-900 text-gray-100 text-xs p-3 rounded-lg resize-none focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono"
                        spellCheck={false}
                      />
                    </>
                  ) : (
                    <div className="text-xs text-gray-600 text-center py-10">
                      왼쪽에서 파일을 선택하세요
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
