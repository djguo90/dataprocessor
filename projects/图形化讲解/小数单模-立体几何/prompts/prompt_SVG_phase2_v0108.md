# 角色设定 (Role & Profile)
你是一名资深的**小学立体几何可视化辅导专家**，同时精通前端可视化技术（HTML/SVG/JS）。

# 任务概述 (Task Objective)
你的核心任务是处理给定的试题与讲解脚本，生成可渲染的HTML/SVG/JS代码。

# 输入规范 (Input Specification)
输入为以下格式
【试题】
xxxxx
【讲解脚本】
<JSON>{"idx":4,"step":"步骤讲解","type":"分析","cont":"口播逐字稿内容","display_cont":"板书内容","mark_cont":[{"mark_target": "question_stem", "mark_target_idx": -1, "style": "circle", "cont": "标画题干内容"}],"visual_guide":"视觉操作指令"}</JSON>

# 输出规范 (Output Specification)

**严厉禁止**：在阶段二输出中，**绝对不要**重新输出或定义 `drawCuboid`, `drawCylinder` 等工具函数。默认这些函数已经存在于环境中。你只需要输出调用这些函数的逻辑代码，并且优先使用默认参数。

## 输出格式遵循以下样例:
【使用的JS函数】
```json
[
    "xxx"（只需要给出函数名，枚举范围：drawCuboid/drawCylinder/drawCone/drawArrow/drawDimensionLine/drawDirectLabel）
]
```
【每一步的输出】
```html
<script id="script_step_1/2/3/4/5/6/7"> // id需要输入中的idx保持一致
// 可以使用SVG原生的元素或者上述支持的JS函数，注意采用逐步叠加的方式绘图，每一步生成的图不主动消失
// 所有 step 脚本共享同一全局作用域；公共常量只允许在第一个 graph step 定义一次，后续 step 只能读取；如果必须新增变量，必须使用带 step 后缀的唯一命名（如 h_drop_s3、rx_s3）
</script>
```

## 输出要求

提取讲解脚本中所有 `visual_guide` 非空的语义块，生成 HTML/SVG/JS 代码块。

### 核心渲染逻辑：斜二测画法 (Oblique Projection)或正视图画法 (Front/Side Projection with Depth)

#### 斜二测画法

此时所有的图形绘制基于 **X/Y平面为正面**，**Z轴为深度** 的投影转换。

*   **3D 坐标定义**：
    *   $x$ 轴：水平向右（宽度）。
    *   $y$ 轴：垂直向上（高度）。
    *   $z$ 轴：垂直屏幕（深度）。**注意**：为了视觉上的自然，通常规定 Z 轴的正方向或负方向向右上方倾斜。
*   **投影公式**（将 3D 点 $(x, y, z)$ 转换为 2D 视图点 $(x', y')$）：
    *   深度系数通常取 $0.5$（斜二测标准）。
    *   $x' = x + z \times 0.5 \times \cos(45^\circ)$
    *   $y' = y + z \times 0.5 \times \sin(45^\circ)$
*   **SVG 坐标适配**：
    *   SVG 的 $y$ 轴原点在左上角且向下增加。
    *   需要对逻辑 $y'$ 取反并加上画布中心偏移。
    *   最终公式：
        *   `svg_x = center_x + x'`
        *   `svg_y = center_y - y'`

#### 正视图画法

此时图形绘制基于 **X/Y平面为基准**，但 **Z轴（深度）会按照系数 $k$ 叠加到垂直方向**。这意味着物体“往里走”在视觉上会表现为“往上跑”。

*   **3D 坐标定义**：
    *   $x$ 轴：水平向右（宽度）。
    *   $y$ 轴：垂直向上（高度/海拔）。
    *   $z$ 轴：垂直屏幕向内（深度）。
*   **投影公式**（将 3D 点 $(x, y, z)$ 转换为 2D 视图点 $(x', y')$）：
    *   **深度系数 ($k$)**：默认为 $0.5$。这决定了“纵深感”的强弱。
    *   $x' = x$ （X 轴不受深度影响，保持水平）。
    *   $y' = y + z \times k$ （逻辑高度 = 实际高度 + 压缩后的深度）。
*   **SVG/Canvas 坐标适配**：
    *   屏幕坐标系 $y$ 轴向下增加，因此需对 $y'$ 取反。
    *   **代码对应公式**：
        *   `px = centerX + x`
        *   `py = centerY - (y + z * k)`


### 代码架构要求 (保持模块化)

1.  **配置区**：定义画布中心、缩放比例、斜二测角度。
2.  **几何定义**：顶点坐标以 `{x, y, z}` 格式定义。例如正方体正面是 $z=0$，背面是 $z=4$。
3.  **工具函数**：`Projections`, `drawCuboid`, `drawCylinder` 等。

### 绘图要求

1. **环境假设**：假设所有工具函数（`drawCuboid`, `Projections` 等）已在全局作用域定义，**严禁**在输出中重新定义这些函数。
2. **可用工具**：代码中可以使用工具函数或者SVG原生绘图工具（例如可以使用<text>, <path>, <line>, <rect>, <circle>, <ellipse>, <polyline>等）。
3. **ID 语义化与一致性**：
   - 创建图形时必须指定语义化的 `id`（如 `cube-main`, `arrow-step1`）。
   - 修改图形（如高亮）时，必须利用工具函数的 ID 命名规则准确获取元素（例如 `drawCuboid` 生成的顶面 ID 必然是 `${id}-face-top`）。
4. **布局计算（Layout Calculation）**：
   - **禁止硬编码**：不要在代码中大量使用如 `x: 350` 这样的魔术数字。
   - **响应式计算**：必须在代码开头定义 `cx` (中心X), `cy` (中心Y), `baseSize` 等常量。后续坐标应基于这些常量计算（如 `x: cx - baseSize/2`）。
   - **防重叠逻辑**：涉及多个物体时，必须根据投影宽度/高度计算 `gap`，防止视觉重叠。
   - **尺寸线布局**：绘制尺寸线时，需要尽可能分布在不同的边上。
5. **增量绘制**：
   - 后续步骤（Step N）是在 Step N-1 的基础上运行的。
   - 不要清除画布，除非题目要求重置场景。
   - 利用 `document.getElementById` 获取之前步骤的元素进行修改（变色、隐藏）。

### 绘图空间布局要求

1. 尽量不要使用drawArrow函数，如果使用，只能使用水平方向的箭头。
2. 对于长方体或正方体，必须使用斜二测画法，对于圆柱体，圆锥体，必须使用正视图画法。

### 默认样式配置及核心工具函数

以下是绘制几何图形的默认配置以及核心工具函数，可供调用。

#### 默认配置
```javascript
// =====================
// 1) 几何体统一默认样式
// =====================
const DEFAULT_STYLES = {
    // --- 边线 (visible edges) ---
    edgeStroke: "#333",        // 边线颜色
    edgeWidth: 2,              // 边线宽度
    edgeOpacity: 1,            // 边线透明度
    edgeLinecap: "round",      // butt | round | square
    edgeLinejoin: "round",     // miter | round | bevel
    edgeMiterlimit: 4,         // join=miter 时的尖角限制

    // --- 不可见线 (hidden edges) ---
    dashArray: "5,5",          // 兼容旧字段：不可见线默认虚线样式（你现有代码用这个）
    hiddenDashArray: "5,5",    // 推荐新字段：专门给 hidden 用
    hiddenStroke: "#333",      // 可设置为更淡，比如 "#666"
    hiddenWidth: null,         // null 表示沿用 edgeWidth；也可单独设置
    hiddenOpacity: 1,          // 可设置为 0.8/0.6 更像工程制图

    // --- 面 (faces) ---
    faceFill: "rgba(0,0,0,0)", // 面填充色 (默认透明)
    faceOpacity: 1,            // 面整体透明度（可配合 faceFill 使用）
    faceStroke: "none",        // 面描边颜色（默认不描边）
    faceStrokeWidth: 0,        // 面描边宽度
    faceStrokeOpacity: 1,      // 面描边透明度

    // --- 顶点 (vertices) ---
    showVertices: false,       // 是否显示顶点
    vertexRadius: 4,           // 顶点半径
    vertexFill: "#333",        // 顶点填充
    vertexStroke: "none",      // 顶点描边
    vertexStrokeWidth: 0,      // 顶点描边宽度
    vertexOpacity: 1,          // 顶点透明度

    // --- 圆类细分 (cylinder/cone smoothing) ---
    segments: 72,              // 圆周分段数（圆柱/圆锥默认可读这个）

    // --- 调试辅助 ---
    showCenters: false,        // 是否显示几何中心点（圆柱/圆锥等）
    centerRadius: 3,
    centerFill: "#e11d48",     // 调试用醒目色
    debug: false               // true 时可让你的绘制函数加额外辅助元素/更醒目样式
};

// =====================
// 2) 标注/箭头统一默认样式（建议）
//   适用于 drawArrow / drawDimensionLine / drawCurlyBraceLabel / drawDirectLabel
// =====================
const DEFAULT_ANNOTATION_STYLES = {
    // --- 线条/箭头通用 ---
    stroke: "#333",
    strokeWidth: 1.5,
    opacity: 1,
    linecap: "round",
    linejoin: "round",
    dashArray: null,           // null 表示实线；如 "4,4"

    fill: "#333",              // 箭头/实体符号填充色

    // --- 文字通用 ---
    fontSize: 14,
    fontFamily: "Arial, sans-serif",
    textFill: "#333",

    // 文字光晕（你现在是白描边 halo）
    haloStroke: "white",
    haloWidth: 3,
    haloLinejoin: "round",

    // 可选：强背景（比 halo 更“遮挡线条”）
    textBackground: false,
    textBgFill: "white",
    textBgOpacity: 1,
    textBgPadding: 3,          // 背景 padding（需要你在代码里用 <rect> 实现）

    // --- 箭头参数（arrow/dim/direct 都可能用到） ---
    arrowSize: 8,
    arrowWidth: 3,

    // --- 尺寸标注特有（drawDimensionLine） ---
    textOffset: 10,
    gap: 5,
    ext_length: 10,

    // --- 花括号特有（drawCurlyBraceLabel） ---
    braceDepth: 10,
    braceGap: 15,

    // --- 原地/辅助线标注特有（drawDirectLabel） ---
    directDashArray: "4,4",
    directArrowStart: true,
    directArrowEnd: true
};
```

#### 投影函数（二维三维图形通用）
```javascript
const Projections = {
    /** 
     * 策略 A: 斜二测 (数学标准，适合组合)
     * 特点：X轴随Z轴偏移，圆是歪的
     */
    OBLIQUE: function(x, y, z, config) {
        const { centerX, centerY, k = 0.5, angle = Math.PI / 4 } = config;
        return {
            px: centerX + x + z * k * Math.cos(angle),
            py: centerY - (y + z * k * Math.sin(angle))
        };
    },

    /** 
     * 策略 B: 正视图 (视觉优化，适合单独圆柱)
     * 特点：X轴不变，圆是平的
     */
    FRONT: function(x, y, z, config) {
        const { centerX, centerY, k = 0.3 } = config;
        return {
            px: centerX + x,
            py: centerY - (y + z * k)
        };
    }
};
```

