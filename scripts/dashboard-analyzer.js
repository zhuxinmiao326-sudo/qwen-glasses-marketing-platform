/**
 * 洞察看板 · 悦普数据上传分析器
 * 纯浏览器端运行：SheetJS 解析 Excel，PapaParse 解析 CSV，Plotly 渲染图表。
 */
(function () {
  'use strict';

  // ============================================================
  // 0. 工具函数
  // ============================================================
  function num(x) {
    if (x === null || x === undefined || x === '') return 0;
    if (typeof x === 'number') return isFinite(x) ? x : 0;
    const s = String(x).replace(/,/g, '').replace(/万/g, '').replace(/%/g, '').replace(/元/g, '').trim();
    if (s === '' || s === '-') return 0;
    const v = parseFloat(s);
    return isFinite(v) ? v : 0;
  }

  function fmtWan(x) { return (x / 10000).toFixed(1); }
  function fmtPct(x, digits) {
    digits = digits === undefined ? 2 : digits;
    if (x === null || x === undefined || !isFinite(x)) return '';
    return (x * 100).toFixed(digits) + '%';
  }
  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  }
  function percentileScore(values, x, higherIsBetter) {
    const arr = values.filter(v => v !== null && v !== undefined && isFinite(v));
    if (!arr.length || !isFinite(x)) return 50;
    const n = arr.length;
    let le = 0;
    for (const v of arr) if (v <= x) le += 1;
    let score = (le / n) * 100;
    if (!higherIsBetter) score = 100 - score;
    return Math.max(0, Math.min(100, score));
  }
  function avg(arr, key) {
    const vals = arr.filter(o => isFinite(key ? o[key] : o)).map(o => key ? o[key] : o);
    return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
  }
  function sum(arr, key) {
    return arr.reduce((a, o) => a + (isFinite(key ? o[key] : o) ? (key ? o[key] : o) : 0), 0);
  }
  function median(values) {
    const arr = values.filter(v => isFinite(v)).sort((a, b) => a - b);
    if (!arr.length) return 0;
    const m = Math.floor(arr.length / 2);
    return arr.length % 2 ? arr[m] : (arr[m - 1] + arr[m]) / 2;
  }

  // ============================================================
  // 1. 分类函数
  // ============================================================
  function classifyType(title, rawType, project) {
    const t = String(rawType || '').toLowerCase().replace(/、/g, '/').replace(/,/g, '/');
    const ti = String(title || '').toLowerCase();
    const pj = String(project || '').toLowerCase();
    if (ti.includes('盲人') || ti.includes('宝哥') || t.includes('盲人')) return '盲人解读';
    if (t.includes('外国人') || ti.includes('外国')) return '外国人';
    if (t.includes('自然科普') || t.includes('科普')) return '自然科普';
    if (t.includes('音乐')) return '音乐';
    if (t.includes('职场') || t.includes('办公') || t.includes('会议')) return '职场';
    if (t.includes('时尚') || t.includes('穿搭') || ti.includes('ootd')) return '时尚';
    if (t.includes('出行') || t.includes('旅游') || t.includes('旅行')) return '出行旅游';
    if (t.includes('运动') || t.includes('体育')) return '运动/体育';
    if (t.includes('教育') || t.includes('亲子')) return '教育亲子';
    if (t.includes('汽车')) return '汽车';
    if (t.includes('摄影') || t.includes('拍摄')) return '摄影';
    if (t.includes('生活方式') || t.includes('生活记录') || ti.includes('vlog')) return '生活方式';
    if (t.includes('行业') || t.includes('分析') || t.includes('解读')) return '行业分析&解读';
    if (t.includes('科技') || t.includes('数码') || t.includes('测评')) return '科技数码';
    return '生活方式';
  }

  function classifyAudience(title, rawType, blogger, project) {
    const ti = String(title || '').toLowerCase();
    const t = String(rawType || '').toLowerCase();
    const b = String(blogger || '').toLowerCase();
    const pj = String(project || '').toLowerCase();
    if (ti.includes('盲人') || ti.includes('视障') || ti.includes('宝哥')) return '无障碍/视障人群';
    if (ti.includes('职场') || ti.includes('办公') || ti.includes('会议') || ti.includes('上班')) return '职场白领/办公人群';
    if (ti.includes('大学生') || ti.includes('学生') || ti.includes('高考') || ti.includes('校园')) return '大学生/年轻群体';
    if (ti.includes('亲子') || ti.includes('教育') || ti.includes('孩子') || ti.includes('弟弟') || ti.includes('作文')) return '亲子/教育人群';
    if (ti.includes('旅行') || ti.includes('旅游') || ti.includes('户外') || ti.includes('出差')) return '旅行/户外人群';
    if (ti.includes('摄影') || ti.includes('vlog') || ti.includes('创作')) return '摄影/创作人群';
    if (t.includes('外国人') || ti.includes('老外')) return '国际/跨文化人群';
    if (ti.includes('科技') || ti.includes('数码') || ti.includes('测评') || t.includes('科技')) return '科技数码爱好者';
    if (ti.includes('生活') || ti.includes('日常') || ti.includes('品质')) return '品质生活人群';
    if (pj.includes('泛大众') || ti.includes('大众')) return '泛大众';
    return '泛大众';
  }

  function classifyScene(title, rawType) {
    const ti = String(title || '').toLowerCase();
    const t = String(rawType || '').toLowerCase();
    if (ti.includes('办公') || ti.includes('会议') || ti.includes('上班') || ti.includes('职场')) return '办公/会议';
    if (ti.includes('旅行') || ti.includes('旅游') || ti.includes('出差')) return '旅行/导航';
    if (ti.includes('展') || ti.includes('发布会') || ti.includes('awe') || ti.includes('waic')) return '展会/发布会';
    if (ti.includes('摄影') || ti.includes('拍') || ti.includes('vlog') || ti.includes('创作')) return '摄影/创作';
    if (ti.includes('日常') || ti.includes('生活') || ti.includes('种草')) return '日常种草';
    if (ti.includes('运动') || ti.includes('户外') || ti.includes('钓鱼') || ti.includes('跑步')) return '运动/户外';
    return '日常种草';
  }

  function classifyProject(rawProject, title) {
    const pj = String(rawProject || '');
    const ti = String(title || '').toLowerCase();
    if (ti.includes('waic') || pj.toLowerCase().includes('waic')) return 'WAIC项目';
    if (ti.includes('世界杯')) return '世界杯项目';
    if (ti.includes('大学生') || ti.includes('高考')) return '大学生项目';
    if (ti.includes('云南')) return '云南项目';
    if (ti.includes('品鉴会') || pj.toLowerCase().includes('品鉴')) return '5.8品鉴会';
    if (ti.includes('横测') || ti.includes('横评')) return '横测图文';
    if (ti.includes('宝哥')) return '宝哥盲人事件';
    if (pj && pj !== 'nan' && pj !== 'None') {
      if (['76w','90w','星伴','集采'].some(k => pj.includes(k))) return '其他项目';
      return pj.trim();
    }
    return '其他项目';
  }

  // ============================================================
  // 2. 列名探测
  // ============================================================
  function findCol(cols, keywords) {
    for (const c of cols) {
      const s = String(c || '');
      for (const k of keywords) {
        if (s.includes(k)) return c;
      }
    }
    return null;
  }

  function detectColumns(cols, platform) {
    const d = {};
    if (platform === '抖音') {
      d.cost = findCol(cols, ['总计费用']);
      d.gmv = findCol(cols, ['成交']);
      d.views = findCol(cols, ['播放量']);
      d.interact = findCol(cols, ['互动']);
      d.a3 = findCol(cols, ['A3询问用户', '累积新增']);
      d.finish = findCol(cols, ['完播率']);
      d.date = findCol(cols, ['实际发布时间', '发布时间']);
      d.title = findCol(cols, ['内容创意', '一句话描述', '标题']);
      d.blogger = findCol(cols, ['账号昵称', '达人']);
      d.type = findCol(cols, ['类型']);
      d.link = findCol(cols, ['发布链接', '链接']);
    } else {
      d.cost = findCol(cols, ['总计消耗', '消耗']);
      d.gmv = findCol(cols, ['全店成交GMV', 'GMV', '成交']);
      d.views = findCol(cols, ['阅读量']);
      d.interact = findCol(cols, ['互动量']);
      d.exposure = findCol(cols, ['曝光量']);
      d.paidCtr = findCol(cols, ['点击率', 'CTR']);
      d.cpc = findCol(cols, ['CPC', '点击成本']);
      d.finish = findCol(cols, ['完播率']);
      d.date = findCol(cols, ['发布时间']);
      d.title = findCol(cols, ['内容创意', '一句话描述', '标题']);
      d.blogger = findCol(cols, ['账号昵称', '达人']);
      d.type = findCol(cols, ['类型']);
      d.project = findCol(cols, ['传播阶段']);
      d.projectFallback = findCol(cols, ['任务组']);
      d.link = findCol(cols, ['发布链接', '链接']);
    }
    return d;
  }

  // ============================================================
  // 3. 解析工作表
  // ============================================================
  function parseSheet(rows, platform, projectColName, dateRange) {
    const cols = rows.length ? Object.keys(rows[0]) : [];
    const d = detectColumns(cols, platform);
    const out = [];
    for (const r of rows) {
      if (String(r['平台'] || '').trim() !== platform &&
          !(platform === '小红书' && ['红书','小红书'].includes(String(r['平台'] || '').trim()))) continue;

      const dateVal = r[d.date];
      let date = null;
      if (dateVal) {
        if (typeof dateVal === 'number') {
          // Excel 序列号转日期
          date = new Date((dateVal - 25569) * 86400 * 1000);
        } else {
          date = new Date(dateVal);
        }
      }
      if (!date || isNaN(date.getTime())) continue;
      if (dateRange && (date < dateRange[0] || date > dateRange[1])) continue;

      const cost = num(r[d.cost]);
      if (cost <= 0) continue;
      const gmv = num(r[d.gmv]);
      const views = num(r[d.views]);
      const interact = num(r[d.interact]);
      const exposure = num(r[d.exposure]);
      const finishRate = d.finish ? num(r[d.finish]) : 0;
      const a3 = d.a3 ? num(r[d.a3]) : 0;
      const paidCtr = d.paidCtr ? num(r[d.paidCtr]) : 0;
      const cpc = d.cpc ? num(r[d.cpc]) : 0;

      let rawProject = '';
      if (platform === '抖音') {
        rawProject = projectColName ? r[projectColName] : '';
      } else {
        rawProject = (d.project && r[d.project] !== undefined && r[d.project] !== '') ? r[d.project] : (d.projectFallback ? r[d.projectFallback] : '');
      }
      const title = r[d.title] || '';
      const rawType = r[d.type] || '';
      const type = classifyType(title, rawType, rawProject);
      const audience = classifyAudience(title, rawType, r[d.blogger], rawProject);
      const scene = classifyScene(title, rawType);
      const project = classifyProject(rawProject, title);

      out.push({
        platform,
        date,
        title: String(title),
        blogger: String(r[d.blogger] || ''),
        cost,
        gmv,
        roi: (gmv - cost) / cost,
        roas: cost > 0 ? gmv / cost : 0,
        views,
        interact,
        exposure,
        engagementRate: views > 0 ? (interact / views * 100) : 0,
        finishRate,
        a3,
        paidCtr,
        cpc,
        type,
        audience,
        scene,
        project,
        link: String(r[d.link] || '')
      });
    }
    return out;
  }

  function detectSheets(workbook) {
    const names = workbook.SheetNames;
    const sheets = [];
    for (const n of names) {
      const lower = n.toLowerCase();
      if (lower.includes('抖音') && lower.includes('4')) sheets.push({ name: n, platform: '抖音', projectCol: '3/12-上海AWE探展' });
      else if (lower.includes('抖音') && (lower.includes('5') || lower.includes('8'))) sheets.push({ name: n, platform: '抖音', projectCol: '__FIRST_COL__' });
      else if (lower.includes('红书') || lower.includes('小红书')) sheets.push({ name: n, platform: '小红书', projectCol: null });
    }
    return sheets;
  }

  // ============================================================
  // 4. 分析引擎
  // ============================================================
  function analyze(rows, dateRange) {
    const dy = rows.filter(r => r.platform === '抖音');
    const xhs = rows.filter(r => r.platform === '小红书');
    const all = rows;

    const totalCost = sum(all, 'cost');
    const totalGmv = sum(all, 'gmv');
    const overallRoi = totalCost > 0 ? (totalGmv - totalCost) / totalCost : 0;

    function platformMetrics(list) {
      const cost = sum(list, 'cost');
      const gmv = sum(list, 'gmv');
      return {
        count: list.length,
        cost,
        gmv,
        gmvWan: gmv / 10000,
        roi: cost > 0 ? (gmv - cost) / cost : 0,
        roas: cost > 0 ? gmv / cost : 0,
        avgEngagement: avg(list, 'engagementRate'),
        avgFinishRate: avg(list, 'finishRate'),
        paidA3: sum(list, 'a3'),
        a3Cost: sum(list, 'a3') > 0 ? cost / sum(list, 'a3') : cost
      };
    }

    const dyM = platformMetrics(dy);
    const xhsM = platformMetrics(xhs);

    // 五维雷达：传播力、互动力、转化力、ROI力、综合价值
    // 用平台内百分位计算各维度
    function dimScore(list, metric, higherIsBetter) {
      const vals = list.map(r => r[metric]).filter(v => isFinite(v));
      if (!vals.length) return 50;
      const m = avg(list, metric);
      return percentileScore(vals, m, higherIsBetter);
    }
    function radar(list, platform) {
      // 传播力：平均播放量/阅读量的平台内百分位
      const reachVals = all.map(r => r.views);
      const reach = percentileScore(reachVals, avg(list, 'views'), true);
      // 互动力：平均互动率百分位
      const engVals = all.filter(r => r.platform === platform).map(r => r.engagementRate);
      const eng = percentileScore(engVals, avg(list, 'engagementRate'), true);
      // 转化力：平均转化率百分位（用 ROI 近似）
      const convVals = all.filter(r => r.platform === platform).map(r => r.roi);
      const conv = percentileScore(convVals, avg(list, 'roi'), true);
      // ROI力：平均 ROI 百分位
      const roiVals = all.filter(r => r.platform === platform).map(r => r.roi);
      const roiS = percentileScore(roiVals, avg(list, 'roi'), true);
      const value = (reach + eng + conv + roiS) / 4;
      return [reach, eng, conv, roiS, value];
    }

    const radarData = [
      { name: '抖音', data: radar(dy, '抖音').map(v => +v.toFixed(1)) },
      { name: '小红书', data: radar(xhs, '小红书').map(v => +v.toFixed(1)) }
    ];

    // 类型/人群/场景/项目聚合
    function groupBy(list, key) {
      const map = {};
      for (const r of list) {
        const k = r[key];
        if (!map[k]) map[k] = [];
        map[k].push(r);
      }
      return Object.entries(map).map(([k, items]) => ({
        name: k,
        count: items.length,
        cost: sum(items, 'cost'),
        gmv: sum(items, 'gmv'),
        roi: sum(items, 'cost') > 0 ? (sum(items, 'gmv') - sum(items, 'cost')) / sum(items, 'cost') : 0,
        avgEng: avg(items, 'engagementRate'),
        avgFinish: avg(items, 'finishRate'),
        avgViews: avg(items, 'views')
      })).sort((a, b) => b.roi - a.roi);
    }

    const typeAll = groupBy(all, 'type');
    const typeDy = groupBy(dy, 'type');
    const typeXhs = groupBy(xhs, 'type');
    const audAll = groupBy(all, 'audience');
    const audDy = groupBy(dy, 'audience');
    const audXhs = groupBy(xhs, 'audience');
    const sceneAll = groupBy(all, 'scene');
    const sceneDy = groupBy(dy, 'scene');
    const sceneXhs = groupBy(xhs, 'scene');
    const projectAll = groupBy(all, 'project');
    const projectDy = groupBy(dy, 'project');
    const projectXhs = groupBy(xhs, 'project');

    // 矩阵：三维评分
    const dyEngMedian = median(dy.map(r => r.engagementRate));
    const xhsEngMedian = median(xhs.map(r => r.engagementRate));

    function matrixScore(r, platform) {
      const same = all.filter(x => x.platform === platform);
      const engVals = same.map(x => x.engagementRate);
      const attraction = percentileScore(engVals, r.engagementRate, true);
      const roiVals = same.map(x => x.roi);
      const efficiency = percentileScore(roiVals, r.roi, true);
      const gmvVals = same.map(x => x.gmv);
      const scale = percentileScore(gmvVals, r.gmv, true);
      return {
        attraction: +attraction.toFixed(1),
        efficiency: +efficiency.toFixed(1),
        scale: +scale.toFixed(1),
        matrix: +(attraction * 0.3 + efficiency * 0.4 + scale * 0.3).toFixed(1)
      };
    }

    const plot2d = [];
    const plot3d = [];
    let star = 0, potential = 0, cash = 0, ineff = 0, outlier = 0;
    const quadrantDy = {}, quadrantXhs = {};

    for (const r of all) {
      const m = matrixScore(r, r.platform);
      const threshold = r.platform === '抖音' ? dyEngMedian : xhsEngMedian;
      const highAttr = r.engagementRate >= threshold;
      let quadrant, desc;
      if (highAttr && r.roi >= 0) { quadrant = '明星内容'; desc = '高吸引力 · 高ROI'; star++; }
      else if (highAttr && r.roi < 0) { quadrant = '潜力内容'; desc = '高吸引力 · 低ROI'; potential++; }
      else if (!highAttr && r.roi >= 0) { quadrant = '收割型内容'; desc = '低吸引力 · 高ROI'; cash++; }
      else { quadrant = '低效内容'; desc = '低吸引力 · 低ROI'; ineff++; }
      if (r.roi >= 0 && m.attraction < 40) outlier++;

      if (r.platform === '抖音') quadrantDy[quadrant] = (quadrantDy[quadrant] || 0) + 1;
      else quadrantXhs[quadrant] = (quadrantXhs[quadrant] || 0) + 1;

      plot2d.push({
        x: m.attraction,
        y: r.roi,
        size: 5 + m.matrix / 10,
        color: quadrant,
        title: r.title,
        platform: r.platform,
        type: r.type,
        project: r.project,
        eng_rate: r.engagementRate.toFixed(2) + '%',
        gmv: fmtWan(r.gmv) + '万',
        matrix: m.matrix
      });

      plot3d.push({
        x: r.engagementRate,
        y: r.roi, // 用 ROI 近似转化率维度
        z: r.roi,
        size: Math.max(6, Math.sqrt(Math.max(0, r.gmv / 10000)) * 1.25),
        color: r.type,
        title: r.title,
        gmv: fmtWan(r.gmv) + '万'
      });
    }

    // TOP 榜单
    function topCards(list, sortKey, n) {
      return list.slice().sort((a, b) => b[sortKey] - a[sortKey]).slice(0, n).map(r => ({
        platform: r.platform,
        blogger: r.blogger,
        title: r.title,
        type: r.type,
        audience: r.audience,
        cost: fmtWan(r.cost) + '万',
        gmv: fmtWan(r.gmv) + '万',
        roi: +r.roi.toFixed(2),
        roas: +r.roas.toFixed(2),
        conv_rate: '',
        eng_rate: r.engagementRate.toFixed(2) + '%',
        reach: r.views >= 10000 ? (r.views / 10000).toFixed(1) + '万' : String(r.views),
        value: 0,
        matrix: matrixScore(r, r.platform).matrix,
        attraction_score: matrixScore(r, r.platform).attraction,
        efficiency_score: matrixScore(r, r.platform).efficiency,
        scale_score: matrixScore(r, r.platform).scale,
        quadrant: '',
        scenes: r.scene,
        finish_rate: r.finishRate ? r.finishRate.toFixed(2) + '%' : '',
        paid_ctr: r.paidCtr ? r.paidCtr.toFixed(2) + '%' : '',
        paid_a3: r.a3 ? (r.a3 >= 10000 ? (r.a3 / 10000).toFixed(1) + '万' : String(r.a3)) : '',
        link: r.link
      }));
    }

    const topRoi = topCards(all, 'roi', 15);
    const topValue = topCards(all, 'matrix', 15);
    const topDyRoi = topCards(dy, 'roi', 15);
    const topXhsRoi = topCards(xhs, 'roi', 15);
    const topEng = topCards(all, 'engagementRate', 15);
    const topMatrix = topCards(all, 'matrix', 15);
    const roiAttractionOutliers = all.filter(r => r.roi >= 0 && matrixScore(r, r.platform).attraction < 40)
      .sort((a, b) => b.roi - a.roi).slice(0, 15).map(r => topCards([r], 'roi', 1)[0]);

    // 结论
    const bestType = typeAll[0] || {};
    const bestAud = audAll[0] || {};
    const bestProject = projectAll[0] || {};
    const bestScene = sceneAll.sort((a, b) => b.gmv - a.gmv)[0] || {};

    const dataOverview = {
      timeRange: dateRange ? `${dateRange[0].toISOString().slice(0,10)} 至 ${dateRange[1].toISOString().slice(0,10)}` : '',
      allCount: all.length,
      dyCount: dy.length,
      xhsCount: xhs.length,
      totalCost: fmtWan(totalCost) + '万',
      totalGmv: fmtWan(totalGmv) + '万',
      overallRoi: +overallRoi.toFixed(2),
      overallEng: (avg(all, 'engagementRate') / 100).toFixed(4),
      dyRoi: +dyM.roi.toFixed(2),
      xhsRoi: +xhsM.roi.toFixed(2),
      closerToDeal: xhsM.roi > dyM.roi ? '小红书' : '抖音',
      betterForMind: dyM.avgEngagement > xhsM.avgEngagement ? '抖音' : '小红书',
      bestType: bestType.name || '',
      bestAud: bestAud.name || '',
      bestProject: bestProject.name || '',
      bestScene: bestScene.name || '',
      totalA3: dyM.paidA3 >= 10000 ? (dyM.paidA3 / 10000).toFixed(1) + '万' : String(dyM.paidA3),
      a3CostOverall: +(dyM.paidA3 > 0 ? totalCost / dyM.paidA3 : 0).toFixed(2),
      starCount: star,
      potentialCount: potential,
      cashCount: cash,
      ineffCount: ineff,
      outlierCount: outlier,
      dyEngMedian: dyEngMedian.toFixed(2) + '%',
      xhsEngMedian: xhsEngMedian.toFixed(2) + '%'
    };

    const overallConclusion = [
      `1. 整体表现：${dataOverview.timeRange} 期间 ${all.length} 条内容总投入 ${dataOverview.totalCost}，带来 GMV ${dataOverview.totalGmv}，综合 ROI ${dataOverview.overallRoi.toFixed(2)}。`,
      `2. 平台分工：${dataOverview.closerToDeal} 承担收割（ROI ${(dataOverview.closerToDeal === '小红书' ? xhsM.roi : dyM.roi).toFixed(2)}），${dataOverview.betterForMind} 承担心智种草；抖音 A3 总量 ${dataOverview.totalA3}，平均获客成本 ¥${dataOverview.a3CostOverall.toFixed(2)}。`,
      `3. 内容类型：优先复制「${bestType.name}」，同时关注其量效平衡。`,
      `4. 项目维度：打透「${bestProject.name}」，不同月份同一项目已合并统计。`,
      `5. 人群场景：打透「${bestAud.name}」与「${bestScene.name}」场景。`,
      `6. 下一步动作：① 对 Top 案例做达人二次合作 / 切片二创；② 对 ROI<0 但互动率高的内容优化组件 / 评论区承接；③ 对 A3 成本低的内容类型追加抖音投流；④ 对小红书 CTR 高的类型加大投流与搜索承接。`
    ];

    const lessons = [
      `内容类型优先做「${bestType.name}」：该类型平均 ROI ${bestType.roi.toFixed(2)}，投入产出最稳定。`,
      `目标人群优先打「${bestAud.name}」：该人群平均 ROI ${bestAud.roi.toFixed(2)}，与产品功能场景匹配度最高。`,
      `项目维度优先复制「${bestProject.name}」：该项目 ROI ${bestProject.roi.toFixed(2)}，内容策略与平台承接相对成熟。`,
      `高转化内容通常具备「具体场景 + 功能演示 + 行动引导」三重结构。`,
      `抖音适合「看后搜」和「A3 种草」规模化，小红书适合「搜索进店」和「加购成交」收割。`,
      `达人量级不是决定性因素，腰部/尾部达人如果内容类型和人群匹配，ROI 可能高于头部。`
    ];

    return {
      rows,
      dataOverview,
      platformSummary: { '抖音': dyM, '小红书': xhsM },
      radarData,
      typeAll, typeDy, typeXhs,
      audAll, audDy, audXhs,
      sceneAll, sceneDy, sceneXhs,
      projectAll, projectDy, projectXhs,
      plot2d, plot3d,
      quadrantSummary: { star, potential, cash, ineff, outlier },
      quadrantDy, quadrantXhs,
      topRoi, topValue, topDyRoi, topXhsRoi, topEng, topMatrix, roiAttractionOutliers,
      overallConclusion, lessons
    };
  }

  // ============================================================
  // 5. 渲染
  // ============================================================
  function renderAnalysis(result) {
    const container = document.getElementById('analysisResult');
    if (!container) return;
    container.style.display = 'block';
    const staticBox = document.getElementById('dashStatic');
    if (staticBox) staticBox.style.display = 'none';

    const ov = result.dataOverview;
    const ps = result.platformSummary;

    // 概览指标
    document.getElementById('anaTimeRange').textContent = ov.timeRange;
    document.getElementById('anaTotalCount').textContent = ov.allCount;
    document.getElementById('anaDyCount').textContent = ov.dyCount;
    document.getElementById('anaXhsCount').textContent = ov.xhsCount;
    document.getElementById('anaTotalCost').textContent = ov.totalCost;
    document.getElementById('anaTotalGmv').textContent = ov.totalGmv;
    document.getElementById('anaOverallRoi').textContent = ov.overallRoi.toFixed(2);
    document.getElementById('anaDyRoi').textContent = ov.dyRoi.toFixed(2);
    document.getElementById('anaXhsRoi').textContent = ov.xhsRoi.toFixed(2);
    document.getElementById('anaA3Cost').textContent = '¥' + ov.a3CostOverall.toFixed(2);

    // 雷达图
    const dims = ['传播力', '互动力', '转化力', 'ROI力', '综合价值'];
    Plotly.newPlot('radarChart', result.radarData.map(p => ({
      type: 'scatterpolar',
      r: [...p.data, p.data[0]],
      theta: [...dims, dims[0]],
      fill: 'toself',
      name: p.name
    })), {
      polar: { radialaxis: { visible: true, range: [0, 100] } },
      showlegend: true,
      margin: { t: 30, b: 30 }
    }, { responsive: true });

    // 平台 ROI/GMV 双轴
    Plotly.newPlot('platformBarChart', [
      { x: ['抖音', '小红书'], y: [ps['抖音'].roi, ps['小红书'].roi], type: 'bar', name: 'ROI', marker: { color: ['#3b82f6', '#f43f5e'] }, yaxis: 'y1' },
      { x: ['抖音', '小红书'], y: [ps['抖音'].gmvWan, ps['小红书'].gmvWan], type: 'scatter', mode: 'lines+markers', name: 'GMV(万)', marker: { color: '#10b981' }, yaxis: 'y2' }
    ], {
      yaxis: { title: 'ROI', side: 'left' },
      yaxis2: { title: 'GMV(万)', overlaying: 'y', side: 'right' },
      margin: { t: 20, b: 40 }
    }, { responsive: true });

    // 2D 矩阵
    renderMatrix2d(result);

    // 3D 气泡
    render3d(result);

    // 类型 ROI
    renderBar('typeRoiChart', result.typeAll.slice(0, 12), 'name', 'roi', '#3b82f6', '内容类型 ROI');
    renderBar('dyTypeChart', result.typeDy.slice(0, 10), 'name', 'roi', '#3b82f6', '抖音类型 ROI');
    renderBar('xhsTypeChart', result.typeXhs.slice(0, 10), 'name', 'roi', '#f43f5e', '小红书类型 ROI');

    // 人群 ROI
    renderBar('audRoiChart', result.audAll.slice(0, 12), 'name', 'roi', '#8b5cf6', '人群 ROI');

    // 项目 ROI
    renderBar('projectRoiChart', result.projectAll.slice(0, 12), 'name', 'roi', '#10b981', '项目 ROI');

    // TOP 榜单
    renderTopCards('topRoiList', result.topRoi);
    renderTopCards('topMatrixList', result.topMatrix);

    // 结论
    document.getElementById('overallConclusion').innerHTML = result.overallConclusion.map(c => `<li>${c}</li>`).join('');
    document.getElementById('lessonsList').innerHTML = result.lessons.map(l => `<li>${l}</li>`).join('');

    // 矩阵统计
    document.getElementById('matrixStats').innerHTML = `
      明星内容 <strong>${ov.starCount}</strong> · 潜力内容 <strong>${ov.potentialCount}</strong> ·
      收割型 <strong>${ov.cashCount}</strong> · 低效 <strong>${ov.ineffCount}</strong> ·
      异常点 <strong>${ov.outlierCount}</strong>
    `;
  }

  function renderBar(domId, data, xKey, yKey, color, title) {
    const el = document.getElementById(domId);
    if (!el) return;
    if (!data || !data.length) { el.innerHTML = '<p style="color:var(--muted)">暂无数据</p>'; return; }
    const colors = data.map(d => d[yKey] >= 0 ? '#16a34a' : '#dc2626');
    Plotly.newPlot(domId, [{
      x: data.map(d => d[xKey]), y: data.map(d => d[yKey]), type: 'bar',
      marker: { color: colors },
      text: data.map(d => d[yKey].toFixed(2)), textposition: 'outside'
    }], {
      margin: { t: 40, b: 100 },
      yaxis: { title: yKey.toUpperCase() },
      xaxis: { tickangle: -30, automargin: true },
      title: { text: title || '', font: { size: 13 } }
    }, { responsive: true });
  }

  function renderTopCards(domId, data) {
    const box = document.getElementById(domId);
    if (!box) return;
    if (!data || !data.length) { box.innerHTML = '<p style="color:var(--muted)">暂无数据</p>'; return; }
    box.innerHTML = data.map((it, i) => {
      const title = it.link ? `<a href="${escapeHtml(it.link)}" target="_blank" rel="noopener">${i + 1}. ${escapeHtml(it.title)}</a>` : `${i + 1}. ${escapeHtml(it.title)}`;
      return `<div class="top-card" style="background:rgba(255,255,255,0.6);border-radius:12px;padding:14px;margin-bottom:10px;">
        <div style="font-weight:600;font-size:14px;margin-bottom:6px;">${title}</div>
        <div style="font-size:12px;color:var(--muted);line-height:1.6;">
          <span class="chip">${it.platform}</span> <span class="chip tag2">${it.blogger}</span> <span class="chip tag3">${it.type}</span> <span class="chip">${it.audience}</span><br><br>
          ROI <strong>${it.roi}</strong> · 互动率 ${it.eng_rate} · 成本 ${it.cost} · GMV ${it.gmv} · 矩阵分 ${it.matrix}
        </div>
      </div>`;
    }).join('');
  }

  function renderMatrix2d(result) {
    const colors = { '明星内容': '#10b981', '潜力内容': '#3b82f6', '收割型内容': '#f59e0b', '低效内容': '#94a3b8' };
    const quadrants = ['明星内容', '潜力内容', '收割型内容', '低效内容'];
    const traces = quadrants.map(q => {
      const pts = result.plot2d.filter(d => d.color === q);
      return {
        type: 'scatter', mode: 'markers', name: q,
        x: pts.map(d => d.x), y: pts.map(d => d.y),
        text: pts.map(d => d.title),
        marker: { size: pts.map(d => d.size), opacity: 0.75, color: colors[q] },
        hovertemplate: `<b>%{text}</b><br>吸引力分: %{x:.1f}<br>ROI: %{y:.2f}<extra>${q}</extra>`
      };
    });
    const xs = result.plot2d.map(d => d.x);
    const ys = result.plot2d.map(d => d.y);
    const xMin = Math.min(...xs), xMax = Math.max(...xs);
    const yMin = Math.min(...ys), yMax = Math.max(...ys);
    Plotly.newPlot('matrix2dChart', traces, {
      shapes: [
        { type: 'line', x0: 50, x1: 50, y0: yMin * 1.05, y1: yMax * 1.05, line: { dash: 'dash', color: '#64748b' } },
        { type: 'line', x0: xMin * 0.95, x1: xMax * 1.05, y0: 0, y1: 0, line: { dash: 'dash', color: '#64748b' } }
      ],
      xaxis: { title: '内容吸引力评分', range: [xMin - 2, xMax + 2] },
      yaxis: { title: 'ROI' },
      margin: { t: 20, b: 60, l: 60 },
      legend: { orientation: 'h', y: 1.12 }
    }, { responsive: true });
  }

  function render3d(result) {
    const types = [...new Set(result.plot3d.map(d => d.color))];
    const palette = ['#3b82f6','#ef4444','#10b981','#f59e0b','#8b5cf6','#ec4899','#06b6d4','#84cc16','#f97316','#6366f1','#14b8a6','#d946ef'];
    // 2D 投影
    const traces2d = types.map((t, i) => ({
      type: 'scatter', mode: 'markers', name: t,
      x: result.plot3d.filter(d => d.color === t).map(d => d.x),
      y: result.plot3d.filter(d => d.color === t).map(d => d.z),
      text: result.plot3d.filter(d => d.color === t).map(d => d.title),
      marker: { size: result.plot3d.filter(d => d.color === t).map(d => d.size), opacity: 0.75, color: palette[i % palette.length] },
      hovertemplate: '互动率 %{x:.2f}%<br>ROI %{y:.2f}<extra>%{text}</extra>'
    }));
    Plotly.newPlot('bubble2dChart', traces2d, {
      xaxis: { title: '互动率 (%)' }, yaxis: { title: 'ROI' },
      margin: { t: 20, b: 60, l: 60 }, legend: { orientation: 'h', y: -0.25 }
    }, { responsive: true });

    // 3D
    const traces3d = types.map((t, i) => ({
      type: 'scatter3d', mode: 'markers', name: t,
      x: result.plot3d.filter(d => d.color === t).map(d => d.x),
      y: result.plot3d.filter(d => d.color === t).map(d => d.y),
      z: result.plot3d.filter(d => d.color === t).map(d => d.z),
      text: result.plot3d.filter(d => d.color === t).map(d => d.title),
      marker: { size: result.plot3d.filter(d => d.color === t).map(d => d.size), opacity: 0.8, color: palette[i % palette.length] },
      hovertemplate: '互动率 %{x:.2f}%<br>ROI %{y:.2f}<br>ROI %{z:.2f}<extra>%{text}</extra>'
    }));
    Plotly.newPlot('bubble3dChart', traces3d, {
      scene: { xaxis: { title: '互动率 (%)' }, yaxis: { title: 'ROI' }, zaxis: { title: 'ROI' } },
      margin: { t: 20, b: 20 }, legend: { orientation: 'h', y: -0.1 }
    }, { responsive: true });
  }

  // ============================================================
  // 6. 文件上传处理
  // ============================================================
  function onFile(file) {
    const statusEl = document.getElementById('uploadStatus');
    if (statusEl) statusEl.textContent = '正在解析…';
    const ext = (file.name.split('.').pop() || '').toLowerCase();

    if (ext === 'csv') {
      Papa.parse(file, {
        header: true,
        skipEmptyLines: true,
        complete: results => {
          const rows = results.data;
          const platform = detectPlatformFromRows(rows);
          const parsed = parseSheet(rows, platform, null, null);
          runAnalyze(parsed);
        },
        error: err => { if (statusEl) statusEl.textContent = 'CSV 解析失败：' + err.message; }
      });
    } else {
      const reader = new FileReader();
      reader.onload = e => {
        const data = new Uint8Array(e.target.result);
        const workbook = XLSX.read(data, { type: 'array' });
        const sheetInfos = detectSheets(workbook);
        let allRows = [];
        for (const info of sheetInfos) {
          const ws = workbook.Sheets[info.name];
          const rows = XLSX.utils.sheet_to_json(ws, { defval: '' });
          let projectCol = info.projectCol;
          if (projectCol === '__FIRST_COL__') {
            const first = rows.length ? Object.keys(rows[0])[0] : null;
            projectCol = first;
          }
          const parsed = parseSheet(rows, info.platform, projectCol, null);
          allRows = allRows.concat(parsed);
        }
        runAnalyze(allRows);
      };
      reader.readAsArrayBuffer(file);
    }
  }

  function detectPlatformFromRows(rows) {
    for (const r of rows) {
      const p = String(r['平台'] || '').trim();
      if (p === '抖音') return '抖音';
      if (['红书','小红书'].includes(p)) return '小红书';
    }
    return '抖音';
  }

  function runAnalyze(rows) {
    const statusEl = document.getElementById('uploadStatus');
    if (!rows.length) {
      if (statusEl) statusEl.textContent = '未解析到有效数据，请检查文件格式。';
      return;
    }
    const dates = rows.map(r => r.date).filter(d => d && !isNaN(d.getTime())).sort((a, b) => a - b);
    const dateRange = dates.length ? [dates[0], dates[dates.length - 1]] : [new Date('2026-05-04'), new Date('2026-08-04')];
    const result = analyze(rows, dateRange);
    window.__lastAnalysis = result;
    renderAnalysis(result);
    if (statusEl) statusEl.textContent = `分析完成：${rows.length} 条有效内容`;
  }

  // ============================================================
  // 7. 初始化
  // ============================================================
  function init() {
    const input = document.getElementById('dataUpload');
    const drop = document.getElementById('uploadDrop');
    if (!input) return;

    input.addEventListener('change', e => {
      const f = e.target.files[0];
      if (f) onFile(f);
    });

    if (drop) {
      drop.addEventListener('click', () => input.click());
      ['dragenter','dragover','dragleave','drop'].forEach(evt => {
        drop.addEventListener(evt, e => { e.preventDefault(); e.stopPropagation(); }, false);
      });
      ['dragenter','dragover'].forEach(evt => {
        drop.addEventListener(evt, () => drop.classList.add('dragover'), false);
      });
      ['dragleave','drop'].forEach(evt => {
        drop.addEventListener(evt, () => drop.classList.remove('dragover'), false);
      });
      drop.addEventListener('drop', e => {
        const f = e.dataTransfer.files[0];
        if (f) onFile(f);
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
