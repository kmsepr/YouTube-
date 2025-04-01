<?php
// List of IPTV channels
$channels = [
    "safari_tv" => "https://j78dp346yq5r-hls-live.5centscdn.com/safari/live.stream/chunks.m3u8",
    "victers_tv" => "https://932y4x26ljv8-hls-live.5centscdn.com/victers/tv.stream/victers/tv1/chunks.m3u8",
    "kairali_we" => "https://yuppmedtaorire.akamaized.net/v1/master/a0d007312bfd99c47f76b77ae26b1ccdaae76cb1/wetv_nim_https/050522/wetv/playlist.m3u8",
    "flowers_tv" => "http://103.199.161.254/Content/flowers/Live/Channel(Flowers)/index.m3u8",
    "dd_malayalam" => "https://d3eyhgoylams0m.cloudfront.net/v1/manifest/93ce20f0f52760bf38be911ff4c91ed02aa2fd92/ed7bd2c7-8d10-4051-b397-2f6b90f99acb/562ee8f9-9950-48a0-ba1d-effa00cf0478/2.m3u8",
    "amrita_tv" => "https://dr1zhpsuem5f4.cloudfront.net/master.m3u8",
    "24_news" => "https://segment.yuppcdn.net/110322/channel24/playlist.m3u8",
    "mazhavil_manorama" => "https://yuppmedtaorire.akamaized.net/v1/master/a0d007312bfd99c47f76b77ae26b1ccdaae76cb1/mazhavilmanorama_nim_https/050522/mazhavilmanorama/playlist.m3u8",
    "aaj_tak" => "https://feeds.intoday.in/aajtak/api/aajtakhd/master.m3u8"
];


// Check if the requested channel exists
if (!isset($_GET['channel']) || !array_key_exists($_GET['channel'], $channels)) {
    die("Invalid channel! Use ?channel=safari_tv");
}

$url = escapeshellarg($channels[$_GET['channel']]);
header("Content-Type: video/3gpp");

// Convert M3U8 to **H.263 + AAC** (3GP format for Symbian)
passthru("ffmpeg -i $url -c:v h263 -b:v 200k -c:a aac -b:a 48k -ar 22050 -ac 1 -f 3gp -movflags frag_keyframe+empty_moov -");
?>