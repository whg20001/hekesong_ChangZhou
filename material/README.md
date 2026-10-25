# 华罗庚数学展馆 · Blender 模型

根据 `scene-03-3d/模型清单.md` 制作，模型与交付物统一保存在用户指定的根目录 `material/`。
清单中的 S0–S6 共 52 项均已制作，包含 P0、P1、P2。已落实第一轮检验反馈 A1–A5 与 B1–B3，另增加序厅标题牌和两只玻璃展柜（S1-6、S1-7）。

| 文件名 | 内容 |
|---|---|
| `S0_shell` | 建筑外壳、五区地面、隔墙和门洞、天花板、两处天窗、入口门、两扇独立出口门、22 盏轨道射灯、出口指示牌 |
| `S1_lobby` | 风格化华罗庚铜质半身像与基座、六块时间轴展板、长凳、导览台、两盆绿植、北墙标题牌、两只玻璃手稿展柜 |
| `S2_shop` | 杂货铺门脸、柜台、三层货架及货物、13 档共 91 颗独立算盘珠、调整方向和尺寸的账本、笔砚、煤油灯、三个人形纸板、隔离栏、说明牌 |
| `S3_tea` | 木格窗茶室背景、窗花、茶桌、炉子、水壶、茶壶、四只茶杯、茶叶罐、独立壶盖和罐盖、挂钟和独立指针、甘特图展板、凳子、吊灯、说明牌 |
| `S4_factory` | 砖墙和高窗、熔炉及独立炉门、控制台和旋钮按钮、温度表及指针、黑板、8 个试样、3 个齿轮、工作台及工具、说明牌 |
| `S5_exit` | 八块斐波那契方块和对应四分之一圆弧螺旋、留言台、结语展墙 |
| `S6_common` | 弯曲纸卡、说明立牌、黄铜隔离柱与独立绒绳、地面箭头、小盆栽 |

每组提供同名 `.blend` 源文件、开启 Draco 压缩的 `.glb`、`.png` 预览和 `.audit.json` 物体清单。
`Hua_Museum.blend` 是 S0–S5 在清单世界坐标中组装的完整源工程；通用件保留在 S6 供复制。
`Hua_Museum.png` 是组合预览。

## 使用

- Blender 原生坐标：米制，Z 向上，地面 Z=0；S0–S5 导入后无需重新摆放或居中。
- GLB 使用标准 glTF Y 向上：Blender `(x,y,z)` 对应 glTF `(x,z,-y)`。Three.js 中直接加载即可，场景坐标与转轴要按此映射。
- 所有源工程仅包含网格；灯光、相机和预览地台仅在临时渲染时生成。总览和外壳预览暂时移除了屋顶、近侧外墙，源工程及 GLB 中保留完整建筑。
- 材质只使用 Principled BSDF 的常量颜色、金属度、粗糙度、Alpha 与自发光。没有程序化纹理、外部贴图或 Transmission。
- 铜像是按清单特征塑造的低多边形艺术化半身像：圆框眼镜、侧分短发、中山装立领；不是人物扫描或真实纪念馆藏品的复刻。
- `SIGN_` 物体均为空白并带归一化 UV。文字、人物画像、图表由网页后续绘制或替换材质。
- `COL_` 是简单长方体碰撞网格，包含 `collision=true` 自定义属性。网页加载后应设 `visible=false`，同时纳入碰撞检测。源文件使用线框显示与 Alpha=0 材质，便于检查且不依赖隐藏状态导出。
- `ANIM_` 转动零件已将原点设置在轴心或合页；没有预设动画。`rotation_axis_blender` 自定义属性记录 Blender 坐标中的转轴。
- 水壶盖、茶壶盖、茶叶罐盖分别作为对应 `INT_` 容器的子物体，移动容器时随容器移动，也能绕自己的合页独立转动。
- 炉门 `ANIM_furnaceDoor` 旋转为 0 时关闭；合页仍位于 `(2.98,13.21,0.7)`。
- 出口门为两个独立网格：`INT_exitDoor_L` 合页 `(12,3,0)`，`INT_exitDoor_R` 合页 `(12,5,0)`；均默认关闭、绕 Blender Z 轴旋转。旧的 `INT_exitDoor` 已删除。
- 算盘珠命名为 `ANIM_bead_01_1` 至 `ANIM_bead_13_7`，每颗 16 个三角面、原点位于珠心，可沿 Blender X 轴移动。档号沿 +Y 增加；`_1`、`_2` 为横梁 +X 侧的上珠，`_3` 至 `_7` 为 -X 侧的下珠。`_1`、`_3` 分别最靠近横梁。旧的整档节点 `ANIM_beads_*` 已删除。
- `SIGN_ledgerL` 在 +Y 侧、`SIGN_ledgerR` 在 -Y 侧，单页为 X 0.22 × Y 0.15 m；两个页面 UV 均为 U 朝 -Y、V 朝 +X，适合玩家站在 -X 一侧阅读。
- `Common_stanchion` 和 `Common_rope` 保留为独立网格。绳子原点在起始挂钩处，局部 X 范围为 `[0,1]` m，沿 +X 伸出；按两柱间距缩放绳子的 X 即可。
- 茶壶的容器网格和包含壶盖的总高度均为 0.16 m；壶盖保持为独立子物体。
- S6 通用件在原点附近分开放置；纸卡原点位于卡片中心，其他通用件使用底部原点。

```js
// 先按项目已有版本引入 GLTFLoader 和 DRACOLoader，并配置 Draco 解码器路径。
loader.setDRACOLoader(dracoLoader);
loader.load('/material/S3_tea.glb', ({ scene }) => {
  scene.traverse((object) => {
    if (object.name.startsWith('COL_')) object.visible = false;
  });
  museum.add(scene);
  const kettle = scene.getObjectByName('INT_kettle');
  const minuteHand = scene.getObjectByName('ANIM_minHand');
});
```

如果网页部署只复制 `scene-03-3d/models/`，可将这里的七个 GLB 复制到那个目录，并相应设置加载路径。
本次未改动网页代码。

## 重建与检查

在项目根目录执行：

```powershell
& 'D:\blender\blender.exe' --background --python '.\material\build_models.py'
& 'D:\blender\blender.exe' --background --python '.\material\verify_exports.py'
```

只重建一组：在第一条命令结尾加 `-- --only S3_tea`。
只重建指定多组：加 `-- --only S0_shell,S1_lobby,S2_shop,S3_tea,S4_factory,S6_common`，之后单独执行 `-- --assemble-only` 更新总工程。
只生成模型不渲染：加 `-- --skip-render`。
修改分组模型后重新组合：加 `-- --assemble-only`。

`validation.json` 汇总原始 52 项及新增 2 组配件的三角面数量与单项预算；每组的 `.audit.json` 记录节点名称、尺寸、原点和转轴。
`export_validation.json` 记录 GLB 格式、Draco、节点与三角面一致性、实际解码后原点与尺寸、区域范围以及六个通道开口的检验结果。
其中 `feedback_checks` 包含 A1–A5、B1–B3 在 `.blend` 和实际 GLB 解码回读后的 16 项检查。
源码的缩放与旋转及倒角均已应用，模型没有相机、灯光、隐藏物体、动画或文字。
