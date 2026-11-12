# Blender 规则（本专案实测过的作法）

## 前置

- Blender 需**使用者手动**开启，并在 3D 视窗按 `N` → **MCP for Blender** → **Start MCP Server**。没开就会得到 `Could not connect to Blender`。
- 本机版本：Blender 5.2.1 LTS、外挂 v1.7、protocol 7（以 `get_addon_status` 实际回报为准，不要相信目录名称）。
- ⚠️ **此 MCP 让 agent 在 Blender 内执行任意 Python**。动手前先 `get_scene_info()` 确认**当下**档案，不要把使用者的工作覆盖掉。
- 操作完用 `get_viewport_screenshot()` 确认结果。

## 角色 proxy

- **方块人／简化人形优于精致人偶**；形状越阳春，模型的「代理感」越好被忽略。
- 命名：`V5_<角色>_<部位>`（例 `V5_teacher_torso`、`V5_friend_head`），相机 `V5_<镜号>`，场景物件一律加前缀，避免与旧素材混在一起。
- 用 `object.color` 平涂色区分角色（老师深色、朋友橄榄绿），**不要**花时间做材质。
- 道具（碗、盘、筷子、手机、纸张）也要有，因为它们是**空间锚点**；但画面中要读的文字一律留后制。

### 空景镜

空景（无人）镜要隐藏角色，但**保留道具**。这在渲染流程逐镜设定，**不要写死在场景存档里**——否则下一个人打开只看到空房间。

```python
for o in sc.objects:
    if any(o.name.startswith("V5_"+p) for p in ("teacher_", "friend_")) \
       and not any(k in o.name for k in ("bowl", "plate", "chopsticks")):
        o.hide_render = True
```

## 算图设定

- 引擎：`BLENDER_WORKBENCH`（不需要灯光，最快）。
- `sc.display.shading.color_type='OBJECT'`、`light='STUDIO'`、开启 shadows 与 cavity。
- `image_settings.file_format='PNG'`、`color_mode='RGB'`。
- 解析度：正式编辑用 1536×864；**布置图检查用 960×540**；**guide 影片用 512×288**。

**Workbench 是空间与构图检查，不是最终风格参考。**

## 布置图检查（生成前必做）

对每个镜号切换相机各算一张，再合成宫格图。

| 实测数据 | 值 |
|:---|:---|
| 13 镜布置图总耗时 | **0.8 秒** |
| 对比一次 H3 生成 | 数百秒 |

能拦下的问题：座位／朝向错、背景多出物件、景别不符、道具位置、**不同镜号共用同一机位**。

**布置图保证的是空间关系，不是像素级构图**：实测 A2 布置图偏侧背、成片偏正面 3/4，但座位与背景一致。不可宣称锁死构图。

## 运镜

- 相机运动**必须做成 keyframe**，不要靠算图脚本逐格位移相机——否则 `.blend` 单独交付时运镜会消失。
- 插值用 **LINEAR**，才与逐格公式一致：

```python
from mathutils import Vector
base = cam.location.copy()
direction = cam.rotation_euler.to_quaternion() @ Vector((0, 0, -1))  # 视线方向
cam.animation_data_create()
cam.location = base
cam.keyframe_insert("location", frame=1)
cam.location = base + direction * distance
cam.keyframe_insert("location", frame=N)
```

- 验证方式：重算该镜全部帧，与原脚本产出逐格比对。**已验证等价**（124 格差异 0.0047%、首尾格 0 像素差、位置偏差 1.1e-6 m）。

## 可重用档案

- **不要覆写既有 `.blend`**；另存新档（例 `eatery_v5_reusable.blend`），原档保留为历史。
- 只保留**一个场景**。多场景＋多套相机是已发生的混淆来源。
- 移除不用的场景后，清掉 `users == 0` 的孤儿资料（objects / meshes / actions / worlds / collections），回圈执行到没有为止。
- 存档前还原**正常预设状态**：预设相机、角色全部可见、1536×864、frame range 覆盖最长的镜。
- 相机契约另存 `camera_plan_v<N>.json`。

## Blender 5.x API 陷阱（实际踩到）

| 症状 | 正确做法 |
|:---|:---|
| `Action` 没有 `.fcurves` | 5.x 改用 slots／layers：`act.layers[0].strips[0].channelbag(act.slots[0]).fcurves` |
| `Action` 没有 `.fake_user` | 栏位名是 `use_fake_user` |
| `bpy.ops.wm.open_mainfile()` 后 `bpy.context.window` 是 `None` | 开档后不要直接存取 `bpy.context.window`；改用 `bpy.data.scenes`，或先做一次无害呼叫再取 |
| 不确定属性／enum 名称 | 先用 `bpy_api_lookup`、`describe_node_type` 查，不要猜 |
| 假设灯光设定 | Workbench 不吃场景灯光；场景没有 Light 也可能是正常的 |

## 检查节点 ID

不同工作流的 Save 节点 ID 不同（v5 是 `SaveVideo` 15／生图 `SaveImage` 7；外部工作流是 33／9）。**收件要锁该工作流自己的节点**，不要遍历所有输出，否则会把输入影片／图片当成成品。
