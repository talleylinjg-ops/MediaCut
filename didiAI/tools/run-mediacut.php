<?php
require __DIR__ . '/wp-stubs.php';

define('DIDI_MC_BASE_URL', getenv('MC_BASE'));
define('DIDI_MC_API_KEY', getenv('MC_KEY'));

require __DIR__ . '/../wp-content/themes/didi-ai/inc/mediacut.php';

function show($label, $result)
{
    if (is_wp_error($result)) {
        echo "[$label] WP_Error: " . $result->get_error_message() . "\n";
        return;
    }
    $url = isset($result['url']) ? $result['url'] : '(none)';
    $kind = isset($result['result_kind']) ? $result['result_kind'] : '?';
    $task = isset($result['task_id']) ? $result['task_id'] : '?';
    $file = isset($result['file']) ? $result['file'] : '(none)';
    echo "[$label] ok kind=$kind task=$task\n";
    echo "         url=$url\n";
    echo "         file=$file exists=" . (is_string($file) && file_exists($file) ? 'yes' : 'no') . "\n";
    if (!empty($result['download_error'])) {
        echo "         download_error=" . $result['download_error'] . "\n";
    }
}

echo "=== health ===\n";
$health = didi_mc_http('GET', '/health');
echo is_wp_error($health) ? ('  WP_Error: ' . $health->get_error_message() . "\n") : ('  ok body=' . $health['body'] . "\n");

echo "=== t2i ===\n";
show('t2i', didi_mc_t2i('一只戴帽子的猫，水彩画风', 768, 768));

echo "=== i2i ===\n";
$source = __DIR__ . '/sample.png';
if (!file_exists($source)) {
    file_put_contents($source, base64_decode(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
    ));
}
show('i2i', didi_mc_i2i($source, '把背景换成海边日落'));

echo "=== 空 prompt 校验 ===\n";
show('t2i-empty', didi_mc_t2i('   '));

echo "=== 不存在的任务 ===\n";
show('task-404', didi_mc_task_status('not-a-real-task-id'));