#### 自动位置调整
```javascript
/**
 * 全局函数：自动调整带有 .smart-label 类的文本位置，使其不遮挡几何图形。
 * 
 * 原理：
 * 1. 找到所有几何图形（path, line, polygon, rect）。
 * 2. 遍历所有智能标签。
 * 3. 检测标签与几何图形是否重叠。
 * 4. 如果重叠，分别模拟“法向”、“切向+”、“切向-”三个方向，谁先找到空位且移动距离最短，就选谁。
 * 5. 重复尝试，直到不重叠或达到最大尝试次数。
 * 
 * @param {SVGElement} svgRoot - 根 SVG 元素
 */
function autoAvoidOverlap(svgRoot, opts = {}) {
  if (!svgRoot) svgRoot = window.mainSvg;
  if (!svgRoot) return;

  // ===== 可调参数（你也可以在调用时覆盖）=====
  const MAX_STEPS = opts.MAX_STEPS ?? 28;              // 每个方向最多尝试步数
  const STEP_SIZE = opts.STEP_SIZE ?? 4;               // 每步距离(px)
  const PADDING   = opts.PADDING   ?? 2;               // 碰撞缓冲(px)
  const PASSES    = opts.PASSES    ?? 2;               // 多轮迭代，提升多标签稳定性

  // 切向最大搜索距离：关键！默认给大一些，避免 dataset.limit 太小导致“上下走不通”
  const TANGENT_MAX_DIST = opts.TANGENT_MAX_DIST ?? 120;

  // 法向软上限：超过这个距离仍可走，但会被额外惩罚，避免“往右跑飞”
  const NORMAL_SOFT_LIMIT = opts.NORMAL_SOFT_LIMIT ?? 28;   // px
  const NORMAL_OVER_PENALTY = opts.NORMAL_OVER_PENALTY ?? 1.6; // 越大越不愿意跑远

  // 各方向基础惩罚系数（越小越优先）
  const PENALTY_NORMAL      = opts.PENALTY_NORMAL      ?? 1.0;
  const PENALTY_TANGENT     = opts.PENALTY_TANGENT     ?? 0.95;  // 让“上下”略优先一点
  const PENALTY_NORMAL_OPP  = opts.PENALTY_NORMAL_OPP  ?? 1.15;
  const PENALTY_DIAG        = opts.PENALTY_DIAG        ?? 1.05;

  // ===== 1) 障碍物：几何 + 非 smart-label 的 text（比如 S=50cm²）=====
  const obstacles = Array.from(
    svgRoot.querySelectorAll("path, polygon, line, rect, circle, ellipse, text:not(.smart-label)")
  );
  const labels = Array.from(svgRoot.querySelectorAll("text.smart-label"));
  if (!labels.length) return;

  const isVisibleEl = (el) => {
    const style = window.getComputedStyle(el);
    if (!style) return true;
    if (style.display === "none" || style.visibility === "hidden") return false;
    if (parseFloat(style.opacity || "1") <= 0) return false;
    return true;
  };

  const rectsOverlap = (a, b) => !(
    a.x > b.x + b.width ||
    a.x + a.width < b.x ||
    a.y > b.y + b.height ||
    a.y + a.height < b.y
  );

  const getInflatedBBox = (el, pad) => {
    const bb = el.getBBox();
    let sw = 0;
    const swAttr = el.getAttribute("stroke-width");
    if (swAttr != null) sw = parseFloat(swAttr) || 0;
    const inflate = pad + sw * 0.5;
    return {
      x: bb.x - inflate,
      y: bb.y - inflate,
      width: bb.width + inflate * 2,
      height: bb.height + inflate * 2
    };
  };

  // ===== 2) 关键修复：按 text-anchor / dominant-baseline 算虚拟 Rect =====
  const makeTextRectCalculator = (textEl, w, h) => {
    const anchor = (textEl.getAttribute("text-anchor") || "middle").trim();
    const baseline = (textEl.getAttribute("dominant-baseline") || "middle").trim();

    // halo 也算进碰撞（文字描边）
    const haloW = parseFloat(textEl.getAttribute("stroke-width") || "0") || 0;
    const inflate = PADDING + haloW * 0.5;

    return (x, y) => {
      let rx;
      if (anchor === "start") rx = x;
      else if (anchor === "end") rx = x - w;
      else rx = x - w / 2;

      let ry;
      if (baseline === "middle" || baseline === "central") ry = y - h / 2;
      else if (baseline === "hanging" || baseline === "text-before-edge") ry = y;
      else if (baseline === "text-after-edge") ry = y - h;
      else ry = y - h / 2;

      return {
        x: rx - inflate,
        y: ry - inflate,
        width: w + inflate * 2,
        height: h + inflate * 2
      };
    };
  };

  const checkCollision = (vrect, ignoreGroup, placedLabelRects) => {
    // 几何/文字障碍物
    for (const shape of obstacles) {
      if (!isVisibleEl(shape)) continue;
      if (ignoreGroup && ignoreGroup.contains(shape)) continue;
      const r = getInflatedBBox(shape, PADDING);
      if (rectsOverlap(vrect, r)) return true;
    }
    // 已安置标签（实现标签互避）
    for (const item of placedLabelRects) {
      if (ignoreGroup && item.group && ignoreGroup === item.group) continue;
      if (rectsOverlap(vrect, item.rect)) return true;
    }
    return false;
  };

  const norm2 = (x, y) => {
    const L = Math.hypot(x, y);
    if (L < 1e-9) return { x: 0, y: 0 };
    return { x: x / L, y: y / L };
  };

  // ===== 3) 多轮迭代处理多标签 =====
  for (let pass = 0; pass < PASSES; pass++) {
    let movedAny = false;
    const placed = []; // 本轮已放置标签的 rect，后续标签要避开它们

    for (const textEl of labels) {
      if (!isVisibleEl(textEl)) continue;

      // 来自 drawDimensionLine 的向量信息
      const nx0 = parseFloat(textEl.dataset.nx || "0");
      const ny0 = parseFloat(textEl.dataset.ny || "1");
      const ux0 = parseFloat(textEl.dataset.ux || "1");
      const uy0 = parseFloat(textEl.dataset.uy || "0");

      const ox = parseFloat(textEl.dataset.ox || textEl.getAttribute("x") || "0");
      const oy = parseFloat(textEl.dataset.oy || textEl.getAttribute("y") || "0");

      // 你原先的 limit 很小，这里把它当“建议值”，实际最大用 TANGENT_MAX_DIST
      const rawLimit = parseFloat(textEl.dataset.limit);
      const tangentMaxDist = Math.max(
        isFinite(rawLimit) ? rawLimit : 0,
        TANGENT_MAX_DIST
      );

      const parentId = textEl.dataset.parentId;
      const myGroup = parentId ? document.getElementById(parentId) : (textEl.closest("g") || null);

      // 先恢复原点测尺寸
      textEl.setAttribute("x", ox);
      textEl.setAttribute("y", oy);
      const baseBox = textEl.getBBox();
      const w = baseBox.width;
      const h = baseBox.height;

      const calcRect = makeTextRectCalculator(textEl, w, h);

      // 起点如果不撞，仍然要加入 placed（避免其他标签盖上来）
      const startRect = calcRect(ox, oy);

      const N  = norm2(nx0, ny0);
      const U  = norm2(ux0, uy0);

      // 候选方向：法向±、切向±、斜向（法+切 的组合）
      const dirs = [
        { name: "normal",     vx: N.x,        vy: N.y,        maxDist: null,          basePenalty: PENALTY_NORMAL },
        { name: "tangent+",   vx: U.x,        vy: U.y,        maxDist: tangentMaxDist, basePenalty: PENALTY_TANGENT },
        { name: "tangent-",   vx: -U.x,       vy: -U.y,       maxDist: tangentMaxDist, basePenalty: PENALTY_TANGENT },
        { name: "normalOpp",  vx: -N.x,       vy: -N.y,       maxDist: null,          basePenalty: PENALTY_NORMAL_OPP },

        // 斜向：更容易找到“近的空位”
        (() => { const v = norm2(N.x + U.x, N.y + U.y); return { name:"diag1", vx:v.x, vy:v.y, maxDist: 120, basePenalty: PENALTY_DIAG }; })(),
        (() => { const v = norm2(N.x - U.x, N.y - U.y); return { name:"diag2", vx:v.x, vy:v.y, maxDist: 120, basePenalty: PENALTY_DIAG }; })(),
        (() => { const v = norm2(-N.x + U.x, -N.y + U.y); return { name:"diag3", vx:v.x, vy:v.y, maxDist: 120, basePenalty: PENALTY_DIAG }; })(),
        (() => { const v = norm2(-N.x - U.x, -N.y - U.y); return { name:"diag4", vx:v.x, vy:v.y, maxDist: 120, basePenalty: PENALTY_DIAG }; })(),
      ].filter(d => Math.hypot(d.vx, d.vy) > 1e-6);

      const findBestInDir = (dir) => {
        let best = null;

        for (let i = 0; i <= MAX_STEPS; i++) {
          const dist = i * STEP_SIZE;
          if (dir.maxDist != null && dist > dir.maxDist) break;

          const x = ox + dir.vx * dist;
          const y = oy + dir.vy * dist;
          const vrect = calcRect(x, y);

          if (checkCollision(vrect, myGroup, placed)) continue;

          // 代价：基础距离 * 惩罚
          // 对“normal”加入跑远惩罚，避免向右走太多
          let cost = dist * dir.basePenalty;

          if (dir.name === "normal" && dist > NORMAL_SOFT_LIMIT) {
            cost += (dist - NORMAL_SOFT_LIMIT) * NORMAL_OVER_PENALTY;
          }

          // 找到就先记录，但继续看看同方向有没有更低 cost（通常 i 越小越好）
          if (!best || cost < best.cost) {
            best = { x, y, rect: vrect, steps: i, cost, name: dir.name };
          }

          // 同方向 i 越大通常越差，这里可直接 break 加速
          // 但为了稳一点（考虑 normal 跑远惩罚），我们不 break，让它有机会在同方向选更合理的点
        }

        return best;
      };

      // 如果起点不撞：仍可能需要微调以避开“标签-标签”，所以也纳入候选
      let bestOverall = null;
      if (!checkCollision(startRect, myGroup, placed)) {
        bestOverall = { x: ox, y: oy, rect: startRect, steps: 0, cost: 0, name: "stay" };
      }

      for (const dir of dirs) {
        const cand = findBestInDir(dir);
        if (!cand) continue;
        if (!bestOverall || cand.cost < bestOverall.cost) bestOverall = cand;
      }

      if (!bestOverall) {
        // 全都堵死：保持原位并落位
        placed.push({ group: myGroup, rect: startRect, el: textEl });
        continue;
      }

      // 应用最佳位置
      if (bestOverall.steps > 0) movedAny = true;

      textEl.setAttribute("x", bestOverall.x);
      textEl.setAttribute("y", bestOverall.y);

      // 背景框同步（避免你之前 s 未定义）
      const bgEl =
        (parentId && document.getElementById(`${parentId}-text-bg`)) ||
        document.getElementById(`${textEl.id}-bg`) ||
        document.getElementById(`${textEl.id}-text-bg`);

      if (bgEl && bgEl.tagName.toLowerCase() === "rect") {
        const bb = textEl.getBBox();
        const pad = 3;
        bgEl.setAttribute("x", bb.x - pad);
        bgEl.setAttribute("y", bb.y - pad);
        bgEl.setAttribute("width", bb.width + pad * 2);
        bgEl.setAttribute("height", bb.height + pad * 2);
      }

      // 记录最终 rect，供后续标签避让
      const finalRect = calcRect(bestOverall.x, bestOverall.y);
      placed.push({ group: myGroup, rect: finalRect, el: textEl });
    }

    if (!movedAny) break;
  }
}
```

#### 长方体（包含正方体）
```javascript
/**
 * 绘制长方体 (支持自定义投影策略)
 *
 * @param {Object} config - 长方体配置对象
 * @param {string} config.id - SVG 元素的唯一 ID 前缀
 * @param {number} [config.x=0] - 左下前（靠近观察者）顶点 x (3D)
 * @param {number} [config.y=0] - 左下前（靠近观察者）顶点 y (3D)
 * @param {number} [config.z=0] - 左下前（靠近观察者）顶点 z (3D)
 * @param {number} config.w - 宽 (X轴跨度)
 * @param {number} config.h - 高 (Y轴跨度)
 * @param {number} config.d - 深 (Z轴跨度)
 * @param {number} config.centerX - 画布中心点 X（供投影函数使用）
 * @param {number} config.centerY - 画布中心点 Y（供投影函数使用）
 * @param {Function} [config.projectFn] - 投影函数 (例如 Projections.OBLIQUE)
 * @param {Object} [config.styles] - 样式覆盖（基于 DEFAULT_STYLES）
 * @returns {SVGGElement} g
 */
function drawCuboid(config) {
    const {
        id,
        x = 0, y = 0, z = 0,
        w, h, d,
        styles = {},
        projectFn = Projections.OBLIQUE
    } = config;

    if (!id) throw new Error("drawCuboid: config.id is required.");
    if (w == null || h == null || d == null) throw new Error("drawCuboid: config.w/h/d are required.");

    const svgTarget = (typeof svg !== "undefined" ? svg : window.mainSvg);
    if (!svgTarget) throw new Error("drawCuboid: global svg not found.");

    const s = { ...DEFAULT_STYLES, ...styles };

    // ---------- 样式应用：边/隐藏边/面/点 ----------
    const applyVisibleStroke = (el) => {
        el.setAttribute("stroke", s.edgeStroke);
        el.setAttribute("stroke-width", s.edgeWidth);
        if (s.edgeOpacity != null) el.setAttribute("stroke-opacity", s.edgeOpacity);
        if (s.edgeLinecap) el.setAttribute("stroke-linecap", s.edgeLinecap);
        if (s.edgeLinejoin) el.setAttribute("stroke-linejoin", s.edgeLinejoin);
        if (s.edgeLinejoin === "miter" && s.edgeMiterlimit != null) {
            el.setAttribute("stroke-miterlimit", s.edgeMiterlimit);
        }
    };

    const applyHiddenStroke = (el) => {
        const hs = (s.hiddenStroke != null) ? s.hiddenStroke : s.edgeStroke;
        const hw = (s.hiddenWidth != null) ? s.hiddenWidth : s.edgeWidth;
        const ho = (s.hiddenOpacity != null) ? s.hiddenOpacity : s.edgeOpacity;
        const hd = (s.hiddenDashArray != null) ? s.hiddenDashArray : s.dashArray;

        el.setAttribute("stroke", hs);
        el.setAttribute("stroke-width", hw);
        if (ho != null) el.setAttribute("stroke-opacity", ho);
        if (s.edgeLinecap) el.setAttribute("stroke-linecap", s.edgeLinecap);
        if (s.edgeLinejoin) el.setAttribute("stroke-linejoin", s.edgeLinejoin);
        if (s.edgeLinejoin === "miter" && s.edgeMiterlimit != null) {
            el.setAttribute("stroke-miterlimit", s.edgeMiterlimit);
        }
        if (hd) el.setAttribute("stroke-dasharray", hd);
    };

    const applyFaceStyle = (poly) => {
        poly.setAttribute("fill", s.faceFill);
        if (s.faceOpacity != null) poly.setAttribute("fill-opacity", s.faceOpacity);

        if (s.faceStroke && s.faceStroke !== "none" && (s.faceStrokeWidth || 0) > 0) {
            poly.setAttribute("stroke", s.faceStroke);
            poly.setAttribute("stroke-width", s.faceStrokeWidth);
            if (s.faceStrokeOpacity != null) poly.setAttribute("stroke-opacity", s.faceStrokeOpacity);
            if (s.edgeLinecap) poly.setAttribute("stroke-linecap", s.edgeLinecap);
            if (s.edgeLinejoin) poly.setAttribute("stroke-linejoin", s.edgeLinejoin);
        } else {
            poly.setAttribute("stroke", "none");
        }
    };

    const applyVertexStyle = (c) => {
        c.setAttribute("r", s.vertexRadius);
        c.setAttribute("fill", s.vertexFill);
        if (s.vertexOpacity != null) c.setAttribute("fill-opacity", s.vertexOpacity);

        if (s.vertexStroke && s.vertexStroke !== "none" && (s.vertexStrokeWidth || 0) > 0) {
            c.setAttribute("stroke", s.vertexStroke);
            c.setAttribute("stroke-width", s.vertexStrokeWidth);
        } else {
            c.setAttribute("stroke", "none");
        }
    };

    // ---------- 1) 8 个顶点（3D） ----------
    // 约定：0-3 为前表面(z)，4-7 为后表面(z+d)
    // 0: 左下前, 1: 右下前, 2: 右上前, 3: 左上前
    // 4: 左下后, 5: 右下后, 6: 右上后, 7: 左上后
    const v3d = [
        [x,   y,   z],     [x+w, y,   z],     [x+w, y+h, z],     [x,   y+h, z],
        [x,   y,   z+d],   [x+w, y,   z+d],   [x+w, y+h, z+d],   [x,   y+h, z+d]
    ];

    // ---------- 2) 投影到 2D ----------
    const pts = v3d.map(v => projectFn(v[0], v[1], v[2], config));

    // ---------- 3) 面拓扑（先给“常识顺序”，后面会自动修正 winding） ----------
    const facesTopology = [
        { name: "front",  idx: [0, 1, 2, 3] },
        { name: "back",   idx: [4, 5, 6, 7] },
        { name: "right",  idx: [1, 2, 6, 5] },
        { name: "left",   idx: [0, 4, 7, 3] },
        { name: "top",    idx: [3, 7, 6, 2] },
        { name: "bottom", idx: [0, 1, 5, 4] }
    ];

    // ---------- 4) 自动修正 face winding + 再算 faceVisibility ----------
    const v3sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
    const v3dot = (a, b) => a[0]*b[0] + a[1]*b[1] + a[2]*b[2];
    const v3cross = (a, b) => [
        a[1]*b[2] - a[2]*b[1],
        a[2]*b[0] - a[0]*b[2],
        a[0]*b[1] - a[1]*b[0],
    ];
    const v3len = (a) => Math.sqrt(a[0]*a[0] + a[1]*a[1] + a[2]*a[2]);
    const v3norm = (a) => {
        const L = v3len(a);
        if (L < 1e-12) return [0, 0, 0];
        return [a[0]/L, a[1]/L, a[2]/L];
    };

    const faceNormal3D = (idx) => {
        const A = v3d[idx[0]];
        const B = v3d[idx[1]];
        const C = v3d[idx[2]];
        return v3cross(v3sub(B, A), v3sub(C, A));
    };

    // 期望“朝外”的法线方向（基于 v3d 编号约定）
    const EXPECT_OUTWARD = {
        front:  [0, 0, -1],
        back:   [0, 0,  1],
        right:  [1, 0,  0],
        left:   [-1,0,  0],
        top:    [0, 1,  0],
        bottom: [0,-1,  0],
    };

    // 4.1) 先修正 winding：让每个面的法线与“期望外法线”同向
    facesTopology.forEach(face => {
        const exp = EXPECT_OUTWARD[face.name];
        if (!exp) return;
        const n = faceNormal3D(face.idx);
        if (v3dot(n, exp) < 0) {
            face.idx = [...face.idx].reverse();
        }
    });

    // 4.2) 估计 viewDir（对 OBLIQUE/FRONT 这类线性投影很稳）
    const estimateViewDir = () => {
        const eps = 1;
        const p0 = projectFn(0, 0, 0, config);
        const px = projectFn(eps, 0, 0, config);
        const py = projectFn(0, eps, 0, config);
        const pz = projectFn(0, 0, eps, config);

        const row1 = [(px.px - p0.px)/eps, (py.px - p0.px)/eps, (pz.px - p0.px)/eps];
        const row2 = [(px.py - p0.py)/eps, (py.py - p0.py)/eps, (pz.py - p0.py)/eps];

        const v = v3cross(row1, row2);
        const vn = v3norm(v);
        return (v3len(vn) < 1e-9) ? [0, 0, -1] : vn;
    };

    const viewDir0 = estimateViewDir();

    // 4.3) 用 2D 面积符号做一次“手性/正负号”校准（避免 viewDir 符号不确定）
    const faceArea2D = (idx) => {
        let area = 0;
        for (let i = 0; i < idx.length; i++) {
            const p1 = pts[idx[i]];
            const p2 = pts[idx[(i + 1) % idx.length]];
            area += (p1.px * p2.py - p2.px * p1.py);
        }
        return area;
    };

    // 选择最佳组合：flipViewDir? 以及 areaSign(neg/pos) 与 3D 可见性的一致性
    const combos = [
        { flipView: false, areaNegIsFront: true  },
        { flipView: false, areaNegIsFront: false },
        { flipView: true,  areaNegIsFront: true  },
        { flipView: true,  areaNegIsFront: false },
    ];

    const EPS_AREA = 1e-6;
    const EPS_DOT  = 1e-6;

    let best = { score: -1, flipView: false, areaNegIsFront: true };
    combos.forEach(c => {
        const vd = c.flipView ? [-viewDir0[0], -viewDir0[1], -viewDir0[2]] : viewDir0;
        let score = 0;
        let total = 0;

        facesTopology.forEach(face => {
            const n = v3norm(faceNormal3D(face.idx));
            if (v3len(n) < 1e-9) return;

            const a = faceArea2D(face.idx);
            if (Math.abs(a) < EPS_AREA) return;

            const vis3 = v3dot(n, vd) > EPS_DOT;
            const vis2 = c.areaNegIsFront ? (a < 0) : (a > 0);

            score += (vis3 === vis2) ? 1 : 0;
            total += 1;
        });

        // 用一致比例评分（避免 total 少导致误判）
        const ratio = total ? (score / total) : 0;
        if (ratio > best.score) best = { ...c, score: ratio };
    });

    const viewDir = best.flipView ? [-viewDir0[0], -viewDir0[1], -viewDir0[2]] : viewDir0;

    const faceVisibility = {};
    facesTopology.forEach(face => {
        const n = v3norm(faceNormal3D(face.idx));
        faceVisibility[face.name] = v3dot(n, viewDir) > EPS_DOT;
    });

    // ---------- 5) 组 ----------
    const g = document.createElementNS(SVG_NS, "g");
    g.setAttribute("id", id);

    // ---------- 6) 先绘制面（保证边在线上层） ----------
    facesTopology.forEach(face => {
        const poly = document.createElementNS(SVG_NS, "polygon");
        poly.setAttribute("id", `${id}-face-${face.name}`);
        poly.setAttribute("points", face.idx.map(i => `${pts[i].px},${pts[i].py}`).join(" "));
        applyFaceStyle(poly);
        g.appendChild(poly);
    });

    // ---------- 7) 绘制边（自动虚实线） ----------
    const edgesDefinitions = [
        [0, 1], [1, 2], [2, 3], [3, 0], // 前圈
        [4, 5], [5, 6], [6, 7], [7, 4], // 后圈
        [0, 4], [1, 5], [2, 6], [3, 7]  // 连接棱
    ];

    edgesDefinitions.forEach((edgeIndices, i) => {
        const [u, v] = edgeIndices;

        // 查找共享此边的面（相邻顶点）
        const sharedFaces = facesTopology.filter(f => {
            const idxList = f.idx;
            const posU = idxList.indexOf(u);
            const posV = idxList.indexOf(v);
            if (posU === -1 || posV === -1) return false;
            const len = idxList.length;
            return (posU === (posV + 1) % len) || (posV === (posU + 1) % len);
        });

        // 任一共享面可见 => 边可见
        const isVisible = sharedFaces.some(f => faceVisibility[f.name]);

        const line = document.createElementNS(SVG_NS, "line");
        line.setAttribute("id", `${id}-edge-${i}`);
        line.setAttribute("x1", pts[u].px);
        line.setAttribute("y1", pts[u].py);
        line.setAttribute("x2", pts[v].px);
        line.setAttribute("y2", pts[v].py);

        if (isVisible) applyVisibleStroke(line);
        else applyHiddenStroke(line);

        g.appendChild(line);
    });

    // ---------- 8) 顶点（可选） ----------
    if (s.showVertices) {
        pts.forEach((p, i) => {
            const circle = document.createElementNS(SVG_NS, "circle");
            circle.setAttribute("id", `${id}-vertex-${i}`);
            circle.setAttribute("cx", p.px);
            circle.setAttribute("cy", p.py);
            applyVertexStyle(circle);
            g.appendChild(circle);
        });
    }

    // ---------- 9) 中心点（可选，带 id） ----------
    if (s.showCenters) {
        const pc = projectFn(x + w/2, y + h/2, z + d/2, config);
        const c = document.createElementNS(SVG_NS, "circle");
        c.setAttribute("id", `${id}-center`);
        c.setAttribute("cx", pc.px);
        c.setAttribute("cy", pc.py);
        c.setAttribute("r", s.centerRadius || 3);
        c.setAttribute("fill", s.centerFill || "#e11d48");
        g.appendChild(c);
    }

    svgTarget.appendChild(g);
    return g;
}
```

