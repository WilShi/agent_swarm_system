#!/bin/bash
# Agent Swarm CLI 安装脚本

echo "🚀 安装 Agent Swarm CLI..."

# 获取项目目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 创建 bin 目录
mkdir -p ~/bin

# 创建启动脚本
cat > ~/bin/agent-swarm << 'EOF'
#!/bin/bash
# Agent Swarm CLI 启动器

PROJECT_DIR="PROJECT_DIR_PLACEHOLDER"
cd "$PROJECT_DIR"
python3 agent-swarm "$@"
EOF

# 替换项目目录
sed -i.bak "s|PROJECT_DIR_PLACEHOLDER|$PROJECT_DIR|g" ~/bin/agent-swarm
rm -f ~/bin/agent-swarm.bak

# 添加执行权限
chmod +x ~/bin/agent-swarm
chmod +x "$PROJECT_DIR/agent-swarm"

# 检查 PATH
if [[ ":$PATH:" != *":$HOME/bin:"* ]]; then
    echo ""
    echo "⚠️  需要将 ~/bin 添加到 PATH"
    echo ""
    echo "请运行以下命令（或添加到 ~/.zshrc 或 ~/.bashrc）:"
    echo 'export PATH="$HOME/bin:$PATH"'
    echo ""
fi

echo "✅ 安装完成！"
echo ""
echo "使用方法:"
echo "  agent-swarm --help"
echo "  agent-swarm list"
echo "  agent-swarm execute '帮我写个Python函数'"
echo "  agent-swarm interactive"
echo ""
