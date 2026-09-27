<?php
/**
 * MediaCut 适配层（DIDI AI）
 *
 * 作用：让 DIDI AI 站点通过 MediaCut API 完成「生图（文生图 / 图生图编辑）」以及视频、语音等能力。
 * 本文件自包含，不依赖主题其它代码，可直接被 functions.php 引入：
 *
 *     require_once get_template_directory() . '/inc/mediacut.php';
 *
 * 配置读取顺序（先命中先用）：
 *   1. 常量 DIDI_MC_BASE_URL / DIDI_MC_API_KEY
 *   2. 选项 didi_ai_config['mediacut']（数组，可含 base_url / api_key / webhook_token / timeout 等）
 *   3. 选项 mediacut_bridge_settings
 *
 * 对外 REST（命名空间 didi/v1）：
 *   POST /wp-json/didi/v1/mc/t2i    生图      参数 prompt, width, height
 *   POST /wp-json/didi/v1/mc/i2i    图片编辑  multipart 字段 file + prompt
 *   POST /wp-json/didi/v1/mc/video  文生视频  参数 prompt, duration, motion
 *   POST /wp-json/didi/v1/mc/task   轮询任务  参数 task_id（返回状态，完成后带 url）
 *   GET  /wp-json/didi/v1/mc/health 连通性检查
 *
 * 供主题 PHP 直接调用的函数：
 *   didi_mc_t2i($prompt, $width = 0, $height = 0)
 *   didi_mc_i2i($file_path, $prompt, $filename = '')
 *   didi_mc_video($prompt, $duration = 5, $motion = 'zoom')
 *   didi_mc_task_status($task_id)
 *   didi_mc_await($task_id, $max_seconds = 0)
 *   didi_mc_generate($endpoint, $fields, $files)
 *   以上函数成功返回数组（task_id/status/url/file/kind/text），失败返回 WP_Error。
 *
 * 前端轮询示例：
 *   const r = await fetch('/wp-json/didi/v1/mc/t2i', {
 *     method: 'POST',
 *     headers: { 'Content-Type': 'application/json', 'X-WP-Nonce': wpApiSettings.nonce },
 *     body: JSON.stringify({ prompt: '海边日落', width: 768, height: 768 })
 *   }).then(r => r.json());
 *   // r.url 为已下载到本地的结果地址
 *
 * @package didi-ai
 */

if (!defined('ABSPATH')) {
    exit;
}

if (!defined('DIDI_MC_PREFIX')) {
    define('DIDI_MC_PREFIX', 'didi_mediacut');
}

/**
 * 读取 MediaCut 适配配置。
 *
 * @return array
 */
function didi_mc_get_settings()
{
    $defaults = array(
        'base_url' => '',
        'api_key' => '',
        'webhook_token' => '',
        'timeout' => 60,
        'poll_interval' => 2,
        'max_poll_seconds' => 240,
    );

    $stored = get_option('didi_ai_config', array());
    $mc = array();
    if (is_array($stored) && isset($stored['mediacut']) && is_array($stored['mediacut'])) {
        $mc = $stored['mediacut'];
    } else {
        $alt = get_option('mediacut_bridge_settings', array());
        if (is_array($alt)) {
            $mc = $alt;
        }
    }

    $settings = wp_parse_args($mc, $defaults);

    if (defined('DIDI_MC_BASE_URL')) {
        $settings['base_url'] = DIDI_MC_BASE_URL;
    }
    if (defined('DIDI_MC_API_KEY')) {
        $settings['api_key'] = DIDI_MC_API_KEY;
    }

    $settings['base_url'] = untrailingslashit(trim((string) $settings['base_url']));
    $settings['api_key'] = trim((string) $settings['api_key']);
    $settings['webhook_token'] = trim((string) $settings['webhook_token']);
    $settings['timeout'] = max(10, (int) $settings['timeout']);
    $settings['poll_interval'] = max(1, (int) $settings['poll_interval']);
    $settings['max_poll_seconds'] = max(10, (int) $settings['max_poll_seconds']);

    return apply_filters('didi_mc_settings', $settings);
}

/**
 * 从 MediaCut 错误响应中提取可读信息。
 *
 * @param string $raw  响应体。
 * @param int    $code HTTP 状态码。
 * @return string
 */
