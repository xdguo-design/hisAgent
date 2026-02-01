@echo off
REM HIS开发Agent - Anaconda环境启动脚本

echo ========================================
echo HIS开发Agent - Anaconda环境启动
echo ========================================
echo.

REM 检查conda是否可用
where conda >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到conda命令，请确保已安装Anaconda或Miniconda
    echo 请访问 https://www.anaconda.com/download 下载安装
    pause
    exit /b 1
)

REM 检查环境是否存在
conda env list | findstr /C:"hisagent" >nul 2>nul
if %errorlevel% neq 0 (
    echo [信息] 未找到hisagent环境，正在创建...
    call conda env create -f environment.yml
    if %errorlevel% neq 0 (
        echo [错误] 创建环境失败
        pause
        exit /b 1
    )
    echo [成功] 环境创建完成
)

echo [信息] 激活hisagent环境...
call conda activate hisagent

echo [信息] 检查环境变量...
if not exist .env (
    echo [警告] 未找到.env文件
    echo [信息] 正在从.env.example复制...
    copy .env.example .env >nul
    echo [提示] 请编辑.env文件，填入必要的API密钥
    echo 必填项：ZHIPUAI_API_KEY
    echo.
    pause
)

echo [信息] 检查Python版本...
python --version

echo [信息] 检查依赖...
pip show fastapi >nul 2>nul
if %errorlevel% neq 0 (
    echo [警告] 依赖可能未完全安装，正在安装...
    pip install -r requirements.txt
)

echo.
echo ========================================
echo [成功] 环境准备完成！
echo ========================================
echo.
echo 启动服务...
python -m app.main

pause