#### 圆柱体
```javascript
/**
 * 绘制圆柱体 (支持自定义投影策略)
 * 
 * @param {Object} config - 配置对象
 * @param {string} config.id - SVG 元素 ID 前缀
 * @param {number} config.x - 底面圆心 x 坐标 (3D)
 * @param {number} config.y - 底面圆心 y 坐标 (3D)
 * @param {number} config.z - 底面圆心 z 坐标 (3D)
 * @param {number} config.r - 圆柱半径
 * @param {number} config.h - 圆柱高度
 * @param {number} config.centerX - 画布中心点 X
 * @param {number} config.centerY - 画布中心点 Y
 * @param {Function} [config.projectFn=Projections.FRONT] - 投影函数（圆柱/圆锥默认 FRONT）
 * @param {Object} [config.styles] - 样式配置
 */
function drawCylinder(config) {
    const {
        id,
        x, y, z, r, h,
        projectFn = Projections.FRONT,
        styles = {},
    } = config;

    const s = { ...DEFAULT_STYLES, ...styles };
    const segments = (typeof s.segments === "number" && s.segments >= 12) ? s.segments : 72;

    // ---- 样式应用工具：可见/不可见边、面 ----
    const applyVisibleStroke = (el) => {
        el.setAttribute("stroke", s.edgeStroke);
        el.setAttribute("stroke-width", s.edgeWidth);
        if (s.edgeOpacity != null) el.setAttribute("stroke-opacity", s.edgeOpacity);
        if (s.edgeLinecap) el.setAttribute("stroke-linecap", s.edgeLinecap);
        if (s.edgeLinejoin) el.setAttribute("stroke-linejoin", s.edgeLinejoin);
        if (s.edgeLinejoin === "miter" && s.edgeMiterlimit != null) {
            el.setAttribute("stroke-miterlimit", s.edgeMiterlimit);
        }
    };

    const applyHiddenStroke = (el) => {
        const hs = (s.hiddenStroke != null) ? s.hiddenStroke : s.edgeStroke;
        const hw = (s.hiddenWidth != null) ? s.hiddenWidth : s.edgeWidth;
        const ho = (s.hiddenOpacity != null) ? s.hiddenOpacity : s.edgeOpacity;
        const hd = (s.hiddenDashArray != null) ? s.hiddenDashArray : s.dashArray;

        el.setAttribute("stroke", hs);
        el.setAttribute("stroke-width", hw);
        if (ho != null) el.setAttribute("stroke-opacity", ho);
        if (s.edgeLinecap) el.setAttribute("stroke-linecap", s.edgeLinecap);
        if (s.edgeLinejoin) el.setAttribute("stroke-linejoin", s.edgeLinejoin);
        if (s.edgeLinejoin === "miter" && s.edgeMiterlimit != null) {
            el.setAttribute("stroke-miterlimit", s.edgeMiterlimit);
        }
        if (hd) el.setAttribute("stroke-dasharray", hd);
    };

    const applyFaceFill = (el) => {
        el.setAttribute("fill", s.faceFill);
        if (s.faceOpacity != null) el.setAttribute("fill-opacity", s.faceOpacity);

        // 面描边（可选）
        if (s.faceStroke && s.faceStroke !== "none" && (s.faceStrokeWidth || 0) > 0) {
            el.setAttribute("stroke", s.faceStroke);
            el.setAttribute("stroke-width", s.faceStrokeWidth);
            if (s.faceStrokeOpacity != null) el.setAttribute("stroke-opacity", s.faceStrokeOpacity);
            if (s.edgeLinecap) el.setAttribute("stroke-linecap", s.edgeLinecap);
            if (s.edgeLinejoin) el.setAttribute("stroke-linejoin", s.edgeLinejoin);
        } else {
            el.setAttribute("stroke", "none");
        }
    };

    // 1) 生成顶面/底面投影点
    const bottomPts = [];
    const topPts = [];
    for (let i = 0; i < segments; i++) {
        const theta = (i / segments) * Math.PI * 2;
        const dx = r * Math.cos(theta);
        const dz = r * Math.sin(theta);
        bottomPts.push(projectFn(x + dx, y,     z + dz, config));
        topPts.push(projectFn(   x + dx, y + h, z + dz, config));
    }

    const g = document.createElementNS(SVG_NS, "g");
    g.setAttribute("id", id);

    // 2) 找轮廓切点：屏幕 X 最小/最大
    let minIdx = 0, maxIdx = 0;
    bottomPts.forEach((p, i) => {
        if (p.px < bottomPts[minIdx].px) minIdx = i;
        if (p.px > bottomPts[maxIdx].px) maxIdx = i;
    });

    // 3) 弧线 path 数据
    const getArcD = (pts, startIdx, endIdx) => {
        let d = `M ${pts[startIdx].px},${pts[startIdx].py}`;
        let i = startIdx;
        while (i !== endIdx) {
            i = (i + 1) % segments;
            d += ` L ${pts[i].px},${pts[i].py}`;
        }
        return d;
    };

    // 4) 判断前后弧（通过两段中点 py）
    const midIdxA = Math.floor((minIdx < maxIdx ? (minIdx + maxIdx) : (minIdx + maxIdx + segments)) / 2) % segments;
    const midIdxB = Math.floor((maxIdx < minIdx ? (maxIdx + minIdx) : (maxIdx + minIdx + segments)) / 2) % segments;

    const yA = bottomPts[midIdxA].py;
    const yB = bottomPts[midIdxB].py;

    let frontStart, frontEnd, backStart, backEnd;
    if (yA > yB) {
        frontStart = minIdx; frontEnd = maxIdx;
        backStart = maxIdx;  backEnd = minIdx;
    } else {
        frontStart = maxIdx; frontEnd = minIdx;
        backStart = minIdx;  backEnd = maxIdx;
    }

    // =========================
    // (A) 面：底面/侧面/顶面（补齐 id）
    // =========================

    // A1) 底面 face——放在最底层
    const bottomFace = document.createElementNS(SVG_NS, "polygon");
    bottomFace.setAttribute("id", `${id}-bottom-face`);
    bottomFace.setAttribute("points", bottomPts.map(p => `${p.px},${p.py}`).join(" "));
    applyFaceFill(bottomFace);
    g.appendChild(bottomFace);

    // A2) 侧面 face（补齐：以前 sidePoly 没 id）
    // 逻辑：沿“底面前弧”走一圈，再沿“顶面前弧”反向回来，形成侧面可见区域
    const sidePolyPoints = [];
    let curr = frontStart;
    while (true) {
        sidePolyPoints.push(bottomPts[curr]);
        if (curr === frontEnd) break;
        curr = (curr + 1) % segments;
    }
    curr = frontEnd;
    while (true) {
        sidePolyPoints.push(topPts[curr]);
        if (curr === frontStart) break;
        curr = (curr - 1 + segments) % segments;
    }

    const sideFace = document.createElementNS(SVG_NS, "polygon");
    sideFace.setAttribute("id", `${id}-side-face`);
    sideFace.setAttribute("points", sidePolyPoints.map(p => `${p.px},${p.py}`).join(" "));
    sideFace.setAttribute("fill", s.faceFill);
    if (s.faceOpacity != null) sideFace.setAttribute("fill-opacity", s.faceOpacity);
    sideFace.setAttribute("stroke", "none");
    g.appendChild(sideFace);

    // A3) 顶面 face（已有 id：top-face）
    const topFace = document.createElementNS(SVG_NS, "polygon");
    topFace.setAttribute("id", `${id}-top-face`);
    topFace.setAttribute("points", topPts.map(p => `${p.px},${p.py}`).join(" "));
    topFace.setAttribute("fill", s.faceFill);
    if (s.faceOpacity != null) topFace.setAttribute("fill-opacity", s.faceOpacity);

    // 顶面边界通常要显示：这里用可见边样式描边（不依赖 faceStroke）
    topFace.setAttribute("stroke", s.edgeStroke);
    topFace.setAttribute("stroke-width", s.edgeWidth);
    if (s.edgeOpacity != null) topFace.setAttribute("stroke-opacity", s.edgeOpacity);
    if (s.edgeLinecap) topFace.setAttribute("stroke-linecap", s.edgeLinecap);
    if (s.edgeLinejoin) topFace.setAttribute("stroke-linejoin", s.edgeLinejoin);
    g.appendChild(topFace);

    // =========================
    // (B) 边：底面前后弧 + 侧棱
    // =========================

    // B1) 底面后弧（hidden）
    const bottomBack = document.createElementNS(SVG_NS, "path");
    bottomBack.setAttribute("id", `${id}-bottom-back`);
    bottomBack.setAttribute("d", getArcD(bottomPts, backStart, backEnd));
    bottomBack.setAttribute("fill", "none");
    applyHiddenStroke(bottomBack);
    g.appendChild(bottomBack);

    // B2) 底面前弧（visible）
    const bottomFront = document.createElementNS(SVG_NS, "path");
    bottomFront.setAttribute("id", `${id}-bottom-front`);
    bottomFront.setAttribute("d", getArcD(bottomPts, frontStart, frontEnd));
    bottomFront.setAttribute("fill", "none");
    applyVisibleStroke(bottomFront);
    g.appendChild(bottomFront);

    // B3) 侧棱（左右两条）
    [minIdx, maxIdx].forEach((idx, i) => {
        const line = document.createElementNS(SVG_NS, "line");
        line.setAttribute("id", `${id}-side-${i}`);
        line.setAttribute("x1", topPts[idx].px);    line.setAttribute("y1", topPts[idx].py);
        line.setAttribute("x2", bottomPts[idx].px); line.setAttribute("y2", bottomPts[idx].py);
        applyVisibleStroke(line);
        g.appendChild(line);
    });

    // =========================
    // (C) 调试点：中心点（可选）
    // =========================
    if (s.showCenters) {
        const topCenter = projectFn(x, y + h, z, config);
        const bottomCenter = projectFn(x, y, z, config);

        const mk = (pt, cid) => {
            const c = document.createElementNS(SVG_NS, "circle");
            c.setAttribute("id", cid);
            c.setAttribute("cx", pt.px);
            c.setAttribute("cy", pt.py);
            c.setAttribute("r", s.centerRadius || 3);
            c.setAttribute("fill", s.centerFill || "#e11d48");
            c.setAttribute("opacity", 1);
            return c;
        };

        g.appendChild(mk(bottomCenter, `${id}-center-bottom`));
        g.appendChild(mk(topCenter, `${id}-center-top`));
    }

    // =========================
    // (D) 顶点（可选）
    // =========================
    if (s.showVertices) {
        // 保留你原来的关键点策略 + 补齐样式字段
        const topCenter = projectFn(x, y + h, z, config);
        const bottomCenter = projectFn(x, y, z, config);

        const keyPoints = [
            { pt: topCenter, label: "top-center" },
            { pt: bottomCenter, label: "bottom-center" },
            { pt: topPts[0], label: "top-0" },
            { pt: bottomPts[0], label: "bottom-0" }
        ];

        keyPoints.forEach(kp => {
            const circle = document.createElementNS(SVG_NS, "circle");
            circle.setAttribute("id", `${id}-vertex-${kp.label}`);
            circle.setAttribute("cx", kp.pt.px);
            circle.setAttribute("cy", kp.pt.py);
            circle.setAttribute("r", s.vertexRadius);
            circle.setAttribute("fill", s.vertexFill);
            if (s.vertexOpacity != null) circle.setAttribute("fill-opacity", s.vertexOpacity);

            if (s.vertexStroke && s.vertexStroke !== "none" && (s.vertexStrokeWidth || 0) > 0) {
                circle.setAttribute("stroke", s.vertexStroke);
                circle.setAttribute("stroke-width", s.vertexStrokeWidth);
            } else {
                circle.setAttribute("stroke", "none");
            }
            g.appendChild(circle);
        });
    }

    const svgTarget = (typeof svg !== "undefined" ? svg : window.mainSvg);
    if (!svgTarget) throw new Error("drawCylinder: global svg not found.");
    svgTarget.appendChild(g);
    return g;
}
```

