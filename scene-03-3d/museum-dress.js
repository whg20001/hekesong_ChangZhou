// 巧排任务 · 展馆细化：材质细节、布景道具、氛围（光柱、浮尘、窗外的雨）
// 只在网页端生成，不改 Codex 的模型文件。坐标一律用 Blender 平面图坐标（米，Z 向上），由 B() 转成 three。
import * as THREE from 'three';

export const B = (x, y, z = 0) => new THREE.Vector3(x, z, -y);
const R = (a, b) => a + Math.random() * (b - a);

/* ================= 材质细节：世界坐标噪声（木纹、墙面、砖、金属） ================= */
// 模型里的材质都是纯色，这里在着色器里叠一层程序化细节；不依赖 UV，也不需要贴图
const NOISE = `
varying vec3 vWP; varying vec3 vWN;
uniform float uTime;
float dh3(vec3 p){ p = fract(p * .3183099 + .1); p *= 17.; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
float dn3(vec3 x){ vec3 i = floor(x), f = fract(x); f = f * f * (3. - 2. * f);
  return mix(mix(mix(dh3(i), dh3(i + vec3(1,0,0)), f.x), mix(dh3(i + vec3(0,1,0)), dh3(i + vec3(1,1,0)), f.x), f.y),
             mix(mix(dh3(i + vec3(0,0,1)), dh3(i + vec3(1,0,1)), f.x), mix(dh3(i + vec3(0,1,1)), dh3(i + vec3(1,1,1)), f.x), f.y), f.z); }
float dfbm(vec3 p){ float a = .5, s = 0.; for (int i = 0; i < 4; i++) { s += a * dn3(p); p *= 2.03; a *= .5; } return s; }
// 墙脚、墙顶变暗一点，像有环境光遮蔽
float wallAO(){ return abs(vWN.y) < .5 ? mix(.68, 1., smoothstep(0., 1.1, vWP.y)) * mix(.82, 1., smoothstep(4.25, 3.3, vWP.y)) : 1.; }
`;
const COLOR = {
  wood: `{ bool hz = abs(vWN.y) > .7;
    vec3 q = hz ? vec3(vWP.x * 1.1, 0., vWP.z * 13.) : vec3(vWP.x * 9., vWP.y * .9, vWP.z * 9.);
    float g = dfbm(q), ring = smoothstep(.35, .65, fract(g * 5.5));
    diffuseColor.rgb *= mix(.8, 1.1, g) * (.95 + .07 * ring) * wallAO(); }`,
  plaster: `{ float g = dfbm(vWP * 1.2) * .1 + dn3(vWP * 38.) * .035;
    if (vWN.y > .7) { float sp = step(.9, dh3(floor(vWP * 95.))); diffuseColor.rgb *= .94 + g; diffuseColor.rgb = mix(diffuseColor.rgb, diffuseColor.rgb * vec3(.62,.58,.52), sp * .55); }
    else diffuseColor.rgb *= (.93 + g) * wallAO(); }`,
  brick: `{ float g = dfbm(vWP * vec3(2.6, 5.5, 2.6)); diffuseColor.rgb *= (.8 + .34 * g + .05 * dn3(vWP * 30.)) * wallAO(); }`,
  metal: `{ diffuseColor.rgb *= .9 + .14 * dfbm(vWP * 3.); }`,
  // 天窗玻璃：落在上面的雨滴（往下流的细痕 + 亮点）
  glass: `{ /* 天窗用水平面坐标，门窗玻璃用竖直面坐标 */ vec2 p = abs(vWN.y) > .5 ? vWP.xz * 9. : vec2(vWP.x + vWP.z, vWP.y) * 9.;
    float col = floor(p.x); float t = uTime * (.6 + dh3(vec3(col, 1., 3.)) * .8);
    float streak = smoothstep(.96, 1., fract(p.y * .15 + t + dh3(vec3(col, 2., 7.)))) * step(.55, dh3(vec3(col, 5., 1.)));
    float drop = step(.985, dh3(floor(vec3(vWP.xz * 40., floor(uTime * .5)))));
    diffuseColor.rgb += vec3(.55, .65, .8) * (streak * .5 + drop * .8); diffuseColor.a = min(1., diffuseColor.a + streak * .25 + drop * .4); }`,
};
const ROUGH = {
  wood: `roughnessFactor *= .85 + .3 * dn3(vWP * 6.);`,
  plaster: ``, brick: `roughnessFactor = max(roughnessFactor, .85);`,
  metal: `roughnessFactor *= .7 + .6 * dfbm(vWP * 7.);`, glass: ``,
};
export const detailUniforms = { uTime: { value: 0 } };
function categoryOf(m) {
  const n = (m.name || '').toLowerCase();
  if (m.map) return null;
  if (/glass/.test(n)) return 'glass';
  if (/wood|walnut|^tea$/.test(n)) return 'wood';
  if (/ivory|^green|greenlight|plaster|mortar/.test(n)) return 'plaster';
  if (/brick/.test(n)) return 'brick';
  if (/iron|brass|copper|bronze|steel/.test(n)) return 'metal';
  return null;
}
export function applyDetail(root) {
  root.traverse(o => {
    if (!o.isMesh || !o.visible) return;
    for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
      if (!m || !m.isMeshStandardMaterial || m.userData.detail) continue;
      const cat = m.userData.cat || categoryOf(m); if (!cat) continue;
      m.userData.detail = cat;
      m.onBeforeCompile = sh => {
        sh.uniforms.uTime = detailUniforms.uTime;
        sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying vec3 vWP; varying vec3 vWN;')
          .replace('#include <fog_vertex>', '#include <fog_vertex>\nvWP = (modelMatrix * vec4(transformed, 1.)).xyz; vWN = normalize(mat3(modelMatrix) * objectNormal);');
        sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\n' + NOISE)
          .replace('#include <color_fragment>', '#include <color_fragment>\n' + COLOR[cat])
          .replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\n' + ROUGH[cat]);
      };
      m.customProgramCacheKey = () => 'detail-' + cat;
      m.needsUpdate = true;
    }
  });
}