function didi_mc_extract_error($raw, $code)
{
    $decoded = json_decode((string) $raw, true);
    if (is_array($decoded)) {
        if (isset($decoded['detail'])) {
            if (is_string($decoded['detail'])) {
                return $decoded['detail'];
            }
            return wp_json_encode($decoded['detail']);
        }
        if (isset($decoded['message']) && is_string($decoded['message'])) {
            return $decoded['message'];
        }
    }
    $raw = trim(wp_strip_all_tags((string) $raw));
    if ($raw !== '') {
        return mb_substr($raw, 0, 300);
    }
    return 'MediaCut 请求失败（HTTP ' . (int) $code . '）';
}

/**
 * 发起一次 MediaCut HTTP 请求。
 *
 * @param string $method GET / POST。
 * @param string $path   以 / 开头的接口路径。
 * @param array  $args   body|json|headers。
 * @return array|WP_Error 成功返回 array(code, body)。
 */
function didi_mc_http($method, $path, $args = array())
{
    $settings = didi_mc_get_settings();
    if ($settings['base_url'] === '') {
        return new WP_Error('didi_mc_no_base', '未配置 MediaCut 地址（didi_ai_config[mediacut][base_url]）');
    }
    if ($settings['api_key'] === '') {
        return new WP_Error('didi_mc_no_key', '未配置 MediaCut API Key（didi_ai_config[mediacut][api_key]）');
    }

    $headers = array('Accept' => 'application/json');
    $headers['Authorization'] = 'Bearer ' . $settings['api_key'];
    if (isset($args['headers']) && is_array($args['headers'])) {
        $headers = array_merge($headers, $args['headers']);
    }

    $request = array(
        'method' => strtoupper($method),
        'timeout' => $settings['timeout'],
        'headers' => $headers,
        'redirection' => 5,
    );

    if (isset($args['json'])) {
        $request['headers']['Content-Type'] = 'application/json';
        $request['body'] = wp_json_encode($args['json']);
    } elseif (isset($args['body'])) {
        $request['body'] = $args['body'];
    }

    $response = wp_remote_request($settings['base_url'] . $path, $request);
    if (is_wp_error($response)) {
        return $response;
    }

    $code = (int) wp_remote_retrieve_response_code($response);
    $raw = wp_remote_retrieve_body($response);

    if ($code < 200 || $code >= 300) {
        return new WP_Error(
            'didi_mc_http_' . $code,
            didi_mc_extract_error($raw, $code),
            array('status' => $code, 'body' => $raw)
        );
    }

    return array('code' => $code, 'body' => $raw);
}

/**
 * 构造 multipart 请求体。
 *
 * @param array $fields 普通字段。
 * @param array $files  文件项：field/filename/type/content。
 * @return array body/content_type。
 */
function didi_mc_multipart($fields, $files)
{
    $boundary = wp_generate_password(24, false, false);
    $eol = "\r\n";
    $body = '';

    foreach ($fields as $name => $value) {
        if ($value === null) {
            continue;
        }
        $body .= '--' . $boundary . $eol;
        $body .= 'Content-Disposition: form-data; name="' . $name . '"' . $eol . $eol;
        $body .= $value . $eol;
    }

    foreach ($files as $file) {
        $body .= '--' . $boundary . $eol;
        $body .= 'Content-Disposition: form-data; name="' . $file['field'] . '"; filename="' . $file['filename'] . '"' . $eol;
        $body .= 'Content-Type: ' . $file['type'] . $eol . $eol;
        $body .= $file['content'] . $eol;
    }

    $body .= '--' . $boundary . '--' . $eol;

    return array(
        'body' => $body,
        'content_type' => 'multipart/form-data; boundary=' . $boundary,
    );
}

/**
 * 将本地文件读取为 multipart 文件项。
 *
 * @param string $field    表单字段名。
 * @param string $path     本地绝对路径。
 * @param string $filename 上传文件名。
 * @return array|WP_Error
 */
function didi_mc_file_entry($field, $path, $filename = '')
{
    if (!is_string($path) || $path === '' || !file_exists($path)) {
        return new WP_Error('didi_mc_no_file', '待上传的图片不存在或不可读');
    }
    $content = file_get_contents($path);
    if ($content === false) {
        return new WP_Error('didi_mc_read_file', '读取图片失败');
    }
    $type = 'application/octet-stream';
    if (function_exists('wp_check_filetype')) {
        $check = wp_check_filetype($filename !== '' ? $filename : basename($path));
        if (!empty($check['type'])) {
            $type = $check['type'];
        }
    }
    return array(
        'field' => $field,
        'filename' => $filename !== '' ? $filename : basename($path),
        'type' => $type,
        'content' => $content,
    );
}

/**
 * 提交异步任务到 MediaCut。
 *
 * @param string $endpoint t2i/i2i/video/tts/matting/enhance/asr。
 * @param array  $fields   普通字段。
 * @param array  $files    multipart 文件项。
 * @return array|WP_Error 成功返回 task_id/status 等。
 */