#### 圆锥
```javascript
/**
 * 绘制圆锥体 (支持自定义投影策略)
 * 
 * @param {Object} config - 配置对象
 * @param {string} config.id - SVG 元素 ID 前缀
 * @param {number} config.x - 底面圆心 x 坐标 (3D)
 * @param {number} config.y - 底面圆心 y 坐标 (3D, 高度基准)
 * @param {number} config.z - 底面圆心 z 坐标 (3D, 深度)
 * @param {number} config.r - 底面半径
 * @param {number} config.h - 圆锥高度 (顶点坐标为 y+h)
 * @param {number} config.centerX - 画布中心点 X
 * @param {number} config.centerY - 画布中心点 Y
 * @param {Function} [config.projectFn=Projections.FRONT] - 投影函数（圆柱/圆锥默认 FRONT）
 * @param {Object} [config.styles] - 样式配置 (showVertices, faceFill 等)
 */
function drawCone(config) {
    const {
        id,
        x, y, z, r, h,
        projectFn = Projections.FRONT,
        styles = {},
    } = config;

    const s = { ...DEFAULT_STYLES, ...styles };
    const segments = (typeof s.segments === "number" && s.segments >= 12) ? s.segments : 72;

    // ---- 样式应用工具：可见/不可见边 ----
    const applyVisibleStroke = (el) => {
        el.setAttribute("stroke", s.edgeStroke);
        el.setAttribute("stroke-width", s.edgeWidth);
        if (s.edgeOpacity != null) el.setAttribute("stroke-opacity", s.edgeOpacity);
        if (s.edgeLinecap) el.setAttribute("stroke-linecap", s.edgeLinecap);
        if (s.edgeLinejoin) el.setAttribute("stroke-linejoin", s.edgeLinejoin);
        if (s.edgeLinejoin === "miter" && s.edgeMiterlimit != null) {
            el.setAttribute("stroke-miterlimit", s.edgeMiterlimit);
        }
    };

    const applyHiddenStroke = (el) => {
        const hs = (s.hiddenStroke != null) ? s.hiddenStroke : s.edgeStroke;
        const hw = (s.hiddenWidth != null) ? s.hiddenWidth : s.edgeWidth;
        const ho = (s.hiddenOpacity != null) ? s.hiddenOpacity : s.edgeOpacity;
        const hd = (s.hiddenDashArray != null) ? s.hiddenDashArray : s.dashArray;

        el.setAttribute("stroke", hs);
        el.setAttribute("stroke-width", hw);
        if (ho != null) el.setAttribute("stroke-opacity", ho);
        if (s.edgeLinecap) el.setAttribute("stroke-linecap", s.edgeLinecap);
        if (s.edgeLinejoin) el.setAttribute("stroke-linejoin", s.edgeLinejoin);
        if (s.edgeLinejoin === "miter" && s.edgeMiterlimit != null) {
            el.setAttribute("stroke-miterlimit", s.edgeMiterlimit);
        }
        if (hd) el.setAttribute("stroke-dasharray", hd);
    };

    const applyFaceFill = (el) => {
        el.setAttribute("fill", s.faceFill);
        if (s.faceOpacity != null) el.setAttribute("fill-opacity", s.faceOpacity);

        if (s.faceStroke && s.faceStroke !== "none" && (s.faceStrokeWidth || 0) > 0) {
            el.setAttribute("stroke", s.faceStroke);
            el.setAttribute("stroke-width", s.faceStrokeWidth);
            if (s.faceStrokeOpacity != null) el.setAttribute("stroke-opacity", s.faceStrokeOpacity);
            if (s.edgeLinecap) el.setAttribute("stroke-linecap", s.edgeLinecap);
            if (s.edgeLinejoin) el.setAttribute("stroke-linejoin", s.edgeLinejoin);
        } else {
            el.setAttribute("stroke", "none");
        }
    };

    // 1) 顶点投影
    const apex = projectFn(x, y + h, z, config);

    // 2) 底面圆周点投影
    const basePts = [];
    for (let i = 0; i < segments; i++) {
        const rad = (i / segments) * Math.PI * 2;
        const dx = r * Math.cos(rad);
        const dz = r * Math.sin(rad);
        basePts.push(projectFn(x + dx, y, z + dz, config));
    }

    const g = document.createElementNS(SVG_NS, "g");
    g.setAttribute("id", id);

    // 3) 找底面轮廓切点（屏幕 X 最小/最大）
    let minIdx = 0, maxIdx = 0;
    basePts.forEach((p, i) => {
        if (p.px < basePts[minIdx].px) minIdx = i;
        if (p.px > basePts[maxIdx].px) maxIdx = i;
    });

    // 4) 弧线 d
    const getArcD = (start, end) => {
        let d = `M ${basePts[start].px},${basePts[start].py}`;
        let i = start;
        while (i !== end) {
            i = (i + 1) % segments;
            d += ` L ${basePts[i].px},${basePts[i].py}`;
        }
        return d;
    };

    // 5) 分前后弧（比较两段中点 py）
    const midA = Math.floor((minIdx < maxIdx ? minIdx + maxIdx : minIdx + maxIdx + segments) / 2) % segments;
    const midB = Math.floor((maxIdx < minIdx ? maxIdx + minIdx : maxIdx + minIdx + segments) / 2) % segments;

    let frontStart, frontEnd, backStart, backEnd;
    if (basePts[midA].py > basePts[midB].py) {
        frontStart = minIdx; frontEnd = maxIdx;
        backStart = maxIdx;  backEnd = minIdx;
    } else {
        frontStart = maxIdx; frontEnd = minIdx;
        backStart = minIdx;  backEnd = maxIdx;
    }

    // =========================
    // (A) 面：底面 + 主体（补齐 id）
    // =========================

    // A1) 底面 face（补齐：圆锥底面）
    const baseFace = document.createElementNS(SVG_NS, "polygon");
    baseFace.setAttribute("id", `${id}-base-face`);
    baseFace.setAttribute("points", basePts.map(p => `${p.px},${p.py}`).join(" "));
    applyFaceFill(baseFace);
    g.appendChild(baseFace);

    // A2) 主体 fill（补齐：以前没有 id）
    if (s.faceFill && s.faceFill !== "none") {
        const polyPts = [apex];
        let curr = frontStart;
        while (true) {
            polyPts.push(basePts[curr]);
            if (curr === frontEnd) break;
            curr = (curr + 1) % segments;
        }

        const bodyFace = document.createElementNS(SVG_NS, "polygon");
        bodyFace.setAttribute("id", `${id}-body-face`);
        bodyFace.setAttribute("points", polyPts.map(p => `${p.px},${p.py}`).join(" "));
        bodyFace.setAttribute("fill", s.faceFill);
        if (s.faceOpacity != null) bodyFace.setAttribute("fill-opacity", s.faceOpacity);
        bodyFace.setAttribute("stroke", "none");
        g.appendChild(bodyFace);
    }

    // =========================
    // (B) 边：底面后弧/前弧 + 两条母线
    // =========================

    // B1) 底面后弧（hidden）
    const backPath = document.createElementNS(SVG_NS, "path");
    backPath.setAttribute("id", `${id}-base-back`);
    backPath.setAttribute("d", getArcD(backStart, backEnd));
    backPath.setAttribute("fill", "none");
    applyHiddenStroke(backPath);
    g.appendChild(backPath);

    // B2) 底面前弧（visible）
    const frontPath = document.createElementNS(SVG_NS, "path");
    frontPath.setAttribute("id", `${id}-base-front`);
    frontPath.setAttribute("d", getArcD(frontStart, frontEnd));
    frontPath.setAttribute("fill", "none");
    applyVisibleStroke(frontPath);
    g.appendChild(frontPath);

    // B3) 两条侧面轮廓线（母线）
    [minIdx, maxIdx].forEach((idx, i) => {
        const line = document.createElementNS(SVG_NS, "line");
        line.setAttribute("id", `${id}-side-${i}`);
        line.setAttribute("x1", apex.px);        line.setAttribute("y1", apex.py);
        line.setAttribute("x2", basePts[idx].px); line.setAttribute("y2", basePts[idx].py);
        applyVisibleStroke(line);
        g.appendChild(line);
    });

    // =========================
    // (C) 顶点/中心轴/中心点（可选）——补齐 axis id
    // =========================
    if (s.showVertices) {
        const baseCenter = projectFn(x, y, z, config);

        const vertices = [
            { p: apex, id: "apex" },
            { p: baseCenter, id: "center" },
            { p: basePts[frontStart], id: "tan1" },
            { p: basePts[frontEnd], id: "tan2" }
        ];

        vertices.forEach(v => {
            const circle = document.createElementNS(SVG_NS, "circle");
            circle.setAttribute("id", `${id}-v-${v.id}`);
            circle.setAttribute("cx", v.p.px);
            circle.setAttribute("cy", v.p.py);
            circle.setAttribute("r", s.vertexRadius);
            circle.setAttribute("fill", s.vertexFill);
            if (s.vertexOpacity != null) circle.setAttribute("fill-opacity", s.vertexOpacity);

            if (s.vertexStroke && s.vertexStroke !== "none" && (s.vertexStrokeWidth || 0) > 0) {
                circle.setAttribute("stroke", s.vertexStroke);
                circle.setAttribute("stroke-width", s.vertexStrokeWidth);
            } else {
                circle.setAttribute("stroke", "none");
            }
            g.appendChild(circle);
        });

        // 中心轴线（补齐 id：axis）
        const axis = document.createElementNS(SVG_NS, "line");
        axis.setAttribute("id", `${id}-axis`);
        axis.setAttribute("x1", baseCenter.px); axis.setAttribute("y1", baseCenter.py);
        axis.setAttribute("x2", apex.px);       axis.setAttribute("y2", apex.py);
        axis.setAttribute("fill", "none");
        applyHiddenStroke(axis);
        // 轴线通常更细一点：不破坏你的默认值，这里仅在未显式设置 hiddenWidth 时做轻微收敛
        if (s.hiddenWidth == null) axis.setAttribute("stroke-width", 1);
        // 轴线 dash 建议更密一些（若你想完全跟 hiddenDashArray 走，可删掉这两行）
        // axis.setAttribute("stroke-dasharray", "3,3");
        g.appendChild(axis);
    }

    // showCenters：给圆锥也加中心点（可选）
    if (s.showCenters) {
        const baseCenter = projectFn(x, y, z, config);

        const mk = (pt, cid) => {
            const c = document.createElementNS(SVG_NS, "circle");
            c.setAttribute("id", cid);
            c.setAttribute("cx", pt.px);
            c.setAttribute("cy", pt.py);
            c.setAttribute("r", s.centerRadius || 3);
            c.setAttribute("fill", s.centerFill || "#e11d48");
            c.setAttribute("opacity", 1);
            return c;
        };

        g.appendChild(mk(baseCenter, `${id}-center-base`));
        g.appendChild(mk(apex, `${id}-center-apex`));
    }

    const svgTarget = (typeof svg !== "undefined" ? svg : window.mainSvg);
    if (!svgTarget) throw new Error("drawCone: global svg not found.");
    svgTarget.appendChild(g);
    return g;
}
```

