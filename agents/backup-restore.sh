#!/bin/bash
# DGM 프롬프트 가이드 백업 / 복원 시스템
#
# Usage:
#   bash agents/backup-restore.sh backup [태그]     현재 상태 백업 (태그 선택: baseline, auto, 날짜)
#   bash agents/backup-restore.sh list               백업 목록 보기
#   bash agents/backup-restore.sh restore [버전명]   특정 버전으로 복원
#   bash agents/backup-restore.sh restore baseline   초기 버전으로 복원
#   bash agents/backup-restore.sh diff [버전명]      현재와 특정 버전 차이 확인

# 경로 자동 감지: 이 스크립트(agents/backup-restore.sh)의 실제 위치 기준으로
# 저장소 루트를 스스로 찾는다 (WSL/RunPod/VPS 등 배포 서버가 바뀌어도 항상 정확).
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BACKUP_BASE="$PROJECT_DIR/.claude/agents/backups"
AGENTS_DIR="$PROJECT_DIR/.claude/agents"
LOG_FILE="$BACKUP_BASE/BACKUP_LOG.md"

# 백업 대상 파일 (프롬프트 가이드 관련만)
BACKUP_FILES=(
  "music-generator.md"
  "music-generator-genre-samples.md"
  "image-generator.md"
  "researcher.md"
)

# ──────────────────────────────────────────────
log_entry() {
  local action="$1" version="$2" note="$3"
  echo "| $(date '+%Y-%m-%d %H:%M') | ${action} | ${version} | ${note} |" >> "$LOG_FILE"
}

cmd_backup() {
  local tag="${1:-auto}"
  local timestamp=$(date '+%Y%m%d_%H%M%S')

  if [ "$tag" = "baseline" ]; then
    VERSION="v_baseline"
  else
    VERSION="v_${timestamp}_${tag}"
  fi

  DEST="$BACKUP_BASE/$VERSION"

  # baseline은 1회만 허용
  if [ "$tag" = "baseline" ] && [ -d "$DEST" ]; then
    echo "⚠ baseline 백업이 이미 존재합니다: $DEST"
    echo "  기존 baseline을 덮어쓰려면 먼저 삭제 후 재실행하세요."
    exit 1
  fi

  mkdir -p "$DEST"

  local copied=0
  for file in "${BACKUP_FILES[@]}"; do
    src="$AGENTS_DIR/$file"
    if [ -f "$src" ]; then
      cp "$src" "$DEST/$file"
      echo "  ✓ $file"
      ((copied++))
    else
      echo "  - $file (없음 — 건너뜀)"
    fi
  done

  # style-database.json도 백업 (있으면)
  if [ -f "$AGENTS_DIR/style-database.json" ]; then
    cp "$AGENTS_DIR/style-database.json" "$DEST/style-database.json"
    echo "  ✓ style-database.json"
  fi

  # 로그 초기화 (없으면)
  if [ ! -f "$LOG_FILE" ]; then
    echo "# DGM 프롬프트 백업 로그" > "$LOG_FILE"
    echo "" >> "$LOG_FILE"
    echo "| 일시 | 작업 | 버전 | 비고 |" >> "$LOG_FILE"
    echo "|------|------|------|------|" >> "$LOG_FILE"
  fi

  log_entry "BACKUP" "$VERSION" "${copied}개 파일"

  echo ""
  echo "✅ 백업 완료: $VERSION ($copied개 파일)"
  if [ "$tag" = "baseline" ]; then
    echo "   ★ 초기 버전(baseline) 저장됨 — 언제든 이 상태로 복원 가능"
  fi

  # cron 자동 백업은 매일 쌓이므로 30일 지난 auto 백업은 정리한다
  # (baseline/수동 태그 백업은 절대 자동 삭제하지 않음)
  if [ "$tag" = "auto" ]; then
    find "$BACKUP_BASE" -maxdepth 1 -type d -name 'v_*_auto' -mtime +30 -print -exec rm -rf {} \; \
      | while read -r pruned; do echo "  🗑 30일 경과 auto 백업 정리: $(basename "$pruned")"; done
  fi
}

