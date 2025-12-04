#!/bin/bash
# AI视频生成插件 - 自动打包脚本
# 用法: ./build.sh [版本号]
# 示例: ./build.sh 0.0.11

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  AI视频生成插件 - 自动打包工具${NC}"
echo -e "${GREEN}========================================${NC}"

# 1. 检查必要文件
echo -e "\n${YELLOW}[1/5] 检查必要文件...${NC}"
REQUIRED_FILES=("manifest.yaml" "main.py" "requirements.txt" "_assets/icon.svg" "provider/ai_video.yaml" "provider/ai_video.py")
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ 错误: 缺少必要文件 $file${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✅ 所有必要文件存在${NC}"

# 2. 检查 tools 目录
echo -e "\n${YELLOW}[2/5] 检查工具文件...${NC}"
TOOL_FILES=("tools/text_to_video.py" "tools/text_to_video.yaml" "tools/image_to_video.py" "tools/image_to_video.yaml" "tools/query_task.py" "tools/query_task.yaml")
for file in "${TOOL_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ 错误: 缺少工具文件 $file${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✅ 所有工具文件存在${NC}"

# 3. 验证 manifest.yaml 配置
echo -e "\n${YELLOW}[3/5] 验证配置文件...${NC}"

# 检查 icon 路径
ICON_PATH=$(grep "^icon:" manifest.yaml | awk '{print $2}')
if [ ! -f "$ICON_PATH" ]; then
    echo -e "${RED}❌ 错误: manifest.yaml 中的 icon 路径无效: $ICON_PATH${NC}"
    echo -e "${YELLOW}   请修改为: icon: _assets/icon.svg${NC}"
    exit 1
fi
echo -e "${GREEN}✅ icon 路径正确: $ICON_PATH${NC}"

# 检查 provider 路径 (从 plugins.tools 中提取)
PROVIDER_PATH=$(grep -A2 "plugins:" manifest.yaml | grep "\- " | head -1 | sed 's/.*- //')
if [ ! -f "$PROVIDER_PATH" ]; then
    echo -e "${RED}❌ 错误: manifest.yaml 中的 provider 路径无效: $PROVIDER_PATH${NC}"
    exit 1
fi
echo -e "${GREEN}✅ provider 路径正确: $PROVIDER_PATH${NC}"

# 4. 获取版本号
echo -e "\n${YELLOW}[4/5] 处理版本号...${NC}"
if [ -n "$1" ]; then
    VERSION="$1"
    # 更新 manifest.yaml 中的版本号
    sed -i "s/version: [0-9.]*$/version: $VERSION/g" manifest.yaml
    echo -e "${GREEN}✅ 版本号已更新为: $VERSION${NC}"
else
    VERSION=$(grep "^version:" manifest.yaml | tail -1 | awk '{print $2}')
    echo -e "${GREEN}✅ 使用当前版本号: $VERSION${NC}"
fi

# 5. 打包
echo -e "\n${YELLOW}[5/5] 开始打包...${NC}"
OUTPUT_FILE="../ai_video_generation-v${VERSION}.difypkg"
rm -f "$OUTPUT_FILE"

# 在当前目录内打包，确保 manifest.yaml 在根目录
# 使用 -D 选项不存储目录条目，避免 Dify 解析错误
zip -rD "$OUTPUT_FILE" . \
    -x ".git/*" \
    -x "__pycache__/*" \
    -x "tools/__pycache__/*" \
    -x "provider/__pycache__/*" \
    -x "*.pyc" \
    -x ".gitignore" \
    -x "build.sh"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 打包成功！${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "📦 输出文件: ${YELLOW}$(realpath $OUTPUT_FILE)${NC}"
echo -e "📋 版本号: ${YELLOW}v${VERSION}${NC}"

# 显示打包内容
echo -e "\n📁 打包内容:"
unzip -l "$OUTPUT_FILE" | grep -v "^Archive:" | head -20

echo -e "\n${GREEN}下一步:${NC}"
echo -e "  1. 在 Dify 中上传 ${YELLOW}ai_video_generation-v${VERSION}.difypkg${NC}"
echo -e "  2. 或推送到 GitHub: git push && gh release create v${VERSION} $OUTPUT_FILE"