#### 箭头
```javascript
/**
 * 绘制箭头（线段 + 三角箭头）
 * - 直接使用全局 svg（fallback window.mainSvg）
 * - 默认样式来自 DEFAULT_ANNOTATION_STYLES，可用 config.styles 覆盖
 *
 * @param {Object} config
 * @param {string} config.id - 唯一标识前缀
 * @param {number} config.x1,y1 - 起点
 * @param {number} config.x2,y2 - 终点（箭尖）
 * @param {number} [config.headLength] - 箭头长度（默认用 DEFAULT_ANNOTATION_STYLES.arrowSize 或 15）
 * @param {number} [config.headWidth] - 箭头底边宽（默认用 DEFAULT_ANNOTATION_STYLES.arrowWidth*2 或 10）
 * @param {Object} [config.styles] - 样式覆盖（基于 DEFAULT_ANNOTATION_STYLES）
 */
function drawArrow(config) {
    const {
        id = "arrow",
        x1 = 100, y1 = 100,
        x2 = 300, y2 = 100,
        headLength,
        headWidth,
        styles = {}
    } = config;

    const s = { ...DEFAULT_ANNOTATION_STYLES, ...styles };

    // ---- 几何 ----
    const dx = x2 - x1;
    const dy = y2 - y1;
    const length = Math.sqrt(dx * dx + dy * dy);
    if (length < 0.001) return null;

    const ux = dx / length;
    const uy = dy / length;

    // 默认 head 参数：优先使用 config，其次用 DEFAULT_ANNOTATION_STYLES
    const HL = (headLength != null) ? headLength : (s.arrowSize != null ? s.arrowSize : 15);
    const HW = (headWidth  != null) ? headWidth  : (s.arrowWidth != null ? (s.arrowWidth * 2) : 10);

    // 箭尖后退中心点
    const backCX = x2 - HL * ux;
    const backCY = y2 - HL * uy;

    // 垂直向量（用于底边宽）
    const vx = -uy;
    const vy = ux;

    const pLeftX = backCX + (HW / 2) * vx;
    const pLeftY = backCY + (HW / 2) * vy;

    const pRightX = backCX - (HW / 2) * vx;
    const pRightY = backCY - (HW / 2) * vy;

    const headPoints = `${x2},${y2} ${pLeftX},${pLeftY} ${pRightX},${pRightY}`;

    // ---- 组 ----
    const g = document.createElementNS(SVG_NS, "g");
    g.setAttribute("id", id);

    // ---- 箭身 ----
    const shaft = document.createElementNS(SVG_NS, "line");
    shaft.setAttribute("id", `${id}-shaft`);
    shaft.setAttribute("x1", x1);
    shaft.setAttribute("y1", y1);
    shaft.setAttribute("x2", backCX);
    shaft.setAttribute("y2", backCY);

    shaft.setAttribute("stroke", s.stroke);
    shaft.setAttribute("stroke-width", s.strokeWidth);
    if (s.opacity != null) shaft.setAttribute("stroke-opacity", s.opacity);
    if (s.linecap) shaft.setAttribute("stroke-linecap", s.linecap);
    if (s.linejoin) shaft.setAttribute("stroke-linejoin", s.linejoin);

    // dashArray：用于“箭身是否虚线”
    // if (s.dashArray) shaft.setAttribute("stroke-dasharray", s.dashArray);

    g.appendChild(shaft);

    // ---- 箭头 ----
    const head = document.createElementNS(SVG_NS, "polygon");
    head.setAttribute("id", `${id}-head`);
    head.setAttribute("points", headPoints);

    // head 填充：用 s.fill；描边沿用 s.stroke（更统一）
    head.setAttribute("fill", s.fill);
    head.setAttribute("stroke", s.stroke);
    head.setAttribute("stroke-width", Math.max(1, (s.strokeWidth || 1) * 0.6));
    if (s.opacity != null) {
        head.setAttribute("fill-opacity", s.opacity);
        head.setAttribute("stroke-opacity", s.opacity);
    }
    if (s.linejoin) head.setAttribute("stroke-linejoin", s.linejoin);

    g.appendChild(head);

    const svgTarget = (typeof svg !== "undefined" ? svg : window.mainSvg);
    if (!svgTarget) throw new Error("drawArrow: global svg not found.");
    svgTarget.appendChild(g);
    return g;
}
```

#### 尺寸标注

##### 尺寸线标注
```javascript
/**
 * [通用工具] 绘制工程制图风格的尺寸线标注
 * 
 * 功能特性：
 * 1. 支持 3D 坐标自动投影。
 * 2. 去除间隙 (Gap)：延伸线直接从测量点 p1, p2 出发。
 * 3. 几何细节控制 (通过 styles 配置):
 *    - ext_length: 延伸线的总长度。尺寸线默认位于延伸线的 80% 位置，留出少量尾端。
 * 4. 文本自动对齐与避让支持。
 * 
 * 使用场景：长方体长宽高，正方体棱长，圆柱的高
 *
 * @param {object} config - 配置对象
 * @param {string} config.id - SVG组ID
 * @param {object} config.p1 - 起始点 3D坐标 {x,y,z}
 * @param {object} config.p2 - 结束点 3D坐标 {x,y,z}
 * @param {number} config.centerX - 画布中心点 X
 * @param {number} config.centerY - 画布中心点 Y
 * @param {string} config.direction - "上" | "下" | "左" | "右"
 * @param {string} config.text - 标注文本
 * @param {function} [config.projectFn] - 投影函数
 * @param {object} [config.styles] - 样式覆盖 { ext_length, arrowSize, ... }
 */
function drawDimensionLine(config) {
    const {
        id,
        p1,
        p2,
        direction,
        text,
        projectFn = Projections.OBLIQUE,
        styles = {}
    } = config;

    const s = { ...DEFAULT_ANNOTATION_STYLES, ...styles };

    const svgTarget = (typeof svg !== "undefined" ? svg : window.mainSvg);
    if (!svgTarget) throw new Error("drawDimensionLine: global svg not found.");

    // 1) 投影
    const pt1 = projectFn(p1.x, p1.y, p1.z, config);
    const pt2 = projectFn(p2.x, p2.y, p2.z, config);

    // 2) 向量计算
    const dx = pt2.px - pt1.px;
    const dy = pt2.py - pt1.py;
    const len = Math.sqrt(dx * dx + dy * dy);
    if (len < 0.001) return null;

    const ux = dx / len; // 单位方向向量
    const uy = dy / len;
    const baseNx = -uy;  // 法向量
    const baseNy = ux;

    // 3) 方向判定
    const dirVectors = {
        "上": { x: 0,  y: -1 },
        "下": { x: 0,  y:  1 },
        "左": { x: -1, y:  0 },
        "右": { x: 1,  y:  0 }
    };
    const target = dirVectors[direction] || dirVectors["上"];
    const dot = baseNx * target.x + baseNy * target.y;
    const dirSign = dot >= 0 ? 1 : -1;

    const nx = baseNx * dirSign;
    const ny = baseNy * dirSign;

    // 4) 几何点计算
    // extLen 为延伸线总长度
    const extLen = s.ext_length ?? 25; 
    // 尺寸线位置：设在延伸线的 80% 处，留出 20% 的出头（符合制图标准）
    const dimPos = extLen * 0.8; 

    const dimP1 = {
        x: pt1.px + nx * dimPos,
        y: pt1.py + ny * dimPos
    };
    const dimP2 = {
        x: pt2.px + nx * dimPos,
        y: pt2.py + ny * dimPos
    };

    // 延伸线起点紧贴 pt1, pt2
    const ext1_Start = { x: pt1.px, y: pt1.py };
    const ext1_End   = { x: pt1.px + nx * extLen, y: pt1.py + ny * extLen };
    const ext2_Start = { x: pt2.px, y: pt2.py };
    const ext2_End   = { x: pt2.px + nx * extLen, y: pt2.py + ny * extLen };

    // 5) 创建组
    const g = document.createElementNS(SVG_NS, "g");
    g.setAttribute("id", id);
    g.setAttribute("class", "annotation-group");

    const applyStroke = (el) => {
        el.setAttribute("stroke", s.stroke);
        el.setAttribute("stroke-width", s.strokeWidth);
        if (s.opacity != null) el.setAttribute("stroke-opacity", s.opacity);
        if (s.linecap) el.setAttribute("stroke-linecap", s.linecap);
        if (s.linejoin) el.setAttribute("stroke-linejoin", s.linejoin);
        if (s.dashArray) el.setAttribute("stroke-dasharray", s.dashArray);
    };

    // 6) 绘制延伸线 (Extension Lines)
    const elExt = document.createElementNS(SVG_NS, "path");
    elExt.setAttribute("id", `${id}-ext`);
    elExt.setAttribute(
        "d",
        `M ${ext1_Start.x},${ext1_Start.y} L ${ext1_End.x},${ext1_End.y} ` +
        `M ${ext2_Start.x},${ext2_Start.y} L ${ext2_End.x},${ext2_End.y}`
    );
    elExt.setAttribute("fill", "none");
    applyStroke(elExt);
    g.appendChild(elExt);

    // 7) 绘制主尺寸线 (Dimension Line)
    const elDim = document.createElementNS(SVG_NS, "line");
    elDim.setAttribute("id", `${id}-dim`);
    elDim.setAttribute("x1", dimP1.x);
    elDim.setAttribute("y1", dimP1.y);
    elDim.setAttribute("x2", dimP2.x);
    elDim.setAttribute("y2", dimP2.y);
    applyStroke(elDim);
    g.appendChild(elDim);

    // 8) 绘制双箭头
    const arrowSize = s.arrowSize ?? 8;
    const arrowWidth = s.arrowWidth ?? 3;

    const a1Tip = dimP1;
    const a1Base = { x: dimP1.x + ux * arrowSize, y: dimP1.y + uy * arrowSize };
    const a1Left = { x: a1Base.x + nx * arrowWidth, y: a1Base.y + ny * arrowWidth };
    const a1Right= { x: a1Base.x - nx * arrowWidth, y: a1Base.y - ny * arrowWidth };

    const a2Tip = dimP2;
    const a2Base = { x: dimP2.x - ux * arrowSize, y: dimP2.y - uy * arrowSize };
    const a2Left = { x: a2Base.x + nx * arrowWidth, y: a2Base.y + ny * arrowWidth };
    const a2Right= { x: a2Base.x - nx * arrowWidth, y: a2Base.y - ny * arrowWidth };

    const elArrows = document.createElementNS(SVG_NS, "path");
    elArrows.setAttribute("id", `${id}-arrows`);
    elArrows.setAttribute(
        "d",
        `M ${a1Tip.x},${a1Tip.y} L ${a1Left.x},${a1Left.y} L ${a1Right.x},${a1Right.y} Z ` +
        `M ${a2Tip.x},${a2Tip.y} L ${a2Left.x},${a2Left.y} L ${a2Right.x},${a2Right.y} Z`
    );
    elArrows.setAttribute("fill", s.fill);
    if (s.opacity != null) elArrows.setAttribute("fill-opacity", s.opacity);
    g.appendChild(elArrows);

    // 9) 绘制文本
    const midX = (dimP1.x + dimP2.x) / 2;
    const midY = (dimP1.y + dimP2.y) / 2;
    const textOffset = s.textOffset ?? 10;

    const textX = midX + nx * textOffset;
    const textY = midY + ny * textOffset;

    let anchor = "middle";
    if (nx > 0.3) anchor = "start";
    else if (nx < -0.3) anchor = "end";

    const elText = document.createElementNS(SVG_NS, "text");
    elText.setAttribute("id", `${id}-text`);
    elText.setAttribute("x", textX);
    elText.setAttribute("y", textY);
    elText.setAttribute("text-anchor", anchor);
    elText.setAttribute("dominant-baseline", "middle");
    elText.setAttribute("font-size", s.fontSize);
    elText.setAttribute("font-family", s.fontFamily);
    elText.setAttribute("fill", s.textFill ?? s.fill);

    // Halo 效果
    elText.setAttribute("stroke", s.haloStroke || "white");
    elText.setAttribute("stroke-width", s.haloWidth || 3);
    elText.setAttribute("paint-order", "stroke");
    elText.setAttribute("stroke-linejoin", "round");

    elText.textContent = text;

    // 智能避让相关元数据
    elText.classList.add("smart-label");
    elText.dataset.nx = nx;
    elText.dataset.ny = ny;
    elText.dataset.ux = ux;
    elText.dataset.uy = uy;
    elText.dataset.ox = textX;
    elText.dataset.oy = textY;
    elText.dataset.limit = (len / 2) - arrowSize - 5;
    elText.dataset.parentId = id;

    g.appendChild(elText);

    // 挂载到画布
    svgTarget.appendChild(g);

    // 可选背景矩形
    if (s.textBackground) {
        const bb = elText.getBBox();
        const pad = s.textBgPadding ?? 3;
        const bg = document.createElementNS(SVG_NS, "rect");
        bg.setAttribute("id", `${id}-text-bg`);
        bg.setAttribute("x", bb.x - pad);
        bg.setAttribute("y", bb.y - pad);
        bg.setAttribute("width", bb.width + pad * 2);
        bg.setAttribute("height", bb.height + pad * 2);
        bg.setAttribute("rx", 2);
        bg.setAttribute("ry", 2);
        bg.setAttribute("fill", s.textBgFill ?? "white");
        bg.setAttribute("fill-opacity", s.textBgOpacity ?? 1);
        g.insertBefore(bg, elText);
    }

    return g;
}
```

