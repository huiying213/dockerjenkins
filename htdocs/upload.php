<?php
$targetDir = "uploads/";

// 检查文件夹是否存在，不存在则创建
if (!is_dir($targetDir)) {
    mkdir($targetDir, 0755, true);
}

$uploadOk = true;
$log = "";

// 展示已上传文件列表
echo "<h3>📂 已上传文件列表：</h3>";
if ($handle = opendir($targetDir)) {
    echo "<ul>";
    while (false !== ($entry = readdir($handle))) {
        if ($entry != "." && $entry != "..") {
            $filePath = $targetDir . $entry;
            $size = filesize($filePath);
            $time = date("Y-m-d H:i:s", filemtime($filePath));
            echo "<li>
                    <a href=' ' target='_blank'>$entry</a > 
                    （大小：" . $size . " 字节，修改时间：$time）
                  </li>";
        }
    }
    echo "</ul>";
    closedir($handle);
}

// 检查是否有文件上传
if (!isset($_FILES["myfile"])) {
    $log .= "❌ 没有接收到文件数据。\n";
    $uploadOk = false;
} else {
    $file = $_FILES["myfile"];
    $targetFile = $targetDir . basename($file["name"]);

    // 打印文件基本信息
    $log .= "📄 上传文件信息：\n";
    $log .= "原始文件名： " . $file["name"] . "\n";
    $log .= "文件类型：   " . $file["type"] . "\n";
    $log .= "文件大小：   " . $file["size"] . " 字节\n";
    $log .= "临时文件：   " . $file["tmp_name"] . "\n";
    $log .= "错误码：     " . $file["error"] . "\n\n";

    // 检查是否有错误
    if ($file["error"] !== UPLOAD_ERR_OK) {
        $log .= "❌ 上传失败，错误代码：" . $file["error"] . "\n";
        $log .= upload_error_message($file["error"]) . "\n";
        $uploadOk = false;
    }

    // 尝试保存文件
    if ($uploadOk) {
        if (move_uploaded_file($file["tmp_name"], $targetFile)) {
            $log .= "✅ 上传成功！文件已保存为： " . $targetFile . "\n";
        } else {
            $log .= "❌ move_uploaded_file() 执行失败，文件未保存。\n";
            $uploadOk = false;
        }
    }
}

// 输出日志
echo "<pre>$log</pre>";



// 错误码解释函数
function upload_error_message($code) {
    switch ($code) {
        case UPLOAD_ERR_INI_SIZE:    return "文件超过了 php.ini 中 upload_max_filesize 限制。";
        case UPLOAD_ERR_FORM_SIZE:   return "文件超过了 HTML 表单中 MAX_FILE_SIZE 限制。";
        case UPLOAD_ERR_PARTIAL:     return "文件只有部分被上传。";
        case UPLOAD_ERR_NO_FILE:     return "没有文件被上传。";
        case UPLOAD_ERR_NO_TMP_DIR:  return "找不到临时文件夹。";
        case UPLOAD_ERR_CANT_WRITE:  return "文件写入失败。";
        case UPLOAD_ERR_EXTENSION:   return "PHP 扩展中断了文件上传。";
        default: return "未知错误。";
    }
}
?>