/* ================= 画布贴图小工具 ================= */
function tex(w, h, draw, opt = {}) {
  const cv = document.createElement('canvas'); cv.width = w; cv.height = h;
  draw(cv.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  if (opt.repeat) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(...opt.repeat); }
  return t;
}
const grain = (c, w, h, n = 300, a = .05) => { for (let i = 0; i < n; i++) { c.fillStyle = `rgba(60,40,20,${(Math.random() * a).toFixed(3)})`; c.fillRect(Math.random() * w, Math.random() * h, 1 + Math.random() * 3, 1 + Math.random() * 3); } };

/* ================= 布景道具 ================= */
// 都是低多边形的简单几何 + 纯色，和 Codex 的模型同一套配色；地上的大件加碰撞盒
export function buildProps(ctx) {
  const { scene, N, colBoxes, fonts } = ctx;
  const group = new THREE.Group(); group.name = 'DRESS'; scene.add(group);
  const mats = {};
  const mat = (col, name = '', o = {}) => {
    const k = col + name + JSON.stringify(o);
    if (!mats[k]) { mats[k] = new THREE.MeshStandardMaterial(Object.assign({ color: col, roughness: .82, metalness: 0 }, o)); mats[k].name = name; }
    return mats[k];
  };
  const M = {
    walnut: mat('#5f3a24', 'walnut'), wood: mat('#9a6a43', 'wood'), woodLight: mat('#b98a5a', 'woodLight'),
    iron: mat('#2a2a28', 'iron', { metalness: .6, roughness: .55 }), brass: mat('#c9a24a', 'brass', { metalness: .85, roughness: .32 }),
    copper: mat('#b87333', 'copper', { metalness: .8, roughness: .38 }), red: mat('#8a3330', 'red'), cloth: mat('#d9c9a3', 'cloth', { roughness: .95 }),
    sack: mat('#c8b48a', 'sack', { roughness: 1 }), green: mat('#2f5d50', 'green'), crate: mat('#a07a4c', 'wood'), drum: mat('#4a5a52', 'iron', { metalness: .5, roughness: .5 }),
    drumRed: mat('#8c3a2a', 'iron', { metalness: .45, roughness: .55 }), pipe: mat('#5a3a2e', 'iron', { metalness: .55, roughness: .5 }), leaf: mat('#3e6b4a', 'leaf'), pot: mat('#a84533', 'pot'),
  };
  const add = (geo, m, p, rotZ = 0, cast = true) => {
    const o = new THREE.Mesh(geo, m); o.position.copy(p); o.rotation.y = rotZ; o.castShadow = cast; o.receiveShadow = true; group.add(o); return o;
  };
  // 长方体：w 沿 X、d 沿 Y、h 沿 Z；(x, y) 为底面中心，z 为底面高度
  const box = (w, d, h, m, x, y, z = 0, rot = 0) => add(new THREE.BoxGeometry(w, h, d), m, B(x, y, z + h / 2), rot);
  const cyl = (r, h, m, x, y, z = 0, seg = 14, r2 = r) => add(new THREE.CylinderGeometry(r2, r, h, seg), m, B(x, y, z + h / 2));
  const block = (x0, x1, y0, y1, h = 1.2) => colBoxes.push({ x0, x1, z0: -y1, z1: -y0, y0: 0, y1: h });
  const plane = (w, h, map, p, rotY, o = {}) => {
    const m = new THREE.MeshStandardMaterial(Object.assign({ map, roughness: .9, transparent: !!o.transparent, alphaTest: o.alphaTest || 0 }, o.mat || {}));
    const g = new THREE.Mesh(new THREE.PlaneGeometry(w, h), m); g.position.copy(p); g.rotation.y = rotY; g.receiveShadow = true; group.add(g); return g;
  };
  const floorDecal = (w, d, map, x, y, rot = 0, z = .006) => {
    const g = new THREE.Mesh(new THREE.PlaneGeometry(w, d), new THREE.MeshStandardMaterial({ map, roughness: .95, transparent: true, polygonOffset: true, polygonOffsetFactor: -2 }));
    g.rotation.x = -Math.PI / 2; g.rotation.z = rot; g.position.copy(B(x, y, z)); g.receiveShadow = true; group.add(g); return g;
  };
  // 挂在墙上的画框：face = 'N' | 'S' | 'E' | 'W'（画面朝向）
  const FACE = { N: 0, S: Math.PI, E: -Math.PI / 2, W: Math.PI / 2 };
  const frame = (w, h, map, x, y, z, face, frameCol = '#5f3a24') => {
    const g = new THREE.Group(); g.position.copy(B(x, y, z)); g.rotation.y = FACE[face] + Math.PI;   // 平面默认朝 +Z（Blender -Y）
    const fm = mat(frameCol, 'walnut'), t = .05;
    [[w + t * 2, t, 0, h / 2 + t / 2], [w + t * 2, t, 0, -h / 2 - t / 2], [t, h, -w / 2 - t / 2, 0], [t, h, w / 2 + t / 2, 0]].forEach(([a, b, px, py]) => {
      const e = new THREE.Mesh(new THREE.BoxGeometry(a, b, .04), fm); e.position.set(px, py, .02); g.add(e);
    });
    const pic = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshStandardMaterial({ map, roughness: .85 })); pic.position.z = .012; g.add(pic);
    group.add(g); return g;
  };
  const SERIF = fonts.serif, BRUSH = fonts.brush;

  /* ---------- 序厅 ---------- */
  // 红地毯：从入口铺到铜像前
  floorDecal(1.5, 3.5, tex(256, 600, (c, w, h) => {
    c.fillStyle = '#7d2a24'; c.fillRect(0, 0, w, h); c.strokeStyle = '#c9a24a'; c.lineWidth = 10; c.strokeRect(14, 14, w - 28, h - 28);
    c.lineWidth = 3; c.strokeRect(28, 28, w - 56, h - 56);
    for (let y = 80; y < h - 60; y += 110) { c.save(); c.translate(w / 2, y); c.rotate(Math.PI / 4); c.strokeRect(-18, -18, 36, 36); c.restore(); }
    grain(c, w, h, 900, .12);
  }), 0, 2.95);
  // 铜像四周的隔离栏
  const posts = [[-.95, 4.7], [.95, 4.7], [-.95, 6.3], [.95, 6.3]];
  posts.forEach(([x, y]) => stanchion(x, y));
  rope(posts[0], posts[1]); rope(posts[0], posts[2]); rope(posts[1], posts[3]); block(-1.05, 1.05, 4.6, 6.4, 1);
  // 入口内侧的参观路线图（西墙南段）
  frame(1.0, .7, tex(500, 350, (c, w, h) => {
    c.fillStyle = '#f7e9cc'; c.fillRect(0, 0, w, h); c.fillStyle = '#1b2a4a'; c.font = `38px ${BRUSH}`; c.textAlign = 'center'; c.fillText('参观路线', w / 2, 52);
    const rm = [[.06, .52, .3, .38, '展厅一', '#e2674a'], [.06, .16, .4, .34, '展厅二', '#2f8f83'], [.48, .16, .46, .34, '展厅三', '#e0a526'], [.38, .52, .28, .38, '序厅', '#b9ab8c'], [.68, .52, .26, .38, '尾厅', '#1b2a4a']];
    for (const [x, y, rw, rh, t, col] of rm) { c.fillStyle = col; c.fillRect(x * w, y * h + 40, rw * w - 6, rh * h - 50); c.fillStyle = '#fff'; c.font = `22px ${SERIF}`; c.fillText(t, (x + rw / 2) * w, (y + rh / 2) * h + 25); }
    c.strokeStyle = '#1b2a4a'; c.lineWidth = 4; c.setLineDash([10, 8]); c.beginPath(); c.moveTo(.52 * w, .98 * h); c.lineTo(.52 * w, .78 * h); c.lineTo(.2 * w, .78 * h); c.lineTo(.2 * w, .4 * h); c.lineTo(.7 * w, .4 * h); c.lineTo(.8 * w, .75 * h); c.stroke();
  }), -3.86, 1.1, 1.65, 'E');
  // 地面导视箭头：序厅 → 展厅一，尾厅 → 出口
  const arrowTex = tex(128, 128, c => { c.fillStyle = '#c9a24a'; c.beginPath(); c.moveTo(64, 8); c.lineTo(118, 70); c.lineTo(84, 70); c.lineTo(84, 120); c.lineTo(44, 120); c.lineTo(44, 70); c.lineTo(10, 70); c.closePath(); c.fill(); });
  [[-2.6, 3, Math.PI / 2], [-3.4, 3, Math.PI / 2], [10.4, 6.6, Math.PI], [10.6, 5.4, Math.PI], [11.1, 4, -Math.PI / 2]].forEach(([x, y, r]) => floorDecal(.42, .42, arrowTex, x, y, r));
  // 入口地垫
  floorDecal(1.6, .9, tex(256, 144, (c, w, h) => { c.fillStyle = '#3a3226'; c.fillRect(0, 0, w, h); c.strokeStyle = '#5a4a36'; c.lineWidth = 4; for (let x = 8; x < w; x += 12) { c.beginPath(); c.moveTo(x, 6); c.lineTo(x, h - 6); c.stroke(); } }), 0, .6);

  /* ---------- 展厅一 · 小店 ---------- */
  // 米袋、木桶、竹筐：堆在门脸两侧
  [[-10.6, 7.25, 0], [-10.05, 7.3, 0], [-10.35, 7.25, .42]].forEach(([x, y, z]) => sack(x, y, z));
  block(-10.95, -9.7, 6.95, 7.7, 1);
  cyl(.3, .78, M.wood, -10.55, .75, 0, 16, .27); cyl(.31, .05, M.iron, -10.55, .75, .18, 16); cyl(.29, .05, M.iron, -10.55, .75, .62, 16); block(-10.9, -10.2, .4, 1.1, 1);
  cyl(.24, .32, mat('#b98a4a', 'woodLight'), -9.95, .65, 0, 12, .3);
  // 门脸檐下的红灯笼
  [[-10.75, 1.6], [-10.75, 6.4]].forEach(([x, y]) => lantern(x, y, 2.55));
  // 老照片：南墙、北墙
  frame(.9, .65, oldPhoto('street'), -7.6, .12, 1.75, 'N'); frame(.6, .8, oldPhoto('portrait'), -5.9, .12, 1.7, 'N');
  frame(.9, .65, oldPhoto('shop'), -5.6, 7.88, 1.75, 'S');
  // 柜台前的旧地毯
  floorDecal(1.2, 2.4, tex(200, 400, (c, w, h) => { c.fillStyle = '#5a3a2a'; c.fillRect(0, 0, w, h); c.strokeStyle = '#c9a24a'; c.lineWidth = 6; c.strokeRect(10, 10, w - 20, h - 20); c.fillStyle = '#8a3330'; c.fillRect(30, 30, w - 60, h - 60); grain(c, w, h, 600, .15); }), -7.8, 4.0);

  /* ---------- 展厅二 · 茶室 ---------- */
  // 茶桌下的席子
  floorDecal(3.0, 2.6, tex(400, 346, (c, w, h) => {
    c.fillStyle = '#c4a46a'; c.fillRect(0, 0, w, h); c.strokeStyle = 'rgba(90,60,20,.25)'; c.lineWidth = 2;
    for (let y = 0; y < h; y += 6) { c.beginPath(); c.moveTo(0, y); c.lineTo(w, y); c.stroke(); }
    c.strokeStyle = '#2f5d50'; c.lineWidth = 12; c.strokeRect(6, 6, w - 12, h - 12);
  }), -7.0, 12.9);
  // 西墙北段的书法挂轴
  frame(.55, 1.5, tex(220, 600, (c, w, h) => {
    c.fillStyle = '#efe2c2'; c.fillRect(0, 0, w, h); c.fillStyle = '#7a5a32'; c.fillRect(0, 0, w, 26); c.fillRect(0, h - 26, w, 26);
    c.fillStyle = '#1d1d1b'; c.font = `150px ${BRUSH}`; c.textAlign = 'center'; c.fillText('统', w / 2, 200); c.fillText('筹', w / 2, 390);
    c.fillStyle = '#b5321f'; c.fillRect(w / 2 + 30, 470, 34, 34);
  }), -11.86, 14.6, 1.85, 'E', '#7a5a32');
  // 东墙的书架
  bookcase(-2.3, 14.75);
  // 盆栽
  plant(-11.35, 15.35, 1.4); plant(-2.6, 8.6, 1.1);

  /* ---------- 展厅三 · 车间 ---------- */
  // 黄黑警示线围住熔炉、控制台、黑板这一片
  const stripe = tex(256, 32, (c, w, h) => { c.fillStyle = '#e0b430'; c.fillRect(0, 0, w, h); c.fillStyle = '#1d1d1b'; for (let x = -32; x < w; x += 32) { c.beginPath(); c.moveTo(x, h); c.lineTo(x + 16, 0); c.lineTo(x + 32, 0); c.lineTo(x + 16, h); c.fill(); } }, { repeat: [8, 1] });
  const zone = [2.2, 10.4, 12.75, 15.2];
  const line = (x0, y0, x1, y1) => { const len = Math.hypot(x1 - x0, y1 - y0), t = stripe.clone(); t.needsUpdate = true; t.repeat.set(len / 1.2, 1); floorDecal(len, .1, t, (x0 + x1) / 2, (y0 + y1) / 2, Math.atan2(y1 - y0, x1 - x0) - 0); };
  line(zone[0], zone[2], zone[1], zone[2]); line(zone[0], zone[2], zone[0], zone[3]); line(zone[1], zone[2], zone[1], zone[3]);
  // 沿北墙的管道，转到西、东两侧落地
  pipeRun([[1.0, 15.25, 3.85], [9.7, 15.25, 3.85], [9.7, 15.25, .05]]);         // 沿展墙顶、高窗上方，东头落地
  pipeRun([[10.4, 15.78, 3.6], [10.4, 15.78, .05]], .05, M.drumRed);
  pipeRun([[-1.8, 15.78, 3.6], [-1.8, 15.78, .05]], .05, M.drumRed);
  // 木箱和油桶：东侧空地
  [[11.2, 9.0, 0, .8], [10.35, 9.0, 0, .8], [11.2, 9.0, .8, .8], [10.75, 9.85, 0, .6]].forEach(([x, y, z, s]) => crate(x, y, z, s));
  block(9.9, 11.65, 8.55, 10.2, 1.6);
  [[11.3, 11.4, M.drum], [10.68, 11.6, M.drumRed], [11.25, 12.05, M.drum]].forEach(([x, y, m]) => drum(x, y, m));
  block(10.3, 11.65, 11.05, 12.4, 1);
  // 工作台上方的工业吊灯、车间中部两盏
  [[0, 13.9], [5.2, 10.2], [9.6, 10.6]].forEach(([x, y]) => hangLamp(x, y));
  // 工具挂板（北墙，工作台后）
  frame(1.6, .9, tex(480, 270, (c, w, h) => {
    c.fillStyle = '#7a5a3a'; c.fillRect(0, 0, w, h); c.fillStyle = 'rgba(0,0,0,.25)';
    for (let y = 18; y < h; y += 22) for (let x = 18; x < w; x += 22) { c.beginPath(); c.arc(x, y, 3, 0, 7); c.fill(); }
    c.fillStyle = '#2a2a28'; c.strokeStyle = '#2a2a28'; c.lineWidth = 10; c.lineCap = 'round';
    c.beginPath(); c.moveTo(60, 60); c.lineTo(60, 200); c.stroke(); c.beginPath(); c.arc(60, 60, 22, 0, 7); c.stroke();          // 扳手
    c.fillRect(120, 50, 16, 110); c.fillRect(104, 160, 48, 50);                                                                 // 锤子
    c.beginPath(); c.moveTo(200, 50); c.lineTo(240, 200); c.moveTo(260, 50); c.lineTo(220, 200); c.stroke();                     // 钳子
    c.fillStyle = '#c9a24a'; c.fillRect(300, 60, 140, 20); for (let i = 0; i < 14; i++) c.fillRect(300 + i * 10, 80, 2, i % 5 ? 8 : 16);   // 量尺
    c.strokeStyle = '#c0503a'; c.lineWidth = 8; c.beginPath(); c.arc(370, 180, 40, 0, Math.PI * 1.6); c.stroke();                  // 线圈
  }), 0.05, 15.92, 1.85, 'S');
  // 南墙的海报
  frame(1.2, 1.6, tex(360, 480, (c, w, h) => {
    c.fillStyle = '#e8d6a8'; c.fillRect(0, 0, w, h); c.fillStyle = '#b5321f'; c.fillRect(0, 0, w, 120);
    c.fillStyle = '#f7e9cc'; c.font = `76px ${BRUSH}`; c.textAlign = 'center'; c.fillText('优选法', w / 2, 88);
    c.fillStyle = '#1b2a4a'; c.font = `30px ${SERIF}`; c.fillText('少做试验 · 找到最好', w / 2, 170);
    c.strokeStyle = '#1b2a4a'; c.lineWidth = 6; c.beginPath(); c.moveTo(40, 380); c.lineTo(w - 40, 380); c.stroke();
    c.beginPath(); c.moveTo(40, 370); for (let x = 0; x <= 280; x += 4) c.lineTo(40 + x, 370 - 140 * Math.exp(-Math.pow((x - 173) / 70, 2))); c.stroke();
    c.fillStyle = '#b5321f'; c.beginPath(); c.arc(40 + 173, 230, 12, 0, 7); c.fill(); c.font = `bold 34px ${SERIF}`; c.fillText('0.618', 40 + 173, 440);
    grain(c, w, h, 500, .08);
  }), 4.2, 8.12, 1.9, 'N');

  /* ---------- 尾厅 ---------- */
  stanchion(6.3, 5.45); stanchion(9.7, 5.45); rope([6.3, 5.45], [9.7, 5.45]); block(6.2, 9.8, 5.35, 5.55, 1);
  // 西墙三幅“黄金分割”小画
  [['rect', 1.6], ['sun', 3.6], ['shell', 5.6]].forEach(([k, y]) => frame(.8, .8, goldenArt(k), 4.12, y, 1.75, 'E'));
  // 长凳（靠西墙，面朝出口）
  box(.45, 1.8, .06, M.walnut, 4.55, 4.0, .42); [3.25, 4.75].forEach(y => box(.38, .06, .42, M.iron, 4.55, y)); block(4.3, 4.8, 3.1, 4.9, .5);
  plant(4.5, 7.5, 1.3); plant(11.5, 7.4, 1.3);

  /* ---------- 入口门外：雨夜街景（透过玻璃门看到） ---------- */
  const street = plane(10, 5, tex(1024, 512, (c, w, h) => {
    const g = c.createLinearGradient(0, 0, 0, h); g.addColorStop(0, '#0b1426'); g.addColorStop(1, '#1a2238'); c.fillStyle = g; c.fillRect(0, 0, w, h);
    c.fillStyle = '#060b16'; [[0, 210, 180], [170, 160, 140], [300, 230, 200], [520, 140, 160], [690, 200, 130], [820, 170, 210]].forEach(([x, y, bw]) => c.fillRect(x, y, bw, h - y));
    for (let i = 0; i < 60; i++) { c.fillStyle = `rgba(255,${190 + Math.random() * 40 | 0},120,${R(.3, .8).toFixed(2)})`; c.fillRect(R(0, w), R(200, 420), 8, 10); }
    const lg = c.createRadialGradient(780, 300, 4, 780, 300, 140); lg.addColorStop(0, 'rgba(255,200,120,.9)'); lg.addColorStop(1, 'rgba(255,200,120,0)'); c.fillStyle = lg; c.fillRect(600, 140, 360, 340);
    c.fillStyle = '#1b2232'; c.fillRect(776, 300, 6, 212);
  }), B(0, -6, 2.2), Math.PI, { mat: { emissive: '#ffffff', emissiveIntensity: .5, roughness: 1 } });
  street.material.emissiveMap = street.material.map; street.castShadow = false;

  // 道具材质也套上细节着色
  applyDetail(group);
  return group;

  /* ---------- 道具构件 ---------- */
  function stanchion(x, y) {
    const tpl = N.Common_stanchion;
    if (tpl) { const s = tpl.clone(); s.position.copy(B(x, y)); group.add(s); s.traverse(o => { o.castShadow = true; }); }
    else { cyl(.03, .95, M.brass, x, y); cyl(.13, .03, M.brass, x, y); }
  }
  function rope(a, b) {
    const tpl = N.Common_rope; if (!tpl) return;
    const r = tpl.clone(), d = Math.hypot(b[0] - a[0], b[1] - a[1]);
    r.position.copy(B(a[0], a[1], tpl.position.y)); r.scale.x = d; r.rotation.y = Math.atan2(b[1] - a[1], b[0] - a[0]);
    group.add(r);
  }
  function sack(x, y, z) {
    const g = new THREE.SphereGeometry(.3, 10, 7); g.scale(1, .62, .78);
    const o = add(g, M.sack, B(x, y, z + .2)); o.rotation.y = R(-.4, .4);
    cyl(.06, .08, M.sack, x, y, z + .38, 8);
  }
  function lantern(x, y, z) {
    const lm = new THREE.MeshStandardMaterial({ color: '#c0392b', emissive: '#ff5a2a', emissiveIntensity: 1.4, roughness: .7 });
    const g = new THREE.SphereGeometry(.2, 14, 10); g.scale(1, 1.15, 1);
    add(g, lm, B(x, y, z), 0, false);
    cyl(.1, .05, M.iron, x, y, z + .2, 10); cyl(.1, .05, M.iron, x, y, z - .25, 10);
    cyl(.008, .55, M.iron, x, y, z + .25, 4);
    const t = cyl(.015, .25, mat('#e0a526', 'tassel'), x, y, z - .5, 6); t.castShadow = false;
  }
  function crate(x, y, z, s) {
    box(s, s, s, M.crate, x, y, z);
    const e = .035; [[s + .01, e, s + .01, 0, -s / 2 + e / 2], [s + .01, e, s + .01, 0, s / 2 - e / 2]].forEach(([a, b, c, dx, dy]) => box(a, b, c, M.walnut, x + dx, y + dy, z - .005));
    box(s + .012, s + .012, e * 1.4, M.walnut, x, y, z + s * .45);
  }
  function drum(x, y, m) { cyl(.3, .9, m, x, y, 0, 18); [.08, .45, .82].forEach(z => cyl(.305, .025, M.iron, x, y, z, 18)); cyl(.05, .02, M.iron, x + .14, y, .9, 8); }
  function hangLamp(x, y) {
    cyl(.008, 1.1, M.iron, x, y, 3.08, 4);
    const shade = add(new THREE.ConeGeometry(.28, .22, 16, 1, true), mat('#2f5d50', 'green', { side: THREE.DoubleSide, metalness: .4, roughness: .5 }), B(x, y, 2.97));
    shade.castShadow = false;
    add(new THREE.SphereGeometry(.07, 10, 8), new THREE.MeshStandardMaterial({ color: '#fff3d6', emissive: '#ffd08a', emissiveIntensity: 2.2 }), B(x, y, 2.86), 0, false);
  }
  function pipeRun(pts, r = .07, m = M.pipe) {
    for (let i = 0; i < pts.length - 1; i++) {
      const a = B(...pts[i]), b = B(...pts[i + 1]), len = a.distanceTo(b);
      const p = new THREE.Mesh(new THREE.CylinderGeometry(r, r, len, 12), m);
      p.position.copy(a).add(b).multiplyScalar(.5); p.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), b.clone().sub(a).normalize());
      p.castShadow = true; group.add(p);
      const j = new THREE.Mesh(new THREE.SphereGeometry(r * 1.35, 10, 8), m); j.position.copy(b); group.add(j);
      for (let k = 1; k < len / 1.6; k++) { const f = new THREE.Mesh(new THREE.CylinderGeometry(r * 1.3, r * 1.3, .05, 12), m); f.position.lerpVectors(a, b, k * 1.6 / len); f.quaternion.copy(p.quaternion); group.add(f); }
    }
  }
  function bookcase(x, y) {
    const w = .35, d = 1.6, h = 2.0;
    box(w, d, .04, M.walnut, x, y, 0); box(w, d, .04, M.walnut, x, y, h - .04);
    box(w, .04, h, M.walnut, x, y - d / 2, 0); box(w, .04, h, M.walnut, x, y + d / 2, 0); box(.03, d, h, M.walnut, x + w / 2 - .015, y, 0);
    const cols = ['#8a3330', '#2f5d50', '#1b2a4a', '#c9a24a', '#6a4a2a', '#d9c9a3', '#3a5a7a'];
    for (let s = 0; s < 4; s++) {
      const z = .04 + s * .49; if (s) box(w, d, .03, M.walnut, x, y, z - .03);
      let yy = y - d / 2 + .06;
      while (yy < y + d / 2 - .12) {
        const bw = R(.035, .07), bh = R(.26, .4);
        if (Math.random() < .12) { yy += .08; continue; }
        box(w * .8, bw, bh, mat(cols[Math.floor(Math.random() * cols.length)], 'book'), x - .02, yy + bw / 2, z, 0); yy += bw + .004;
      }
    }
    block(x - w / 2, x + w / 2, y - d / 2, y + d / 2, 2);
  }
  function plant(x, y, s) {
    const tpl = N.Common_small_plant;
    if (tpl) { const p = tpl.clone(); p.position.copy(B(x, y)); p.scale.setScalar(s * 1.6); group.add(p); p.traverse(o => o.castShadow = true); }
    block(x - .25 * s, x + .25 * s, y - .25 * s, y + .25 * s, 1);
  }
  function oldPhoto(kind) {
    return tex(450, kind === 'portrait' ? 600 : 325, (c, w, h) => {
      c.fillStyle = '#d8c39a'; c.fillRect(0, 0, w, h);
      c.fillStyle = '#5a4630';
      if (kind === 'street') { for (let i = 0; i < 6; i++) { const bx = i * 78, bh = 120 + (i % 3) * 30; c.fillRect(bx, h - bh, 70, bh); c.beginPath(); c.moveTo(bx - 8, h - bh); c.lineTo(bx + 35, h - bh - 40); c.lineTo(bx + 78, h - bh); c.fill(); } c.fillStyle = '#8a7656'; c.fillRect(0, h - 40, w, 40); }
      if (kind === 'shop') { c.fillRect(60, 120, w - 120, h - 120); c.fillStyle = '#d8c39a'; c.fillRect(90, 160, 110, h - 160); c.fillRect(w - 200, 160, 110, 90); c.fillStyle = '#5a4630'; c.beginPath(); c.moveTo(30, 130); c.lineTo(w / 2, 50); c.lineTo(w - 30, 130); c.fill(); }
      if (kind === 'portrait') { c.beginPath(); c.ellipse(w / 2, 230, 90, 110, 0, 0, 7); c.fill(); c.fillRect(w / 2 - 150, 340, 300, h - 340); c.fillStyle = '#d8c39a'; c.beginPath(); c.arc(w / 2 - 34, 220, 22, 0, 7); c.arc(w / 2 + 34, 220, 22, 0, 7); c.fill(); }
      const g = c.createRadialGradient(w / 2, h / 2, 40, w / 2, h / 2, w * .75); g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(60,40,20,.55)'); c.fillStyle = g; c.fillRect(0, 0, w, h);
      grain(c, w, h, 900, .18);
    });
  }
  function goldenArt(kind) {
    return tex(400, 400, (c, w) => {
      c.fillStyle = '#f3ead6'; c.fillRect(0, 0, w, w); c.strokeStyle = '#1b2a4a'; c.lineWidth = 4;
      if (kind === 'rect') {
        // 斐波那契方块：1、1、2、3、5、8 依次围成黄金矩形
        const u = 18, sq = [[0, 0, 1], [1, 0, 1], [0, 1, 2], [2, 0, 3], [0, 3, 5], [5, 0, 8]], cols = ['#e2674a', '#2f8f83', '#e0a526', '#1b2a4a', '#b9ab8c', '#8a3330'];
        sq.forEach(([a, b2, f], i) => { c.fillStyle = cols[i]; c.fillRect(70 + a * u, 90 + b2 * u, f * u - 3, f * u - 3); });
        c.strokeStyle = '#c9a24a'; c.lineWidth = 5; c.beginPath(); for (let t = 0; t < 12; t += .05) { const r = 3 * Math.pow(1.3, t); c.lineTo(200 + r * Math.cos(t), 200 + r * Math.sin(t)); } c.stroke();
      }
      if (kind === 'sun') { c.fillStyle = '#c9a24a'; for (let i = 0; i < 420; i++) { const a = i * 2.39996, r = 7.5 * Math.sqrt(i); c.beginPath(); c.arc(200 + r * Math.cos(a), 200 + r * Math.sin(a), 4, 0, 7); c.fill(); } }
      if (kind === 'shell') { c.strokeStyle = '#8a3330'; c.lineWidth = 5; c.beginPath(); for (let t = 0; t < 14; t += .04) { const r = 2 * Math.exp(.3063 * t); c.lineTo(200 + r * Math.cos(t), 200 + r * Math.sin(t)); } c.stroke(); for (let t = 0; t < 14; t += .6) { const r = 2 * Math.exp(.3063 * t); c.beginPath(); c.moveTo(200, 200); c.lineTo(200 + r * Math.cos(t), 200 + r * Math.sin(t)); c.stroke(); } }
      c.fillStyle = '#5a4a2e'; c.font = `24px ${SERIF}`; c.textAlign = 'center'; c.fillText({ rect: '斐波那契方块', sun: '向日葵的花盘', shell: '鹦鹉螺' }[kind], w / 2, 380);
    });
  }
}