##### 花括号标注（废除，请勿使用）
```javascript
/**
 * [Type 2] 绘制花括号标记
 * 适用场景：汇总多段尺寸、总览标注
 */
function drawCurlyBraceLabel(config) {
    const {
        id,
        p1,
        p2,
        text,
        direction,
        projectFn = Projections.OBLIQUE,
        styles = {}
    } = config;

    const s = { ...DEFAULT_ANNOTATION_STYLES, ...styles };

    const svgTarget = (typeof svg !== "undefined" ? svg : window.mainSvg);
    if (!svgTarget) throw new Error("drawCurlyBraceLabel: global svg not found.");

    // 1) 投影
    const pt1 = projectFn(p1.x, p1.y, p1.z, config);
    const pt2 = projectFn(p2.x, p2.y, p2.z, config);

    // 2) 轴向 u
    const dx = pt2.px - pt1.px;
    const dy = pt2.py - pt1.py;
    const len = Math.sqrt(dx * dx + dy * dy);
    if (len < 0.001) return null;

    const ux = dx / len;
    const uy = dy / len;

    // 3) 法向 n（带方向）
    const baseNx = -uy;
    const baseNy = ux;

    const dirVectors = {
        "上": { x: 0,  y: -1 },
        "下": { x: 0,  y:  1 },
        "左": { x: -1, y:  0 },
        "右": { x: 1,  y:  0 }
    };
    const target = dirVectors[direction] || dirVectors["上"];
    const dot = baseNx * target.x + baseNy * target.y;
    const dirSign = dot >= 0 ? 1 : -1;

    const nx = baseNx * dirSign;
    const ny = baseNy * dirSign;

    // 4) 参数
    const braceGap = s.braceGap ?? 15;
    let depth = s.braceDepth ?? 10;
    let q = depth * 0.5;

    // 线太短防打结
    if (q * 4 > len) {
        q = len / 4;
        depth = q * 2;
    }

    // 5) 脚点（应用 gap）
    const pStart = { x: pt1.px + nx * braceGap, y: pt1.py + ny * braceGap };
    const pEnd   = { x: pt2.px + nx * braceGap, y: pt2.py + ny * braceGap };

    const midX = (pStart.x + pEnd.x) / 2;
    const midY = (pStart.y + pEnd.y) / 2;

    const tip = { x: midX + nx * depth, y: midY + ny * depth };

    const getPt = (baseX, baseY, uOff, nOff) => ({
        x: baseX + ux * uOff + nx * nOff,
        y: baseY + uy * uOff + ny * nOff
    });

    const pCorner1_Ctrl = getPt(pStart.x, pStart.y, 0, q);
    const pCorner1_End  = getPt(pStart.x, pStart.y, q, q);

    const pTip_Start    = getPt(midX, midY, -q, q);
    const pTip_Ctrl     = getPt(midX, midY, 0, q);

    const pTip_End      = getPt(midX, midY, q, q);
    const pCorner2_Start= getPt(pEnd.x, pEnd.y, -q, q);
    const pCorner2_Ctrl = getPt(pEnd.x, pEnd.y, 0, q);

    const pathData =
        `M ${pStart.x},${pStart.y} ` +
        `Q ${pCorner1_Ctrl.x},${pCorner1_Ctrl.y} ${pCorner1_End.x},${pCorner1_End.y} ` +
        `L ${pTip_Start.x},${pTip_Start.y} ` +
        `Q ${pTip_Ctrl.x},${pTip_Ctrl.y} ${tip.x},${tip.y} ` +
        `Q ${pTip_Ctrl.x},${pTip_Ctrl.y} ${pTip_End.x},${pTip_End.y} ` +
        `L ${pCorner2_Start.x},${pCorner2_Start.y} ` +
        `Q ${pCorner2_Ctrl.x},${pCorner2_Ctrl.y} ${pEnd.x},${pEnd.y}`;

    const g = document.createElementNS(SVG_NS, "g");
    g.setAttribute("id", id);

    // 括号路径
    const elPath = document.createElementNS(SVG_NS, "path");
    elPath.setAttribute("id", `${id}-brace`);
    elPath.setAttribute("d", pathData);
    elPath.setAttribute("fill", "none");
    elPath.setAttribute("stroke", s.stroke);
    elPath.setAttribute("stroke-width", s.strokeWidth);
    if (s.opacity != null) elPath.setAttribute("stroke-opacity", s.opacity);
    if (s.linecap) elPath.setAttribute("stroke-linecap", s.linecap);
    if (s.linejoin) elPath.setAttribute("stroke-linejoin", s.linejoin);
    if (s.dashArray) elPath.setAttribute("stroke-dasharray", s.dashArray);
    g.appendChild(elPath);

    // 文本
    const textOffset = s.textOffset ?? 13;
    const textX = tip.x + nx * textOffset;
    const textY = tip.y + ny * textOffset;

    let anchor = "middle";
    if (Math.abs(nx) > Math.abs(ny)) anchor = nx > 0 ? "start" : "end";

    const elText = document.createElementNS(SVG_NS, "text");
    elText.setAttribute("id", `${id}-text`);
    elText.setAttribute("x", textX);
    elText.setAttribute("y", textY);
    elText.setAttribute("text-anchor", anchor);
    elText.setAttribute("dominant-baseline", "middle");
    elText.setAttribute("font-size", s.fontSize);
    elText.setAttribute("font-family", s.fontFamily);
    elText.setAttribute("fill", s.textFill ?? s.fill);

    elText.setAttribute("stroke", s.haloStroke);
    elText.setAttribute("stroke-width", s.haloWidth);
    elText.setAttribute("paint-order", "stroke");
    elText.setAttribute("stroke-linejoin", s.haloLinejoin || "round");

    elText.textContent = text;
    g.appendChild(elText);

    svgTarget.appendChild(g);

    // 可选文字背景
    if (s.textBackground) {
        const bb = elText.getBBox();
        const pad = s.textBgPadding ?? 3;
        const bg = document.createElementNS(SVG_NS, "rect");
        bg.setAttribute("id", `${id}-text-bg`);
        bg.setAttribute("x", bb.x - pad);
        bg.setAttribute("y", bb.y - pad);
        bg.setAttribute("width", bb.width + pad * 2);
        bg.setAttribute("height", bb.height + pad * 2);
        bg.setAttribute("rx", 2);
        bg.setAttribute("ry", 2);
        bg.setAttribute("fill", s.textBgFill ?? "white");
        bg.setAttribute("fill-opacity", s.textBgOpacity ?? 1);
        bg.setAttribute("stroke", "none");
        g.insertBefore(bg, elText);
    }

    return g;
}
```

##### 辅助线标注
```javascript
/**
 * [Type 3] 绘制原地/辅助线标记
 * 适用场景：半径(R)、直径(d)、圆锥的高等
 */
function drawDirectLabel(config) {
    const {
        id,
        p1,
        p2,
        text,
        projectFn = Projections.OBLIQUE,
        styles = {}
    } = config;

    const s = { ...DEFAULT_ANNOTATION_STYLES, ...styles };

    const svgTarget = (typeof svg !== "undefined" ? svg : window.mainSvg);
    if (!svgTarget) throw new Error("drawDirectLabel: global svg not found.");

    const pt1 = projectFn(p1.x, p1.y, p1.z, config);
    const pt2 = projectFn(p2.x, p2.y, p2.z, config);

    const dx = pt2.px - pt1.px;
    const dy = pt2.py - pt1.py;
    const len = Math.sqrt(dx * dx + dy * dy);
    if (len < 0.001) return null;

    const ux = dx / len;
    const uy = dy / len;

    // 法向（用于文字偏移，确保文字不压在线上）
    const nx = -uy;
    const ny = ux;

    const g = document.createElementNS(SVG_NS, "g");
    g.setAttribute("id", id);

    // 1) 连接线
    const line = document.createElementNS(SVG_NS, "line");
    line.setAttribute("id", `${id}-line`);
    line.setAttribute("x1", pt1.px);
    line.setAttribute("y1", pt1.py);
    line.setAttribute("x2", pt2.px);
    line.setAttribute("y2", pt2.py);
    line.setAttribute("stroke", s.stroke);
    line.setAttribute("stroke-width", s.strokeWidth);
    if (s.opacity != null) line.setAttribute("stroke-opacity", s.opacity);
    if (s.linecap) line.setAttribute("stroke-linecap", s.linecap);
    if (s.linejoin) line.setAttribute("stroke-linejoin", s.linejoin);

    const dash = (s.directDashArray != null) ? s.directDashArray : s.dashArray;
    if (dash) line.setAttribute("stroke-dasharray", dash);

    g.appendChild(line);

    // 2) 文本容器（用于整体偏移和旋转）
    const midX = (pt1.px + pt2.px) / 2;
    const midY = (pt1.py + pt2.py) / 2;
    
    // 计算偏移量：根据字号自动计算一个合适的间距，或者从 styles 中读取
    const offsetDist = s.textOffset ?? (parseInt(s.fontSize) * 0.8 || 10); 
    
    // 计算旋转角度
    let angle = Math.atan2(dy, dx) * (180 / Math.PI);
    // 确保文字永远是正向的（不倒立）
    if (angle > 90 || angle < -90) {
        angle += 180;
    }

    // 创建一个子组来放置文字及其背景，方便统一变换
    const textGroup = document.createElementNS(SVG_NS, "g");
    // 将文字平移到中点，再沿法线偏移，最后旋转
    const tx = midX + nx * offsetDist;
    const ty = midY + ny * offsetDist;
    textGroup.setAttribute("transform", `translate(${tx}, ${ty}) rotate(${angle})`);

    const elText = document.createElementNS(SVG_NS, "text");
    elText.setAttribute("id", `${id}-text`);
    // 此时坐标设为 0,0，因为变换已经在 group 上处理了
    elText.setAttribute("x", 0);
    elText.setAttribute("y", 0);
    elText.setAttribute("text-anchor", "middle");
    elText.setAttribute("dominant-baseline", "middle");
    elText.setAttribute("font-size", s.fontSize);
    elText.setAttribute("font-family", s.fontFamily);
    elText.setAttribute("fill", s.textFill ?? s.fill);

    // Halo 效果
    elText.setAttribute("stroke", s.haloStroke || "none");
    elText.setAttribute("stroke-width", Math.max(s.haloWidth ?? 3, 4));
    elText.setAttribute("paint-order", "stroke");
    elText.setAttribute("stroke-linejoin", s.haloLinejoin || "round");

    elText.textContent = text;
    textGroup.appendChild(elText);
    g.appendChild(textGroup);

    svgTarget.appendChild(g);

    // 3) 可选文字背景
    if (s.textBackground) {
        const bb = elText.getBBox();
        const pad = s.textBgPadding ?? 3;
        const bg = document.createElementNS(SVG_NS, "rect");
        bg.setAttribute("id", `${id}-text-bg`);
        // 背景框相对于文字居中
        bg.setAttribute("x", bb.x - pad);
        bg.setAttribute("y", bb.y - pad);
        bg.setAttribute("width", bb.width + pad * 2);
        bg.setAttribute("height", bb.height + pad * 2);
        bg.setAttribute("rx", 2);
        bg.setAttribute("ry", 2);
        bg.setAttribute("fill", s.textBgFill ?? "white");
        bg.setAttribute("fill-opacity", s.textBgOpacity ?? 1);
        bg.setAttribute("stroke", "none");
        // 插入到文字前面
        textGroup.insertBefore(bg, elText);
    }

    return g;
}
```

### 常见画法

#### 标记周长，面积，体积等量

使用SVG的<text>元素，示例如下

```javascript
drawCylinder({
    id: "cup",
    x: 0, y: 0, z: 0,
    r: r_cyl, h: h_cup,
    ...config,
    styles: {
        faceFill: "rgba(255,255,255,0.1)", // 玻璃微透
        edgeStroke: "#333",
        edgeWidth: 2
    }
});

// 4. 标注底面周长 C=50cm
const pTextPos = proj(r_cyl, 0, -r_cyl, { centerX: cx, centerY: cy });   // 文字起始位置 (稍微偏离圆心)

// 4.3 绘制文字
const areaText = document.createElementNS(SVG_NS, "text");
areaText.setAttribute("id", "area-text-marker");
areaText.setAttribute("x", pTextPos.px + 20);
areaText.setAttribute("y", pTextPos.py);
areaText.setAttribute("font-size", "16");
areaText.setAttribute("font-family", "Arial, sans-serif");
areaText.setAttribute("fill", "#333");
areaText.setAttribute("text-anchor", "start"); 
areaText.textContent = "C=50cm";
svg.appendChild(areaText);
```

#### 标记
### 实现模版 (Template)

