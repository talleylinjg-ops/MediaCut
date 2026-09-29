<?php
/**
 * MediaCut 对接配置（示例模板）
 *
 * 作用：为 DIDI AI（WordPress）提供 MediaCut 的接入地址与 API Key。
 * 适配层 inc/mediacut.php 读取顺序（先命中先用）：
 *   1. 常量 DIDI_MC_BASE_URL / DIDI_MC_API_KEY   ← 本文件提供
 *   2. 选项 didi_ai_config['mediacut']
 *   3. 选项 mediacut_bridge_settings
 *
 * 部署步骤：
 *   1. 复制本文件为 mediacut-config.php，填入真实 base_url 与 api_key
 *   2. 在 wp-config.php 中「ABSPATH 定义之后、require wp-settings.php 之前」加入：
 *          require_once __DIR__ . '/wp-content/mediacut-config.php';
 *   3. 确认 mediacut-config.php 已加入版本控制忽略规则，真实 Key 不进仓库
 *
 * 不使用本文件时，也可以直接在 wp-config.php 写下面两行 define。
 *
 * 连通性自检：
 *   curl -s https://<域名>/health
 *   curl -s https://<域名>/api/v1/dev/key/info -H "Authorization: Bearer <API_KEY>"
 *
 * ===== curl 调用示例 =====
 *
 * # 文生图（异步提交，返回 task_id）
 * curl -X POST https://<域名>/api/v1/ai/t2i \
 *   -H "Authorization: Bearer <API_KEY>" \
 *   -F "prompt=海边日落，水彩画风" -F "width=768" -F "height=768"
 *
 * # 轮询任务（succeeded 后 result_url 形如 <task_id>/result_xxx.png）
 * curl https://<域名>/api/v1/tasks/<task_id> -H "Authorization: Bearer <API_KEY>"
 *
 * # 下载结果（必须带鉴权）
 * curl -o out.png "https://<域名>/api/v1/result/<task_id>/<filename>" \
 *   -H "Authorization: Bearer <API_KEY>"
 *
 * # 图生图编辑（multipart：file + prompt）
 * curl -X POST https://<域名>/api/v1/ai/i2i \
 *   -H "Authorization: Bearer <API_KEY>" \
 *   -F "file=@input.jpg" -F "prompt=把背景换成海边日落"
 *
 * # 文生视频（文生图 + FFmpeg 运镜）
 * curl -X POST https://<域名>/api/v1/ai/video \
 *   -H "Authorization: Bearer <API_KEY>" \
 *   -F "prompt=雪山湖泊航拍" -F "duration=5" -F "motion=zoom"
 *
 * ===== PHP 调用示例（主题内）=====
 *
 * $r = didi_mc_t2i('海边日落，水彩画风', 768, 768);
 * if (is_wp_error($r)) {
 *     error_log($r->get_error_message());
 * } else {
 *     echo esc_url($r['url']);   // 已下载到本地的结果地址
 * }
 *
 * @package didi-ai
 */

if (!defined('DIDI_MC_BASE_URL')) {
    define('DIDI_MC_BASE_URL', 'https://didimedia.com');
}
if (!defined('DIDI_MC_API_KEY')) {
    define('DIDI_MC_API_KEY', 'REPLACE_WITH_YOUR_API_KEY');
}