/* ================= 氛围：光柱、浮尘、闪电 ================= */
export function buildAtmos(ctx) {
  const { scene } = ctx;
  const fx = [];
  // 射灯下的光柱：开口圆锥，越往下越淡，侧面比正面亮
  const coneMat = new THREE.ShaderMaterial({
    uniforms: { col: { value: new THREE.Color('#ffd7a0') }, k: { value: .055 } },
    vertexShader: `varying float vY; varying vec3 vN; varying vec3 vV;
      void main(){ vY = uv.y; vec4 mv = modelViewMatrix * vec4(position, 1.); vN = normalize(normalMatrix * normal); vV = normalize(-mv.xyz); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: `uniform vec3 col; uniform float k; varying float vY; varying vec3 vN; varying vec3 vV;
      void main(){ float rim = 1. - abs(dot(vN, vV)); float a = pow(vY, 1.6) * (.35 + .65 * rim) * k; gl_FragColor = vec4(col * a, 1.); }`,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, toneMapped: false,
  });
  for (const [from, to, r, col, k] of ctx.cones) {
    const a = B(...from), b = B(...to), len = a.distanceTo(b);
    const g = new THREE.CylinderGeometry(.06, r, len, 24, 1, true);
    let cm = coneMat;
    if (col || k) { cm = coneMat.clone(); cm.uniforms.col.value = new THREE.Color(col || '#ffd7a0'); cm.uniforms.k.value = k || .055; }
    const m = new THREE.Mesh(g, cm); m.position.copy(a).add(b).multiplyScalar(.5);
    m.quaternion.setFromUnitVectors(new THREE.Vector3(0, -1, 0), b.clone().sub(a).normalize());
    m.renderOrder = 5; scene.add(m); fx.push(m);
  }
  // 浮尘：展灯下慢慢飘
  const n = 420, pos = new Float32Array(n * 3), seed = new Float32Array(n), AREAS = ctx.dustAreas;
  for (let i = 0; i < n; i++) { const a = AREAS[i % AREAS.length], p = B(R(a[0], a[2]), R(a[1], a[3]), R(.3, 3.3)); pos.set([p.x, p.y, p.z], i * 3); seed[i] = Math.random() * 100; }
  const dg = new THREE.BufferGeometry(); dg.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const dcv = document.createElement('canvas'); dcv.width = dcv.height = 32; const dc = dcv.getContext('2d');
  const gr = dc.createRadialGradient(16, 16, 0, 16, 16, 16); gr.addColorStop(0, 'rgba(255,236,200,1)'); gr.addColorStop(1, 'rgba(255,236,200,0)'); dc.fillStyle = gr; dc.fillRect(0, 0, 32, 32);
  const dust = new THREE.Points(dg, new THREE.PointsMaterial({ size: .018, map: new THREE.CanvasTexture(dcv), transparent: true, opacity: .55, depthWrite: false, blending: THREE.AdditiveBlending }));
  dust.frustumCulled = false; scene.add(dust); fx.push(dust);
  const base = pos.slice();
  // 门外的雨（透过入口玻璃门看到）
  const NR = 500, rp = new Float32Array(NR * 6), rv = new Float32Array(NR);
  for (let i = 0; i < NR; i++) { const p = B(R(-4, 4), R(-5.5, -.4), R(0, 4.5)); rp.set([p.x, p.y, p.z, p.x - .01, p.y - .3, p.z], i * 6); rv[i] = R(6, 9); }
  const rg = new THREE.BufferGeometry(); rg.setAttribute('position', new THREE.BufferAttribute(rp, 3));
  const outRain = new THREE.LineSegments(rg, new THREE.LineBasicMaterial({ color: '#9fb6ff', transparent: true, opacity: .35, fog: false })); scene.add(outRain); fx.push(outRain);

  // 闪电：间隔 25–50 秒，天窗方向两下白光，过一会儿雷声
  let nextFlash = performance.now() + R(14000, 24000), flashT = -1;
  return {
    fx,
    tick(dt, t, onThunder) {
      const p = dg.attributes.position.array;
      for (let i = 0; i < n; i++) { const s = seed[i]; p[i * 3] = base[i * 3] + Math.sin(t * .13 + s) * .25; p[i * 3 + 1] = base[i * 3 + 1] + Math.sin(t * .09 + s * 1.7) * .3; p[i * 3 + 2] = base[i * 3 + 2] + Math.cos(t * .11 + s) * .25; }
      dg.attributes.position.needsUpdate = true;
      const r = rg.attributes.position.array;
      for (let i = 0; i < NR; i++) { const o = i * 6, d = rv[i] * dt; r[o + 1] -= d; r[o + 4] -= d; if (r[o + 4] < 0) { r[o + 1] += 4.5; r[o + 4] += 4.5; } }
      rg.attributes.position.needsUpdate = true;
      const now = performance.now();
      if (now > nextFlash) { flashT = now; nextFlash = now + R(25000, 50000); setTimeout(() => onThunder && onThunder(), R(900, 2200)); }
      const ft = flashT < 0 ? 99 : (now - flashT) / 1000;
      return ft < .9 ? Math.max(0, 1 - ft / .12) * 1 + Math.max(0, 1 - Math.abs(ft - .3) / .1) * .7 : 0;   // 闪电亮度 0–1
    },
  };
}