function didi_mc_submit($endpoint, $fields = array(), $files = array())
{
    if (!empty($files)) {
        $multipart = didi_mc_multipart($fields, $files);
        $payload = array(
            'body' => $multipart['body'],
            'headers' => array('Content-Type' => $multipart['content_type']),
        );
    } else {
        $payload = array('body' => $fields);
    }

    $res = didi_mc_http('POST', '/api/v1/ai/' . $endpoint, $payload);
    if (is_wp_error($res)) {
        return $res;
    }

    $data = json_decode($res['body'], true);
    if (!is_array($data) || empty($data['task_id'])) {
        return new WP_Error('didi_mc_bad_submit', 'MediaCut 未返回任务 ID');
    }

    $data['base_url'] = didi_mc_get_settings()['base_url'];
    return $data;
}

/**
 * 查询任务状态。
 *
 * @param string $task_id 任务 ID。
 * @param bool   $hydrate 成功后是否下载结果并生成本地 url。
 * @return array|WP_Error
 */
function didi_mc_task_status($task_id, $hydrate = true)
{
    $task_id = trim((string) $task_id);
    if ($task_id === '') {
        return new WP_Error('didi_mc_no_task', '缺少 task_id');
    }

    $res = didi_mc_http('GET', '/api/v1/tasks/' . rawurlencode($task_id));
    if (is_wp_error($res)) {
        return $res;
    }

    $data = json_decode($res['body'], true);
    if (!is_array($data)) {
        return new WP_Error('didi_mc_bad_task', '任务状态响应解析失败');
    }

    if ($hydrate && isset($data['status']) && $data['status'] === 'succeeded' && !empty($data['result_url'])) {
        $data = didi_mc_hydrate_result($data);
    }

    return $data;
}

/**
 * 下载结果文件到本地 uploads，并写入 url 字段。
 *
 * @param array $data 任务状态数据。
 * @return array
 */
function didi_mc_hydrate_result($data)
{
    if (!empty($data['url'])) {
        return $data;
    }
    $result_url = isset($data['result_url']) ? (string) $data['result_url'] : '';
    $task_id = isset($data['task_id']) ? (string) $data['task_id'] : '';
    if ($result_url === '' || $task_id === '') {
        return $data;
    }

    $filename = basename($result_url);
    $res = didi_mc_http('GET', '/api/v1/result/' . rawurlencode($task_id) . '/' . rawurlencode($filename));
    if (is_wp_error($res)) {
        $data['download_error'] = $res->get_error_message();
        $data['remote_url'] = didi_mc_get_settings()['base_url'] . '/api/v1/result/' . rawurlencode($task_id) . '/' . rawurlencode($filename);
        return $data;
    }

    $upload = didi_mc_upload_dir();
    if (is_wp_error($upload)) {
        $data['download_error'] = $upload->get_error_message();
        return $data;
    }

    $safe_name = sanitize_file_name($task_id . '-' . $filename);
    $target = trailingslashit($upload['path']) . $safe_name;
    if (file_put_contents($target, $res['body']) === false) {
        $data['download_error'] = '写入本地文件失败';
        return $data;
    }

    $data['file'] = $target;
    $data['url'] = trailingslashit($upload['url']) . $safe_name;
    return $data;
}

/**
 * 获取（并确保存在）本地结果目录。
 *
 * @return array|WP_Error
 */
function didi_mc_upload_dir()
{
    $uploads = wp_upload_dir();
    if (!empty($uploads['error'])) {
        return new WP_Error('didi_mc_upload', $uploads['error']);
    }
    $path = trailingslashit($uploads['basedir']) . DIDI_MC_PREFIX;
    $url = trailingslashit($uploads['baseurl']) . DIDI_MC_PREFIX;
    if (!file_exists($path) && !wp_mkdir_p($path)) {
        return new WP_Error('didi_mc_upload', '无法创建结果目录');
    }
    return array('path' => $path, 'url' => $url);
}

/**
 * 轮询任务直到完成。
 *
 * @param string $task_id     任务 ID。
 * @param int    $max_seconds 最长等待秒数，0 使用配置值。
 * @return array|WP_Error
 */
