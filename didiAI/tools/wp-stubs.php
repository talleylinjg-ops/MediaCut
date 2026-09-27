<?php
/**
 * 最小 WordPress 桩函数，用于在非 WP 环境下验证 inc/mediacut.php 的客户端逻辑。
 * 仅用于本地联调，不进入任何生产环境。
 */

define('ABSPATH', '/tmp/opencode/wp/');

class WP_Error
{
    public $code;
    public $message;
    public $data;

    public function __construct($code = '', $message = '', $data = null)
    {
        $this->code = $code;
        $this->message = $message;
        $this->data = $data;
    }

    public function get_error_message()
    {
        return $this->message;
    }

    public function get_error_data()
    {
        return $this->data;
    }
}

function is_wp_error($thing)
{
    return $thing instanceof WP_Error;
}

function get_option($name, $default = false)
{
    return $default;
}

function apply_filters($tag, $value)
{
    return $value;
}

function wp_parse_args($args, $defaults = array())
{
    if (is_object($args)) {
        $args = get_object_vars($args);
    }
    if (!is_array($args)) {
        $args = array();
    }
    return array_merge($defaults, $args);
}

function untrailingslashit($value)
{
    return rtrim($value, '/');
}

function trailingslashit($value)
{
    return rtrim($value, '/') . '/';
}

function wp_json_encode($data)
{
    return json_encode($data);
}

function wp_strip_all_tags($text)
{
    return strip_tags($text);
}

function wp_generate_password($length = 12, $special = true, $extra = false)
{
    $chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    $out = '';
    for ($i = 0; $i < $length; $i++) {
        $out .= $chars[random_int(0, strlen($chars) - 1)];
    }
    return $out;
}

function sanitize_file_name($name)
{
    return preg_replace('/[^A-Za-z0-9._-]/', '-', $name);
}

function wp_check_filetype($filename)
{
    $ext = strtolower(pathinfo($filename, PATHINFO_EXTENSION));
    $map = array(
        'png' => 'image/png',
        'jpg' => 'image/jpeg',
        'jpeg' => 'image/jpeg',
        'webp' => 'image/webp',
        'bmp' => 'image/bmp',
        'gif' => 'image/gif',
    );
    return array('ext' => $ext, 'type' => isset($map[$ext]) ? $map[$ext] : '');
}

function wp_mkdir_p($target)
{
    return is_dir($target) || mkdir($target, 0777, true);
}

function wp_upload_dir()
{
    $base = '/tmp/opencode/wp-uploads';
    wp_mkdir_p($base);
    return array('basedir' => $base, 'baseurl' => '/wp-content/uploads', 'error' => false);
}

function wp_remote_request($url, $args = array())
{
    $method = isset($args['method']) ? $args['method'] : 'GET';
    $headers = isset($args['headers']) ? $args['headers'] : array();
    $body = isset($args['body']) ? $args['body'] : null;
    $timeout = isset($args['timeout']) ? $args['timeout'] : 60;
    $redirects = isset($args['redirection']) ? (int) $args['redirection'] : 5;

    if (is_array($body)) {
        $body = http_build_query($body);
        $hasType = false;
        foreach (array_keys($headers) as $key) {
            if (strtolower($key) === 'content-type') {
                $hasType = true;
            }
        }
        if (!$hasType) {
            $headers['Content-Type'] = 'application/x-www-form-urlencoded';
        }
    }

    $lines = array();
    foreach ($headers as $k => $v) {
        $lines[] = $k . ': ' . $v;
    }

    $context = stream_context_create(array(
        'http' => array(
            'method' => $method,
            'header' => implode("\r\n", $lines),
            'content' => $body,
            'timeout' => $timeout,
            'ignore_errors' => true,
            'follow_location' => $redirects > 0 ? 1 : 0,
            'max_redirects' => $redirects,
        ),
    ));

    $responseBody = @file_get_contents($url, false, $context);
    if ($responseBody === false) {
        return new WP_Error('http_request_failed', 'request failed: ' . $url);
    }

    $code = 0;
    if (isset($http_response_header) && is_array($http_response_header)) {
        foreach ($http_response_header as $line) {
            if (preg_match('#^HTTP/\S+\s+(\d+)#', $line, $m)) {
                $code = (int) $m[1];
            }
        }
    }

    return array('response' => array('code' => $code), 'body' => $responseBody);
}

function wp_remote_retrieve_response_code($response)
{
    return isset($response['response']['code']) ? $response['response']['code'] : 0;
}

function wp_remote_retrieve_body($response)
{
    return isset($response['body']) ? $response['body'] : '';
}

function is_user_logged_in()
{
    return false;
}

function current_user_can($cap)
{
    return false;
}

function register_rest_route($ns, $route, $args)
{
    return true;
}

function add_action($hook, $callback)
{
    return true;
}

if (!function_exists('mb_substr')) {
    function mb_substr($string, $start, $length = null)
    {
        return $length === null ? substr($string, $start) : substr($string, $start, $length);
    }
}
