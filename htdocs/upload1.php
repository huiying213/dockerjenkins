<?php
$targetDir = "uploads/";

// 检查文件夹是否存在，不存在则创建
if (!is_dir($targetDir)) {
    mkdir($targetDir, 0755, true);
}

$targetFile = $targetDir . basename($_FILES["myfile"]["name"]);

if (move_uploaded_file($_FILES["myfile"]["tmp_name"], $targetFile)) {
    echo "上传成功！文件名：" . htmlspecialchars(basename($_FILES["myfile"]["name"]));
} else {
    echo "上传失败！";
}
?>