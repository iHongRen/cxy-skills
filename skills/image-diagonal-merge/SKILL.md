---
name: image-diagonal-merge
description: 用于把两张图片按一条穿过中心点的分割线合并成一张图
---

# 图片角度分割合并

用内置脚本把两张位图按指定角度的分割线合成一张。分割线必过合成图中心点，用角度描述方向。

## 可用脚本

**`scripts/image_diagonal_merge.py`**

## 角度约定

以合成图中心点为原点，角度按数学惯例（正 x 轴向右，逆时针旋转）取值，范围 0~180°。超过 180° 自动减去 180°（线方向对称，0° 与 180° 等价）。

| 角度 | 分割线方向     | 分割效果      |
| ---- | -------------- | ------------- |
| 0    | 水平           | 上下各半      |
| 45   | 正斜杠 `/`     | 左上 / 右下   |
| 90   | 垂直           | 左右各半      |
| 135  | 反斜杠 `\`     | 左下 / 右上   |
| 180  | 水平（等同 0） | 上下各半      |

## 调用

```text
<python> <skill_dir>/scripts/image_diagonal_merge.py [image1] [image2] [-o output] [--angle 角度] [--swap]
```

### 参数

- `image1` `image2`：可选。省略时自动取当前目录下恰好两张图片。
- `-o, --output`：输出路径，默认 `./merged.png`。
- `-a, --angle`：分割线角度（0~180），默认 90。
- `--swap`：翻转 image1 / image2 所在侧。

### 默认侧

- 水平线（0/180）：image1 在上半部。
- 垂直线（90）：image1 在左侧。
- `/` 斜线（45）：image1 在左上三角。
- `\` 斜线（135）：image1 在左下三角。
- 加 `--swap` 翻转。

## 示例

```text
<python> <skill_dir>/scripts/image_diagonal_merge.py a.png b.png -o out.png --angle 45
<python> <skill_dir>/scripts/image_diagonal_merge.py --angle 90 --swap
<python> <skill_dir>/scripts/image_diagonal_merge.py --angle 135
```

## 行为

- 输出尺寸跟随第一张图，第二张图不同会自动缩放。
- 自动修正 EXIF 方向。
- PNG/WebP/TIFF/GIF 保留透明度；JPEG/BMP 铺白底。
- 成功后打印输出文件的绝对路径。
