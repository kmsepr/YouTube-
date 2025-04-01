<?php
// IPTV Channel List
$channels = [
    "safari_tv" => "https://j78dp346yq5r-hls-live.5centscdn.com/safari/live.stream/chunks.m3u8",
    "victers_tv" => "https://932y4x26ljv8-hls-live.5centscdn.com/victers/tv.stream/victers/tv1/chunks.m3u8",
    "flowers_tv" => "http://103.199.161.254/Content/flowers/Live/Channel(Flowers)/index.m3u8",
    "manorama_news" => "http://103.199.161.254/Content/manoramanews/Live/Channel(ManoramaNews)/index.m3u8",
    "aaj_tak" => "https://feeds.intoday.in/aajtak/api/aajtakhd/master.m3u8"
];

// Check if the requested channel exists
if (!isset($_GET['channel']) || !array_key_exists($_GET['channel'], $channels)) {
    die("Invalid channel! Use ?channel=safari_tv");
}

$url = escapeshellarg($channels[$_GET['channel']]);
header("Content-Type: video/3gpp");

// Convert M3U8 to **H.263 + AAC** (3GP format for Symbian)
passthru("ffmpeg -i $url -c:v h263 -b:v 128k -s 176x144 -r 15 -c:a aac -b:a 32k -ac 1 -ar 22050 -f 3gp -movflags frag_keyframe+empty_moov -");
?>