function didi_mc_await($task_id, $max_seconds = 0)
{
    $settings = didi_mc_get_settings();
    $limit = $max_seconds > 0 ? (int) $max_seconds : $settings['max_poll_seconds'];
    $deadline = time() + $limit;
    $last = null;

    while (time() < $deadline) {
        $data = didi_mc_task_status($task_id, false);
        if (is_wp_error($data)) {
            return $data;
        }
        $last = $data;
        $status = isset($data['status']) ? $data['status'] : '';
        if ($status === 'succeeded') {
            return didi_mc_hydrate_result($data);
        }
        if ($status === 'failed') {
            $message = isset($data['error']) && $data['error'] ? $data['error'] : 'MediaCut 任务执行失败';
            return new WP_Error('didi_mc_task_failed', $message, $data);
        }
        sleep($settings['poll_interval']);
    }

    return new WP_Error('didi_mc_task_timeout', '等待 MediaCut 结果超时', $last);
}

/**
 * 生图（文生图）。
 *
 * @param string $prompt 画面描述。
 * @param int    $width  宽度，0 用服务端默认。
 * @param int    $height 高度，0 用服务端默认。
 * @return array|WP_Error
 */
function didi_mc_t2i($prompt, $width = 0, $height = 0)
{
    $prompt = trim((string) $prompt);
    if ($prompt === '') {
        return new WP_Error('didi_mc_no_prompt', '缺少画面描述');
    }
    $fields = array('prompt' => $prompt);
    if ((int) $width > 0) {
        $fields['width'] = (int) $width;
    }
    if ((int) $height > 0) {
        $fields['height'] = (int) $height;
    }
    $submit = didi_mc_submit('t2i', $fields);
    if (is_wp_error($submit)) {
        return $submit;
    }
    return didi_mc_await($submit['task_id']);
}

/**
 * 图片编辑（图生图）。
 *
 * @param string $file_path 本地图片路径或已上传文件数组。
 * @param string $prompt    编辑描述。
 * @param string $filename  上传文件名。
 * @return array|WP_Error
 */
function didi_mc_i2i($file_path, $prompt, $filename = '')
{
    $prompt = trim((string) $prompt);
    if ($prompt === '') {
        return new WP_Error('didi_mc_no_prompt', '缺少编辑描述');
    }

    if (is_array($file_path) && isset($file_path['tmp_name'])) {
        if ($filename === '' && isset($file_path['name'])) {
            $filename = $file_path['name'];
        }
        $file_path = $file_path['tmp_name'];
    }

    $file = didi_mc_file_entry('file', $file_path, $filename);
    if (is_wp_error($file)) {
        return $file;
    }

    $submit = didi_mc_submit('i2i', array('prompt' => $prompt), array($file));
    if (is_wp_error($submit)) {
        return $submit;
    }
    return didi_mc_await($submit['task_id']);
}

/**
 * 文生视频。
 *
 * @param string $prompt   画面描述。
 * @param int    $duration 时长（秒）。
 * @param string $motion   运镜：zoom/pan。
 * @return array|WP_Error
 */
function didi_mc_video($prompt, $duration = 5, $motion = 'zoom')
{
    $prompt = trim((string) $prompt);
    if ($prompt === '') {
        return new WP_Error('didi_mc_no_prompt', '缺少画面描述');
    }
    $motion = in_array($motion, array('zoom', 'pan'), true) ? $motion : 'zoom';
    $fields = array(
        'prompt' => $prompt,
        'duration' => max(1, (int) $duration),
        'motion' => $motion,
    );
    $submit = didi_mc_submit('video', $fields);
    if (is_wp_error($submit)) {
        return $submit;
    }
    return didi_mc_await($submit['task_id']);
}

/**
 * 通用生成入口，便于主题按需调用其它能力。
 *
 * @param string $endpoint t2i/i2i/video/tts/matting/enhance/asr。
 * @param array  $fields   普通字段。
 * @param array  $files    multipart 文件项。
 * @return array|WP_Error
 */
function didi_mc_generate($endpoint, $fields = array(), $files = array())
{
    $submit = didi_mc_submit($endpoint, $fields, $files);
    if (is_wp_error($submit)) {
        return $submit;
    }
    return didi_mc_await($submit['task_id']);
}

/**
 * REST 权限：登录且具备编辑/上传能力，或命中 X-MC-Token。
 *
 * @param WP_REST_Request $request 请求对象。
 * @return bool
 */
function didi_mc_rest_permission($request)
{
    if (is_user_logged_in() && (current_user_can('edit_posts') || current_user_can('upload_files'))) {
        return true;
    }
    $settings = didi_mc_get_settings();
    if ($settings['webhook_token'] !== '') {
        $token = $request->get_header('x-mc-token');
        if (is_string($token) && hash_equals($settings['webhook_token'], $token)) {
            return true;
        }
    }
    return (bool) apply_filters('didi_mc_rest_permission', false, $request);
}

