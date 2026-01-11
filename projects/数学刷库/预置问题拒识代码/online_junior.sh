#!/bin/bash
today=$(date +%Y%m%d)
MODE="online"
LEVEL="junior"
# DATA_SUB_DIR="close/MultiJunior"
# DATA_SUB_DIR="close/junior1222"
DATA_SUB_DIR="riliu/1225"

EXEC_DIR="/mnt/pan8T/temp_xsji4/DataManagement"
DATA_DIR="${EXEC_DIR}/data/${MODE}/${DATA_SUB_DIR}"
LOG_DIR="${EXEC_DIR}/logs/${MODE}/${DATA_SUB_DIR}"
if [[ ! -d "${LOG_DIR}" ]]; then
    mkdir -p ${LOG_DIR}
fi

STEP="extract"
STEP="preprocess"
STEP="request"
STEP="response"
STEP="update"

LOG_FILE="${LOG_DIR}/${today}_${MODE}_${STEP}.txt"
METRICS_FILE="${DATA_DIR}/metrics_${STEP}.json"

MAX_WORKERS=1

if [[ "${STEP}" == "extract" ]]; then
    INPUT_DIR="${DATA_DIR}/raw"
    SAVE_DIR="${DATA_DIR}/${STEP}"
    STATE_FILE="${DATA_DIR}/_extract_state_is_null.json"  
    ENABLE_DUPLICATE_CHECK=true
elif [[ "${STEP}" == "preprocess" ]]; then
    INPUT_DIR="${DATA_DIR}/extract"
    SAVE_DIR="${DATA_DIR}/${STEP}"
    STATE_FILE="${DATA_DIR}/_preprocess_state_is_null.json"  
    ENABLE_PREFILTER=true   
    ENABLE_LATEX_CHECK=true
elif [[ "${STEP}" == "request" ]]; then
    INPUT_DIR="${DATA_DIR}/preprocess"
    SAVE_DIR="${DATA_DIR}/${STEP}"
    if [[ "${LEVEL}" == "primary" ]]; then
        PROMPT_TEMPLATE_FILE="${EXEC_DIR}/prompts/小学预置问题过滤_1224.txt"
    else
        PROMPT_TEMPLATE_FILE="${EXEC_DIR}/prompts/初中预置问题过滤_1126.txt"
    fi
    RENAME_PREFIX="xsji4_${today}_doubao-seed-1-6-thinking-250615_1114攻关_"
elif [[ "${STEP}" == "response" ]]; then
     INPUT_DIR="${DATA_DIR}/${STEP}/jsonl"
    SAVE_DIR="${DATA_DIR}/${STEP}/answer"
    METRICS_FILE="${DATA_DIR}/metrics_${STEP}.json"
elif [[ "${STEP}" == "update" ]]; then
    FILENAME="初中数学视频预置问题_补充186题.json"
    INPUT_DIR="${DATA_DIR}/raw/${FILENAME}"
    SAVE_DIR="${DATA_DIR}/update/${FILENAME}"
    RESULT_DIR="${DATA_DIR}/response/answer/${FILENAME}"
    STATE_FILE="${DATA_DIR}/_extract_state_is_null.json"
fi


