#!/bin/bash
# 生成 macOS 桌面启动图标「三月七小助手.app」
# 用法：bash tools/macos/make_app.sh [输出目录，默认 ~/Desktop]
set -e
PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
OUT_DIR="${1:-$HOME/Desktop}"
APP="$OUT_DIR/三月七小助手.app"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if [ ! -x "$PROJECT_DIR/.venv/bin/python" ]; then
    echo "未找到 $PROJECT_DIR/.venv/bin/python，请先在项目目录执行 uv sync" >&2
    exit 1
fi

sed "s|__PROJECT_DIR__|$PROJECT_DIR|" "$PROJECT_DIR/tools/macos/launcher.applescript" > "$TMP/launcher.applescript"
rm -rf "$APP"
osacompile -o "$APP" "$TMP/launcher.applescript"

# 用项目图标替换 AppleScript 默认图标
sips -s format png "$PROJECT_DIR/assets/logo/March7th.ico" --out "$TMP/m7.png" >/dev/null
mkdir "$TMP/icon.iconset"
for s in 16 32 128 256; do
    sips -z $s $s "$TMP/m7.png" --out "$TMP/icon.iconset/icon_${s}x${s}.png" >/dev/null
    d=$((s * 2))
    sips -z $d $d "$TMP/m7.png" --out "$TMP/icon.iconset/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$TMP/icon.iconset" -o "$APP/Contents/Resources/applet.icns"
touch "$APP"
echo "已生成：$APP"
