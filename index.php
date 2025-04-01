<?php
$channels = [
    "Safari TV" => "safari_tv",
    "Victers TV" => "victers_tv",
    "Flowers TV" => "flowers_tv",
    "Manorama News" => "manorama_news",
    "Aaj Tak" => "aaj_tak"
];
?>
<!DOCTYPE html>
<html>
<head>
    <title>IPTV Streaming</title>
</head>
<body>
    <h2>Click a Channel to Play</h2>
    <ul>
        <?php foreach ($channels as $name => $id): ?>
            <li><a href="stream.php?channel=<?= $id ?>">▶ <?= $name ?></a></li>
        <?php endforeach; ?>
    </ul>
</body>
</html>