show_help() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --mode <模式>          运行模式: offline, online (必需)"
    echo "  --step <步骤>          处理步骤: extract, preprocess, request, response, merge, update (必需)"
    echo "  --level <等级>         处理等级: sj, sp (默认: sj)"
    echo "  --input_dir <目录>     输入目录路径 (必需)"
    echo "  --save_dir <目录>      输出目录路径 (必需)"
    echo "  --result_dir <目录>    结果目录路径 (必需)"
    echo "  --max_workers <数量>   最大线程数 (默认: 8)"
    echo "  --enable_duplicate_check 启用重复检查"
    echo "  --enable_prefilter     启用预置问题过滤"
    echo "  --enable_latex_check   启用LaTeX格式检查"
    echo "  --prompt_template_file <文件> 提示模板文件路径"
    echo "  --rename_prefix <前缀>  重命名前缀"
    echo "  --question_file <文件> 预置问题文件路径"
    echo "  --state_file <文件> 状态文件路径"
    echo "  --metrics_file <文件>  指标文件路径"
    echo "  --help                 显示此帮助信息"
    echo ""
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case "$1" in
        --step)
            STEP="$2"
            shift 2
            ;;
        --mode)
            MODE="$2"
            shift 2
            ;;
        --level)
            LEVEL="$2"
            shift 2
            ;;
        --input_dir)
            INPUT_DIR="$2"
            shift 2
            ;;
        --save_dir)
            SAVE_DIR="$2"
            shift 2
            ;;
        --result_dir)
            RESULT_DIR="$2"
            shift 2
            ;;
        --max_workers)
            MAX_WORKERS="$2"
            shift 2
            ;;
        --enable_duplicate_check)
            ENABLE_DUPLICATE_CHECK=true
            shift
            ;;
        --enable_prefilter)
            ENABLE_PREFILTER=true
            shift
            ;;
        --enable_latex_check)
            ENABLE_LATEX_CHECK=true
            shift
            ;;
        --prompt_template_file)
            PROMPT_TEMPLATE_FILE="$2"
            shift 2
            ;;
        --rename_prefix)
            RENAME_PREFIX="$2"
            shift 2
            ;;
        --question_file)
            QUESTION_FILE="$2"
            shift 2
            ;;
        --state_file)
            STATE_FILE="$2"
            shift 2
            ;;
        --metrics_file)
            METRICS_FILE="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

# 检查必需参数
if [[ -z "$MODE" || -z "$STEP" || -z "$INPUT_DIR" || -z "$SAVE_DIR" ]]; then
    echo "错误: 缺少必需参数 --mode, --step, --input_dir 和 --save_dir"
    show_help
    exit 1
fi

# 构建命令
CMD="/root/miniforge3/bin/python3.12 ${EXEC_DIR}/manager.py \
    --step ${STEP} \
    --mode ${MODE} \
    --input_dir ${INPUT_DIR} \
    --save_dir ${SAVE_DIR} \
    --max_workers ${MAX_WORKERS}"

# 添加可选参数
if [[ -n "$LEVEL" ]]; then
    CMD="${CMD} \
    --level ${LEVEL}"
fi
if [[ "$ENABLE_DUPLICATE_CHECK" == true ]]; then
    CMD="${CMD} \
    --enable_duplicate_check true"
fi
if [[ "$ENABLE_PREFILTER" == true ]]; then
    CMD="${CMD} \
    --enable_prefilter true"
fi
if [[ "$ENABLE_LATEX_CHECK" == true ]]; then
    CMD="${CMD} \
    --enable_latex_check true"
fi

if [[ -n "$PROMPT_TEMPLATE_FILE" ]]; then
    CMD="${CMD} \
    --prompt_template_file ${PROMPT_TEMPLATE_FILE}"
fi

if [[ -n "$RENAME_PREFIX" ]]; then
    CMD="${CMD} \
    --rename_prefix ${RENAME_PREFIX}"
fi

if [[ -n "$QUESTION_FILE" ]]; then
    CMD="${CMD} \
    --question_file ${QUESTION_FILE}"
fi

if [[ -n "$METRICS_FILE" ]]; then
    CMD="${CMD} \
    --metrics_file ${METRICS_FILE}"
fi

if [[ -n "$STATE_FILE" ]]; then
    CMD="${CMD} \
    --state_file ${STATE_FILE}"
fi

if [[ -n "$RESULT_DIR" ]]; then
    CMD="${CMD} \
    --result_dir ${RESULT_DIR}"
fi


# 输出命令信息
echo "执行命令:"
echo "${CMD}"

nohup ${CMD} > ${LOG_FILE} 2>&1 &

echo "进程ID: $!"
echo "日志文件: ${LOG_FILE}"