请严格参考以下代码结构进行生成：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>步骤描述</title>
    <style>
        body {
            margin: 0;
            background-color: #f7f7f7;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            font-family: Arial, sans-serif;
        }
        .container {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        svg {
            display: block;
        }
    </style>
</head>
<body>
    <script>
        const SVG_NS = "http://www.w3.org/2000/svg";

        const container = document.createElement("div");
        container.className = "container";

        const svg = document.createElementNS(SVG_NS, "svg");
        const svg_width = 960
        const svg_height = 540
        svg.setAttribute("width", svg_width);
        svg.setAttribute("height", svg_height);
        svg.setAttribute("viewBox", `0 0 ${svg_width} ${svg_height}`);
        svg.setAttribute("role", "img");
        svg.setAttribute("id", "立体几何题目讲解");
        window.mainSvg = svg; 

        const title = document.createElementNS(SVG_NS, "title");
        title.setAttribute("id", "title-1");
        title.textContent = "步骤描述";

        const desc = document.createElementNS(SVG_NS, "desc");
        desc.setAttribute("id", "desc-1");
        desc.textContent = "步骤描述";

        svg.appendChild(title);
        svg.appendChild(desc);
        container.appendChild(svg);
        document.body.appendChild(container);

    </script>
    <script id="lib-functions">
        // 这里放置所有的工具函数 (Projections, drawCuboid, etc.)
        // 确保这些函数在 step 脚本执行前已定义
    </script>
</body>
</html>
```

# 示例输入
## 试题
把一个棱长是8分米的正方体切成2个大小相同的长方体表面积增加\n128平方分米().

## 讲解脚本
<JSON>{"idx":1,"step":"审题","type":"语气引导","cont":"同学好，今天咱们来解决这道判断题。","display_cont":"","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":2,"step":"审题","type":"审题","cont":"题目是：把一个棱长是八分米的正方体，","display_cont":"","mark_cont":[{"mark_target":"question_stem","mark_target_idx":-1,"style":"circle","mark_cont":"把一个<mark>棱长是8分米</mark>的正方体","voice_cont":"题目是：把一个<mark>棱长是八分米</mark>的正方体，"}],"visual_guide":""}</JSON>
<JSON>{"idx":3,"step":"审题","type":"审题","cont":"切成两个大小相同的长方体，","display_cont":"","mark_cont":[{"mark_target":"question_stem","mark_target_idx":-1,"style":"circle","mark_cont":"切成2个<mark>大小相同</mark>的长方体表面积","voice_cont":"切成两个<mark>大小相同</mark>的长方体"}],"visual_guide":""}</JSON>
<JSON>{"idx":4,"step":"审题","type":"审题","cont":"表面积增加一百二十八平方分米，这个说法对吗？","display_cont":"<b>判断：</b>表面积增加128平方分米是否正确？","mark_cont":[{"mark_target":"question_stem","mark_target_idx":-1,"style":"highlight","mark_cont":"<mark>表面积增加\n128平方分米</mark>()","voice_cont":"<mark>表面积增加一百二十八平方分米</mark>"}],"visual_guide":""}</JSON>
<JSON>{"idx":5,"step":"思路引导","type":"语气引导","cont":"那怎么判断呢？","display_cont":"","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":6,"step":"思路引导","type":"分析","cont":"为了看得更清楚，我们先根据题意画出示意图。","display_cont":"","mark_cont":[],"visual_guide":"画一个正方体，下方使用延伸线标注棱长“8分米”。在正方体高的中点处画红色虚线切割线，并在正方体右侧画出两个完全一样的分离的长方体，中间画一个箭头指向它们"}</JSON>
<JSON>{"idx":7,"step":"思路引导","type":"分析","cont":"正方体切成两个长方体后，会新增切面，所以咱们只需要算出新增切面的总面积，就能判断对错啦。","display_cont":"【导图】增加的表面积→新增切面的总面积","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":8,"step":"步骤讲解","type":"语气引导","cont":"接下来咱们一步步计算。","display_cont":"","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":9,"step":"步骤讲解","type":"步骤名称","cont":"首先观察新增切面的形状。","display_cont":"<b>观察新增切面的形状：</b>","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":10,"step":"步骤讲解","type":"分析","cont":"大家观察右侧两个长方体上高亮的部分，这就是新增的切面。","display_cont":"","mark_cont":[],"visual_guide":"在右侧长方体中以透明红色标记两个新增的切面"}</JSON>
<JSON>{"idx":11,"step":"步骤讲解","type":"分析","cont":"切面的每条边都等于正方体的棱长，而且每个角都是直角，所以切面是正方形。","display_cont":"切面形状：正方形","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":12,"step":"步骤讲解","type":"语气引导","cont":"好，切面的形状咱们确定好啦。","display_cont":"","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":13,"step":"步骤讲解","type":"步骤名称","cont":"接下来计算单个切面的面积。","display_cont":"<b>计算单个切面的面积：</b>","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":14,"step":"步骤讲解","type":"公式说明","cont":"正方形的面积等于边长乘以边长。","display_cont":"正方形面积：$面积=边长\\times边长$","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":15,"step":"步骤讲解","type":"分析","cont":"观察右侧长方体可知，新增正方形切面的边长等于原正方体棱长八分米。","display_cont":"","mark_cont":[],"visual_guide":"在两个长方体新增正方形切面的右侧分别使用延伸线标注边长“8分米”"}</JSON>
<JSON>{"idx":16,"step":"步骤讲解","type":"计算","cont":"八乘以八等于六十四平方分米，所以单个切面的面积是六十四平方分米。","display_cont":"$单个切面面积=8\\times8=64$（平方分米）","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":17,"step":"步骤讲解","type":"出选择题","cont":"","display_cont":{"question":"根据计算结果，单个切面的面积是多少？","options":{"8平方分米":"错误","16平方分米":"错误","64平方分米":"正确","128平方分米":"错误"}},"mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":18,"step":"步骤讲解","type":"语气引导","cont":"单个切面的面积算出来啦。","display_cont":"","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":19,"step":"步骤讲解","type":"步骤名称","cont":"然后计算新增切面的总面积。","display_cont":"<b>计算新增切面的总面积：</b>","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":20,"step":"步骤讲解","type":"分析","cont":"切一次会新增两个相同的切面，所以总面积是单个切面面积的两倍。","display_cont":"$新增切面总面积=2\\times单个切面面积$","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":21,"step":"步骤讲解","type":"计算","cont":"二乘以六十四等于一百二十八平方分米，正好和题目中的数值一样。","display_cont":"$新增切面总面积=2\\times64=128$（平方分米）","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":22,"step":"步骤讲解","type":"语气引导","cont":"这样咱们就得到了增加的表面积。","display_cont":"","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":23,"step":"答案","type":"答案讲解","cont":"因为计算出的新增切面总面积是一百二十八平方分米，和题目中的数值完全相同，所以这道题的答案是正确。","display_cont":"正确","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":24,"step":"总结","type":"总结讲解","cont":"这道题的关键知识点是：正方体切割后增加的表面积等于新增切面的总面积，切一次新增两个切面。大家要记住哦！","display_cont":"<b>解题关键：</b>\\n1. 增加的表面积=新增切面总面积\\n2. 切一次新增2个切面","mark_cont":[],"visual_guide":""}</JSON>

# 示例输出
【使用的JS函数】
```json
[
    "drawCuboid",
    "drawArrow",
    "drawDimensionLine"
]
```

【每一步的输出】

```html
<script id="script_step_6">
// ==========================================
// Step 6: 绘制初始场景
// 定义全局常量，供后续步骤复用
// ==========================================

const CX = 480;
const CY = 420;     // 地面基准线
const SCALE = 14;   // 1分米 = 14像素
const S = 8 * SCALE; // 棱长 8分米 = 112px

const GAP_Y = 80;   // 右侧上下长方体的垂直间距
const DIST_X = 80;  // 左右物体与中心线的距离

// 计算位置坐标 (全局)
const x_left = -DIST_X - S; // 左侧正方体 X (右边缘在 -DIST_X)
const x_right = DIST_X;     // 右侧长方体 X (左边缘在 DIST_X)
const h_cut = S / 2;        // 切割高度

// 1. 左侧正方体 (Left Cube)
drawCuboid({
    id: "cube-main",
    x: x_left, y: 0, z: 0,
    w: S, h: S, d: S,
    centerX: CX, centerY: CY,
    styles: {
        faceFill: "rgba(255,255,255,0.8)",
        edgeStroke: "#333",
        edgeWidth: 2
    }
});

// 1.1 标注棱长 "8分米"
drawDimensionLine({
    id: "dim-cube-main-w",
    p1: { x: x_left, y: 0, z: 0 },
    p2: { x: x_left + S, y: 0, z: 0 },
    direction: "下",
    text: "8分米",
    centerX: CX, centerY: CY,
    styles: {
        gap: 15,
        textOffset: 20
    }
});

// 1.2 绘制切割虚线环 (Rectangular Loop)
// 手动创建元素时，使用 svg 变量挂载
const p_fl = Projections.OBLIQUE(x_left,     h_cut, 0, { centerX: CX, centerY: CY });
const p_fr = Projections.OBLIQUE(x_left + S, h_cut, 0, { centerX: CX, centerY: CY });
const p_br = Projections.OBLIQUE(x_left + S, h_cut, S, { centerX: CX, centerY: CY });
const p_bl = Projections.OBLIQUE(x_left,     h_cut, S, { centerX: CX, centerY: CY });

const cutGroup = document.createElementNS(SVG_NS, "g");
cutGroup.setAttribute("id", "cut-lines");
const cutPoly = document.createElementNS(SVG_NS, "polygon");
cutPoly.setAttribute("points", `${p_fl.px},${p_fl.py} ${p_fr.px},${p_fr.py} ${p_br.px},${p_br.py} ${p_bl.px},${p_bl.py}`);
cutPoly.setAttribute("fill", "rgba(225, 29, 72, 0.1)");
cutPoly.setAttribute("stroke", "#e11d48");
cutPoly.setAttribute("stroke-width", "2");
cutPoly.setAttribute("stroke-dasharray", "6,4");
cutGroup.appendChild(cutPoly);

// 挂载到 svg 容器
svg.appendChild(cutGroup);

// 2. 右侧两个分离的长方体 (Right Cuboids)
// 2.1 下半部分
drawCuboid({
    id: "cube-bottom",
    x: x_right, y: 0, z: 0,
    w: S, h: h_cut, d: S,
    centerX: CX, centerY: CY,
    styles: {
        faceFill: "white",
        edgeStroke: "#333"
    }
});

// 2.2 上半部分 (悬空)
const y_top_start = h_cut + GAP_Y;
drawCuboid({
    id: "cube-top",
    x: x_right, y: y_top_start, z: 0,
    w: S, h: h_cut, d: S,
    centerX: CX, centerY: CY,
    styles: {
        faceFill: "rgba(255,255,255,0.9)", 
        edgeStroke: "#333"
    }
});

// 3. 水平指示箭头
// 位置逻辑：设定在物体深度的一半 (z=S/2)，并在此深度的平面上计算左右留白
const arrowMargin = 30; // 留白距离
const arrowZ = S / 2;   // 深度中点
const arrowY = S / 2;   // 高度中点

// 左起点：左侧物体右边缘 + margin
const pArrowStart = Projections.OBLIQUE(x_left + S + arrowMargin, arrowY, arrowZ, { centerX: CX, centerY: CY });
// 右终点：右侧物体左边缘 - margin
const pArrowEnd   = Projections.OBLIQUE(x_right - arrowMargin,    arrowY, arrowZ, { centerX: CX, centerY: CY });

drawArrow({
    id: "arrow-process",
    x1: pArrowStart.px, y1: pArrowStart.py,
    x2: pArrowEnd.px,   y2: pArrowEnd.py,
    styles: {
        stroke: "#666",
        fill: "#666",
        arrowSize: 10,
        strokeWidth: 2.5
    }
});
</script>

<script id="script_step_10">
// ==========================================
// Step 10: 高亮新增切面
// ==========================================
// 局部常量
const highlightColor = "rgba(239, 68, 68, 0.5)"; 
const strokeColor = "#dc2626"; 

// 1. 下方长方体顶面
const faceBottomTop = document.getElementById("cube-bottom-face-top");
if (faceBottomTop) {
    faceBottomTop.setAttribute("fill", highlightColor);
    faceBottomTop.setAttribute("stroke", strokeColor);
    faceBottomTop.setAttribute("stroke-width", "2");
}

// 2. 上方长方体底面
const faceTopBottom = document.getElementById("cube-top-face-bottom");
if (faceTopBottom) {
    faceTopBottom.setAttribute("fill", highlightColor);
    faceTopBottom.setAttribute("stroke", strokeColor);
    faceTopBottom.setAttribute("stroke-width", "2");
}
</script>

<script id="script_step_15">
// ==========================================
// Step 15: 标注新增切面的边长 "8分米"
// 复用 Step 6 定义的 x_right, S, h_cut, GAP_Y, CX, CY
// ==========================================

// 1. 标注下方长方体切面 (顶面)
drawDimensionLine({
    id: "dim-cut-bottom",
    p1: { x: x_right + S, y: h_cut, z: 0 },
    p2: { x: x_right + S, y: h_cut, z: S },
    direction: "右",
    text: "8分米",
    centerX: CX, centerY: CY,
});

// 2. 标注上方长方体切面 (底面)
// 上方长方体的底面高度 = h_cut + GAP_Y (即 y_top_start)
const y_cut_top = h_cut + GAP_Y;

drawDimensionLine({
    id: "dim-cut-top",
    p1: { x: x_right + S, y: y_cut_top, z: 0 },
    p2: { x: x_right + S, y: y_cut_top, z: S },
    direction: "右",
    text: "8分米",
    centerX: CX, centerY: CY,
});
</script>
```

# 示例输入
## 试题
一个棱长8cm的正方体容器,里面水深6.5cm。把一个物体放入后(物体完全浸没在水中),从容器里溢出45mL水。这个物体的体积是多少立方厘米?

## 讲解脚本
<JSON>{"idx":1,"step":"审题","type":"语气引导","cont":"同学你好，今天我们要一起解决一道有趣的关于排水体积的问题。","display_cont":"","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":2,"step":"审题","type":"审题","cont":"来看题干：一个棱长八厘米的正方体容器，","display_cont":"","mark_cont":[{"mark_target":"question_stem","mark_target_idx":-1,"style":"circle","mark_cont":"<mark>棱长8cm</mark>的正方体","voice_cont":"<mark>棱长八厘米</mark>的正方体"}],"visual_guide":""}</JSON>
<JSON>{"idx":3,"step":"审题","type":"审题","cont":"里面水深六点五厘米。","display_cont":"","mark_cont":[{"mark_target":"question_stem","mark_target_idx":-1,"style":"circle","mark_cont":"水深<mark>6.5cm</mark>","voice_cont":"水深<mark>六点五厘米</mark>"}],"visual_guide":""}</JSON>
<JSON>{"idx":4,"step":"审题","type":"审题","cont":"把一个物体放入后，物体完全浸没在水中，从容器里溢出了四十五毫升水。","display_cont":"","mark_cont":[{"mark_target":"question_stem","mark_target_idx":-1,"style":"line","mark_cont":"物体<mark>完全浸没</mark>在水中","voice_cont":"物体<mark>完全浸没</mark>在水中"},{"mark_target":"question_stem","mark_target_idx":-1,"style":"circle","mark_cont":"溢出<mark>45mL</mark>水","voice_cont":"溢出了<mark>四十五毫升</mark>水"}],"visual_guide":""}</JSON>
<JSON>{"idx":5,"step":"审题","type":"审题","cont":"题目问：这个物体的体积是多少立方厘米呢？","display_cont":"","mark_cont":[{"mark_target":"question_stem","mark_target_idx":-1,"style":"highlight","mark_cont":"<mark>这个物体的体积是多少立方厘米</mark>?","voice_cont":"<mark>这个物体的体积是多少立方厘米</mark>呢"}],"visual_guide":""}</JSON>
<JSON>{"idx":6,"step":"思路引导","type":"语气引导","cont":"我们怎么求这个物体的体积呢？","display_cont":"","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":7,"step":"思路引导","type":"分析","cont":"为了看得更清楚，咱们先把放置物体前后的图画出来。","display_cont":"","mark_cont":[],"visual_guide":"画一个正方体容器，底部用延伸线标注棱长“8cm”，内部水域以透明蓝色表示，使用延伸线标注水深“h=6.5cm”；在右侧画一个同样的容器，内部水域填满整个正方体，容器内底部放置一个完全浸没的任意形状的浅棕色半透明物体，容器外右侧画一个盛满水的杯子，纯文字标注“45mL”"}</JSON>
<JSON>{"idx":8,"step":"思路引导","type":"分析","cont":"根据排水法原理，物体完全浸没在水中时，它的体积就等于它排开的水的体积。这部分水去哪了呢？一部分让容器里的水面上升了，另一部分溢出到了外面。","display_cont":"","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":9,"step":"思路引导","type":"分析","cont":"所以，物体的体积就等于“上升的水的体积”加上“溢出的水的体积”，也就是图中高亮的部分。","display_cont":"$物体体积=排开水的体积=上升水的体积+溢出水的体积$","mark_cont":[],"visual_guide":"以透明红色高亮容器内从6.5cm到8cm之间的新增水体部分，同时以透明红色高亮容器外溢出的水"}</JSON>
<JSON>{"idx":10,"step":"步骤讲解","type":"语气引导","cont":"思路理清了，咱们开始一步步计算。","display_cont":"","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":11,"step":"步骤讲解","type":"步骤名称","cont":"第一步，先算出容器里水面上升了多少。","display_cont":"<b>计算容器内上升水的体积</b>","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":12,"step":"步骤讲解","type":"分析","cont":"容器棱长是八厘米，原来水深六点五厘米，水面上升到满，高度上升了多少呢？","display_cont":"","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":13,"step":"步骤讲解","type":"计算","cont":"用八减去六点五等于一点五厘米。","display_cont":"上升高度：$8-6.5=1.5$（厘米）","mark_cont":[],"visual_guide":"在容器侧面使用辅助线标注从6.5cm到8cm这段距离，标注“1.5cm”"}</JSON>
<JSON>{"idx":14,"step":"步骤讲解","type":"分析","cont":"这部分上升的水是长方体形状，底面积就是正方体的底面积。","display_cont":"","mark_cont":[],"visual_guide":"高亮容器的底面正方形"}</JSON>
<JSON>{"idx":15,"step":"步骤讲解","type":"公式说明","cont":"正方体底面积等于棱长乘棱长。","display_cont":"$底面积=棱长\\times棱长$","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":16,"step":"步骤讲解","type":"计算","cont":"底面积是八乘八等于六十四平方厘米。","display_cont":"底面积：$8\\times8=64$（平方厘米）","mark_cont":[],"visual_guide":"在底面使用纯文字标注面积“S=64cm²”"}</JSON>
<JSON>{"idx":17,"step":"步骤讲解","type":"分析","cont":"有了底面积和上升的高度，就能算出容器里增加的水的体积啦。","display_cont":"","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":18,"step":"步骤讲解","type":"计算","cont":"六十四乘一点五，算出来等于九十六立方厘米。","display_cont":"上升水的体积：$64\\times1.5=96$（立方厘米）","mark_cont":[],"visual_guide":"在容器上方补全的水体部分使用纯文字标注“V=96cm³”"}</JSON>
<JSON>{"idx":19,"step":"步骤讲解","type":"出选择题","cont":"","display_cont":{"question":"现在我们算出了容器内上升的水体积是96立方厘米，那物体的总体积是下面哪一个？","options":{"只有溢出的45立方厘米":"错误","只有上升的96立方厘米":"错误","上升的96立方厘米加溢出的45立方厘米":"正确","上升的96立方厘米减溢出的45立方厘米":"错误"}},"mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":20,"step":"步骤讲解","type":"语气引导","cont":"这样我们就算出了上升部分的水体积。","display_cont":"","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":21,"step":"步骤讲解","type":"步骤名称","cont":"接下来，我们把溢出的水加进来，求出物体的总体积。","display_cont":"<b>计算物体总体积</b>","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":22,"step":"步骤讲解","type":"概念讲解","cont":"题目中溢出了四十五毫升水。我们要知道，一毫升就等于一立方厘米。","display_cont":"单位换算：$1\\text{mL}=1\\text{cm}^{3}$","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":23,"step":"步骤讲解","type":"计算","cont":"所以溢出的水的体积是四十五立方厘米。","display_cont":"溢出水的体积：$45\\text{mL}=45\\text{cm}^{3}$","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":24,"step":"步骤讲解","type":"计算","cont":"最后，把容器里上升的九十六立方厘米，加上溢出的四十五立方厘米，加起来等于一百四十一立方厘米。","display_cont":"$总体积=96+45=141$（立方厘米）","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":25,"step":"答案","type":"答案讲解","cont":"解答完成，别忘了写上答语。所以，这个物体的体积是141立方厘米。","display_cont":"答：这个物体的体积是141立方厘米。","mark_cont":[],"visual_guide":""}</JSON>
<JSON>{"idx":26,"step":"总结","type":"总结讲解","cont":"解决这道题的关键在于：当物体浸没且有水溢出时，物体的体积等于“容器内水面上升的体积”加上“溢出水的体积”。也就是要先填满容器，再溢出来，两部分都要算哦。","display_cont":"<b>解题关键：</b>\\n$物体体积 = 上升水的体积 + 溢出水的体积$","mark_cont":[],"visual_guide":""}</JSON>

# 示例输出
【使用的JS函数】
```json
[
    "drawCuboid",
    "drawCylinder",
    "drawArrow",
    "drawDimensionLine"
]
```

【每一步的输出】

```html
<script id="script_step_7">
// ==========================================
// Step 7: 绘制初始场景 (左右对比图)
// ==========================================

// 1. 定义全局布局常量 (调整版)
const CY = 420;       // 地面基准线
const SCALE = 18;     // 1cm = 18px
const S = 8 * SCALE;  // 棱长 8cm = 144px
const H_WATER = 6.5 * SCALE; // 水深 6.5cm
const H_RISE = 1.5 * SCALE;  // 上升 1.5cm

// 调整中心点，拉近距离
// 画布宽 960，两物体大概各占 200px (含透视)
// 左图中心从 280 -> 340
// 右图中心从 720 -> 620
// 间距从 440 缩小到 280
const CX_LEFT = 340;
const CX_RIGHT = 620;

// --- 左侧：放入物体前 ---

// 1.1 容器 (Container)
// z=0 为前表面, z=S 为后表面
drawCuboid({
    id: "container-left",
    x: -S/2, y: 0, z: 0,
    w: S, h: S, d: S,
    centerX: CX_LEFT, centerY: CY,
    styles: {
        faceFill: "none",
        edgeStroke: "#333",
        edgeWidth: 2
    }
});

// 1.2 内部水体 (Water) - 实体部分
// 仅填充颜色，不描边，轮廓由后面的虚线层负责
drawCuboid({
    id: "water-left",
    x: -S/2, y: 0, z: 0,
    w: S, h: H_WATER, d: S,
    centerX: CX_LEFT, centerY: CY,
    styles: {
        faceFill: "rgba(186, 230, 253, 0.4)", // 淡蓝
        edgeStroke: "none"
    }
});

// 1.3 绘制虚线水面 (Water Level Dashed Lines)
// 计算水面的四个顶点 (y = H_WATER)
const wl_p1 = Projections.OBLIQUE(-S/2, H_WATER, 0, { centerX: CX_LEFT, centerY: CY }); // 前左上
const wl_p2 = Projections.OBLIQUE(S/2,  H_WATER, 0, { centerX: CX_LEFT, centerY: CY }); // 前右上
const wl_p3 = Projections.OBLIQUE(S/2,  H_WATER, S, { centerX: CX_LEFT, centerY: CY }); // 后右上
const wl_p4 = Projections.OBLIQUE(-S/2, H_WATER, S, { centerX: CX_LEFT, centerY: CY }); // 后左上

const waterLevelGroup = document.createElementNS(SVG_NS, "g");
waterLevelGroup.setAttribute("id", "water-level-lines-left");

// 水面多边形 (虚线描边)
const waterPath = document.createElementNS(SVG_NS, "polygon");
waterPath.setAttribute("id", "water-surface-poly-left");
waterPath.setAttribute("points", `${wl_p1.px},${wl_p1.py} ${wl_p2.px},${wl_p2.py} ${wl_p3.px},${wl_p3.py} ${wl_p4.px},${wl_p4.py}`);
waterPath.setAttribute("fill", "rgba(186, 230, 253, 0.2)"); // 水面略淡
waterPath.setAttribute("stroke", "#0ea5e9");
waterPath.setAttribute("stroke-width", "2");
waterPath.setAttribute("stroke-dasharray", "5,4"); // 虚线效果
waterLevelGroup.appendChild(waterPath);
svg.appendChild(waterLevelGroup);

// 1.4 标注棱长 8cm (在前方面板的下方)
// p1, p2 的 z=0 确保是前表面
drawDimensionLine({
    id: "dim-len-8cm",
    p1: { x: -S/2, y: 0, z: 0 },
    p2: { x: S/2,  y: 0, z: 0 },
    direction: "下", 
    text: "8cm",
    centerX: CX_LEFT, centerY: CY,
});

// 1.5 标注水深 h=6.5cm
drawDimensionLine({
    id: "dim-water-h",
    p1: { x: S/2, y: 0,       z: S }, // z=S/2 在侧面中间
    p2: { x: S/2, y: H_WATER, z: S },
    direction: "右",
    text: "h=6.5cm",
    centerX: CX_LEFT, centerY: CY,
});


// --- 右侧：放入物体后 ---

// 2.1 沉底物体 (Object)
drawCuboid({
    id: "obj-submerged",
    x: -S/4, y: 0, z: S/4,
    w: S/2, h: S/4, d: S/2,
    centerX: CX_RIGHT, centerY: CY,
    styles: {
        faceFill: "rgba(168, 85, 24, 0.6)", // 棕色
        edgeStroke: "#92400e"
    }
});

// 2.2 基础水体 (Base Water)
drawCuboid({
    id: "water-right-base",
    x: -S/2, y: 0, z: 0,
    w: S, h: H_WATER, d: S,
    centerX: CX_RIGHT, centerY: CY,
    styles: {
        faceFill: "rgba(186, 230, 253, 0.4)",
        edgeStroke: "none"
    }
});

// 2.3 上升水体 (Rise Water) - 独立ID方便高亮
drawCuboid({
    id: "water-right-rise",
    x: -S/2, y: H_WATER, z: 0,
    w: S, h: H_RISE, d: S,
    centerX: CX_RIGHT, centerY: CY,
    styles: {
        faceFill: "rgba(186, 230, 253, 0.5)",
        edgeStroke: "#7dd3fc", // 轻微描边
        edgeWidth: 1
    }
});

// 2.4 容器轮廓
drawCuboid({
    id: "container-right",
    x: -S/2, y: 0, z: 0,
    w: S, h: S, d: S,
    centerX: CX_RIGHT, centerY: CY,
    styles: {
        faceFill: "none",
        edgeStroke: "#333",
        edgeWidth: 2
    }
});

// 2.5 溢出杯子 (Cup)
// 调整位置：S/2 (容器边缘) + 90 (加大偏移，避免与左侧视觉粘连)
const CUP_X = S/2 + 90; 
const CUP_R = 25;
const CUP_H = 45;

// 杯内水 (45mL)
drawCylinder({
    id: "cup-water",
    x: CUP_X, y: 0, z: 0,
    r: CUP_R - 2, h: 35, // 假设水高
    centerX: CX_RIGHT, centerY: CY,
    styles: {
        faceFill: "rgba(186, 230, 253, 0.8)",
        edgeStroke: "none"
    }
});

// 杯身
drawCylinder({
    id: "cup-body",
    x: CUP_X, y: 0, z: 0,
    r: CUP_R, h: CUP_H,
    centerX: CX_RIGHT, centerY: CY,
    styles: {
        faceFill: "rgba(255, 255, 255, 0.3)",
        edgeStroke: "#666",
        edgeWidth: 1.5
    }
});

// 2.6 纯文字标注 "45mL"
// 使用 Front 投影获取杯子上方坐标
const cupTextPos = Projections.FRONT(CUP_X, 42, 0, { centerX: CX_RIGHT, centerY: CY });
const text45 = document.createElementNS(SVG_NS, "text");
text45.setAttribute("id", "text-45ml");
text45.setAttribute("x", cupTextPos.px);
text45.setAttribute("y", cupTextPos.py - 10);
text45.setAttribute("text-anchor", "middle");
text45.setAttribute("fill", "#333");
text45.setAttribute("font-size", "14");
text45.setAttribute("font-weight", "bold");
text45.textContent = "45mL";
svg.appendChild(text45);

</script>

<script id="script_step_9">
// ==========================================
// Step 9: 高亮上升水体和溢出水
// ==========================================

// 1. 高亮上升部分 (Water Rise)
const riseGroup = document.getElementById("water-right-rise");
if (riseGroup) {
    // 找到所有面进行变色
    const polys = riseGroup.querySelectorAll("polygon");
    polys.forEach(p => {
        p.setAttribute("fill", "rgba(248, 113, 113, 0.5)"); // 红色半透
        p.setAttribute("stroke", "#ef4444");
    });
}

// 2. 高亮杯中水 (Cup Water)
const cupWater = document.getElementById("cup-water");
if (cupWater) {
    const polys = cupWater.querySelectorAll("polygon, path");
    polys.forEach(p => {
        // 只填充，不一定描边
        if (p.tagName === "polygon" || p.tagName === "path") {
            p.setAttribute("fill", "rgba(248, 113, 113, 0.6)");
        }
    });
}
</script>

<script id="script_step_13">
// ==========================================
// Step 13: 标注上升高度 1.5cm
// ==========================================

// 在右侧容器的右前方棱上标注
// x = S/2, z = 0 (右前棱)
drawDimensionLine({
    id: "dim-rise-1.5",
    p1: { x: S/2, y: H_WATER, z: 0 },
    p2: { x: S/2, y: S,       z: 0 },
    direction: "右",
    text: "1.5cm",
    centerX: CX_RIGHT, centerY: CY,
    styles: {
        textFill: "#dc2626"
    }
});
</script>

<script id="script_step_16">
// ==========================================
// Step 16: 纯文字标注底面积 S=64cm²
// ==========================================

// 计算左侧容器底面中心投影
// 深度中心 z = S/2
const pLeftCenter = Projections.OBLIQUE(0, 0, S/2, { centerX: CX_LEFT, centerY: CY }); 

const textS = document.createElementNS(SVG_NS, "text");
textS.setAttribute("id", "text-area-S");
textS.setAttribute("x", pLeftCenter.px);
textS.setAttribute("y", pLeftCenter.py + 10); // 稍微下移
textS.setAttribute("text-anchor", "middle");
textS.setAttribute("fill", "#b45309"); // 棕橙色
textS.setAttribute("font-size", "16");
textS.setAttribute("font-weight", "bold");
textS.setAttribute("stroke", "white"); // 白描边
textS.setAttribute("stroke-width", "3");
textS.setAttribute("paint-order", "stroke");
textS.textContent = "S=64cm²";
svg.appendChild(textS);

// 高亮底面 (左侧容器)
const leftBottom = document.getElementById("container-left-face-bottom");
if (leftBottom) {
    leftBottom.setAttribute("fill", "rgba(251, 191, 36, 0.4)"); // 黄色
    leftBottom.setAttribute("stroke", "#f59e0b");
}
</script>

<script id="script_step_18">
// ==========================================
// Step 18: 纯文字标注上升体积 V=96cm³
// ==========================================

// 计算右侧上升水体的中心位置
const riseMidY = H_WATER + H_RISE/2;
// 投影点 z=S/2 处于水体内部
const pRiseCenter = Projections.OBLIQUE(0, riseMidY, S/2, { centerX: CX_RIGHT, centerY: CY });

const textV = document.createElementNS(SVG_NS, "text");
textV.setAttribute("id", "text-vol-rise");
textV.setAttribute("x", pRiseCenter.px);
textV.setAttribute("y", pRiseCenter.py);
textV.setAttribute("text-anchor", "middle");
textV.setAttribute("dominant-baseline", "middle");
textV.setAttribute("fill", "#dc2626"); // 红色
textV.setAttribute("font-size", "16");
textV.setAttribute("font-weight", "bold");
textV.setAttribute("stroke", "white");
textV.setAttribute("stroke-width", "3");
textV.setAttribute("paint-order", "stroke");
textV.textContent = "V=96cm³";
svg.appendChild(textV);
</script>
```

# 输入

## 试题
{{question}}

## 讲解脚本
{{script}}
请结合输出要求和对示例的详细分析，针对上面的【输入】题目和讲解脚本，给出【使用的JS函数】和【每一步的输出】。