cmd_list() {
  echo "── DGM 프롬프트 가이드 백업 목록 ──────────────────"
  if [ ! -d "$BACKUP_BASE" ] || [ -z "$(ls -A "$BACKUP_BASE" 2>/dev/null)" ]; then
    echo "  백업 없음"
    return
  fi

  for dir in "$BACKUP_BASE"/v_*/; do
    [ -d "$dir" ] || continue
    version=$(basename "$dir")
    count=$(ls "$dir"*.md "$dir"*.json 2>/dev/null | wc -l)
    size=$(du -sh "$dir" 2>/dev/null | cut -f1)

    if [ "$version" = "v_baseline" ]; then
      echo "  ★ $version  [초기버전]  파일 ${count}개  ${size}"
    else
      echo "    $version  파일 ${count}개  ${size}"
    fi
  done

  echo ""
  echo "복원 명령: bash agents/backup-restore.sh restore [버전명]"
  echo "초기화 명령: bash agents/backup-restore.sh restore baseline"
}

cmd_restore() {
  local target="${1}"

  if [ -z "$target" ]; then
    echo "❌ 복원할 버전을 지정해주세요."
    echo "   사용법: bash agents/backup-restore.sh restore [버전명]"
    cmd_list
    exit 1
  fi

  if [ "$target" = "baseline" ]; then
    RESTORE_DIR="$BACKUP_BASE/v_baseline"
  else
    RESTORE_DIR="$BACKUP_BASE/$target"
  fi

  if [ ! -d "$RESTORE_DIR" ]; then
    echo "❌ 버전을 찾을 수 없습니다: $target"
    echo "   사용 가능한 버전 목록:"
    cmd_list
    exit 1
  fi

  # 복원 전 현재 상태 자동 백업
  echo "▶ 복원 전 현재 상태 자동 백업 중..."
  cmd_backup "pre_restore"
  echo ""

  echo "▶ $target 버전으로 복원 중..."
  local restored=0
  for file in "${BACKUP_FILES[@]}"; do
    src="$RESTORE_DIR/$file"
    dst="$AGENTS_DIR/$file"
    if [ -f "$src" ]; then
      cp "$src" "$dst"
      echo "  ✓ $file"
      ((restored++))
    fi
  done

  if [ -f "$RESTORE_DIR/style-database.json" ]; then
    cp "$RESTORE_DIR/style-database.json" "$AGENTS_DIR/style-database.json"
    echo "  ✓ style-database.json"
  fi

  log_entry "RESTORE" "$target" "${restored}개 파일 복원"

  echo ""
  echo "✅ 복원 완료: $target ($restored개 파일)"
  if [ "$target" = "baseline" ] || [ "$target" = "v_baseline" ]; then
    echo "   초기 버전으로 복원됐습니다. AI 자동 보완 내용이 모두 초기화됐습니다."
  fi
}

cmd_diff() {
  local target="${1:-v_baseline}"
  local compare_dir

  if [ "$target" = "baseline" ]; then
    compare_dir="$BACKUP_BASE/v_baseline"
  else
    compare_dir="$BACKUP_BASE/$target"
  fi

  if [ ! -d "$compare_dir" ]; then
    echo "❌ 버전을 찾을 수 없습니다: $target"
    exit 1
  fi

  echo "── 현재 vs $target 차이 ──────────────────"
  for file in "${BACKUP_FILES[@]}"; do
    current="$AGENTS_DIR/$file"
    backup="$compare_dir/$file"
    if [ -f "$current" ] && [ -f "$backup" ]; then
      diff_lines=$(diff "$backup" "$current" | grep -c "^[<>]" 2>/dev/null || echo 0)
      if [ "$diff_lines" -gt 0 ]; then
        echo "  변경: $file  ($diff_lines줄 차이)"
        diff "$backup" "$current" | head -30
        echo "  ..."
      else
        echo "  동일: $file"
      fi
    fi
  done
}

# ── 메인 ──
ACTION="${1:-help}"

case "$ACTION" in
  backup)   cmd_backup "${2:-auto}" ;;
  list)     cmd_list ;;
  restore)  cmd_restore "$2" ;;
  diff)     cmd_diff "$2" ;;
  *)
    echo "DGM 프롬프트 가이드 백업/복원 시스템"
    echo ""
    echo "명령어:"
    echo "  backup [태그]        현재 상태 백업 (태그 예: baseline, v2)"
    echo "  backup baseline      초기 버전 저장 (장르 가이드 작성 완료 후 1회 실행)"
    echo "  list                 백업 목록 보기"
    echo "  restore [버전명]     특정 버전으로 복원"
    echo "  restore baseline     초기 버전으로 복원 (AI 자동 보완 내용 초기화)"
    echo "  diff [버전명]        현재와 특정 버전 차이 확인"
    ;;
esac