/**
 * REST: 生图。
 *
 * @param WP_REST_Request $request 请求对象。
 * @return WP_REST_Response
 */
function didi_mc_rest_t2i($request)
{
    $prompt = $request->get_param('prompt');
    $result = didi_mc_t2i($prompt, (int) $request->get_param('width'), (int) $request->get_param('height'));
    return didi_mc_rest_response($result);
}

/**
 * REST: 图片编辑。
 *
 * @param WP_REST_Request $request 请求对象。
 * @return WP_REST_Response
 */
function didi_mc_rest_i2i($request)
{
    $files = $request->get_file_params();
    if (empty($files['file']['tmp_name'])) {
        return new WP_REST_Response(array('ok' => false, 'error' => '缺少上传文件字段 file'), 400);
    }
    $result = didi_mc_i2i($files['file'], $request->get_param('prompt'), isset($files['file']['name']) ? $files['file']['name'] : '');
    return didi_mc_rest_response($result);
}

/**
 * REST: 文生视频。
 *
 * @param WP_REST_Request $request 请求对象。
 * @return WP_REST_Response
 */
function didi_mc_rest_video($request)
{
    $result = didi_mc_video(
        $request->get_param('prompt'),
        (int) $request->get_param('duration'),
        (string) $request->get_param('motion')
    );
    return didi_mc_rest_response($result);
}

/**
 * REST: 轮询任务（前端提交后使用）。
 *
 * @param WP_REST_Request $request 请求对象。
 * @return WP_REST_Response
 */
function didi_mc_rest_task($request)
{
    $task_id = $request->get_param('task_id');
    $result = didi_mc_task_status($task_id, true);
    return didi_mc_rest_response($result);
}

/**
 * REST: 连通性检查。
 *
 * @return WP_REST_Response
 */
function didi_mc_rest_health()
{
    $settings = didi_mc_get_settings();
    $res = didi_mc_http('GET', '/health');
    $ok = !is_wp_error($res);
    return new WP_REST_Response(array(
        'ok' => $ok,
        'base_url' => $settings['base_url'],
        'has_key' => $settings['api_key'] !== '',
        'error' => $ok ? null : $res->get_error_message(),
    ), $ok ? 200 : 502);
}

/**
 * 统一封装 REST 返回。
 *
 * @param array|WP_Error $result 处理结果。
 * @return WP_REST_Response
 */
function didi_mc_rest_response($result)
{
    if (is_wp_error($result)) {
        $data = $result->get_error_data();
        $status = is_array($data) && !empty($data['status']) ? (int) $data['status'] : 0;
        if (!$status || $status < 400 || $status > 599) {
            $status = 502;
        }
        $payload = array('ok' => false, 'error' => $result->get_error_message());
        if (is_array($data)) {
            $payload['status'] = isset($data['status']) ? $data['status'] : null;
        }
        return new WP_REST_Response($payload, $status);
    }

    return new WP_REST_Response(array(
        'ok' => true,
        'task_id' => isset($result['task_id']) ? $result['task_id'] : null,
        'status' => isset($result['status']) ? $result['status'] : 'succeeded',
        'kind' => isset($result['result_kind']) ? $result['result_kind'] : null,
        'text' => isset($result['result_text']) ? $result['result_text'] : '',
        'url' => isset($result['url']) ? $result['url'] : null,
        'file' => isset($result['file']) ? $result['file'] : null,
        'download_error' => isset($result['download_error']) ? $result['download_error'] : null,
    ), 200);
}

/**
 * 注册 REST 路由。
 *
 * @return void
 */
function didi_mc_register_routes()
{
    $args = array(
        'methods' => 'POST',
        'permission_callback' => 'didi_mc_rest_permission',
    );

    register_rest_route('didi/v1', '/mc/t2i', array_merge($args, array('callback' => 'didi_mc_rest_t2i')));
    register_rest_route('didi/v1', '/mc/i2i', array_merge($args, array('callback' => 'didi_mc_rest_i2i')));
    register_rest_route('didi/v1', '/mc/video', array_merge($args, array('callback' => 'didi_mc_rest_video')));
    register_rest_route('didi/v1', '/mc/task', array_merge($args, array('callback' => 'didi_mc_rest_task')));
    register_rest_route('didi/v1', '/mc/health', array(
        'methods' => 'GET',
        'callback' => 'didi_mc_rest_health',
        'permission_callback' => 'didi_mc_rest_permission',
    ));
}
add_action('rest_api_init', 'didi_mc_register_routes');
