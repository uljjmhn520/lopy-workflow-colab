# sfx：CC0 音效库（58 个，21MB）

原频道实际用在片子里的音效，全部是 **Freesound CC0 1.0**（公有领域：可商用、免标示、可修改），所以直接附在 repo 里。档案是 Freesound 的 hq 预览 mp3（约 128kbps，做短片混音够用；要原档可到 `manifest.json` 各笔的 `page` 网址登入下载）。每个档的 Freesound 编号、网址、授权确认纪录都在 [manifest.json](manifest.json)。

为什么要用真实录音：H3 做不出来的人身音效（脚步、肚子叫）用程式合成听起来很假，原频道试过后全部改用真实录音。

| 分类 | 档案（时间长度） | 用途 |
|:---|:---|:---|
| 脚步 | `foot_leather_hard_surface_462179`（23s 皮鞋）、`foot_echo_hall_536290`（22s 走廊回音）、`foot_shoes_stone_637555`（7s）、`foot_docmartins_534635`（36s 皮靴）、`foot_tile_variations_834027`（6s，10 个变化）、`foot_laminate_830501`（38s）、`foot_quiet_rubber_613723`（18s 蹑手蹑脚） | 走廊、教室走路；蹑手蹑脚用 quiet_rubber |
| 肚子叫 | `stomach_growling_786693`（1.0s，单声「咕噜」，首选）、`stomach_growling_rumbles_447911`（2.0s）、`stomach_growl_PiSh_52293`（3.6s）、`stomach_long_intense_9_696404`（12s） | 「咕噜咕噜」＝786693 连播两次（第二次降 2 个半音） |
| 翻页 | `page_flip_683706`（9s）、`page_turn_144110`（1.7s）、`page_turn_860360`（0.3s） | 翻书、翻笔记 |
| 门 | `door_close_classroom_379896`（3s）、`door_close_classroom_204178`（10s） | 关教室门 |
| 窗锁 | `window_handle_unlock_448393`（1.3s）、`window_click_slide_669069`（4s） | 扣窗锁 |
| 哨子 | `whistle_referee_gym_218318`（3.3s 体育馆裁判哨，首选）、`whistle_coach_161662`（0.9s 短促）、`whistle_coach_cheap_817398`（1.8s） | 体育课吹哨（2026-10-07 新增，以下同） |
| 球 | `ball_rubber_bounce_423778`（6s 大橡胶球弹地）、`ball_football_bounce_378355`（5.6s）、`ball_catch_hands_514989`（0.2s 双手接球）、`ball_rubber_hit_534111`（0.5s 球打中闷响）、`thud_body_hit_276600`（0.8s 打到身体的「咚」） | 躲避球：打中人＝`thud_body_hit`＋`ball_rubber_hit` 叠；接住＝`ball_catch_hands` |
| 欢呼 | `cheer_children_school_640855`（7.6s 室内孩子欢呼）、`cheer_kids_woah_397317`（4.5s「哇～」）、`cheer_children_after_school_816074`（27.6s 放学尖叫，偏远） | 全班欢呼、惊叹 |
| 欢呼（掌声） | `clap_kids_short_529455`（3.7s）、`clap_kids_unison_430816`（5.2s 约 10 人齐拍）、`clap_kids_529694`（15.7s） | 教室里几个孩子拍手 |
| 环境 | `amb_playground_elementary_252684`（100s 小学操场，含钟声）、`amb_school_recess_264045`（114s 下课打篮球、偶有老师喊声）、`amb_schoolyard_538220`（80s） | 操场底噪（国外录音，有零星外语说话声，混小声当底） |
| 环境（鸟叫） | `amb_birds_window_morning_608154`（50s 开窗鸟叫）、`amb_birds_morning_50619`（32s 清晨乡间） | 早晨房间窗外 |
| 纸 | `paper_fold_367683`（14.7s 对折多次）、`paper_folding_398896`（17s）、`paper_crease_118606`（7.6s 压折线）、`paper_crumple_653952`（5.8s 揉纸） | 折纸桥、美劳 |
| 胶带 | `tape_rip_467721`（1.0s 撕胶带）、`tape_peel_rip_618541`（4.2s 撕起＋扯断）、`tape_scotch_369915`（3.2s 透明胶带）、`sticker_peel_contact_590433`（0.5s 撕胶膜）、`plastic_strip_peel_475169`（1.8s 撕塑胶贴条） | 美劳贴胶带；OK 绷撕开／撕下用后两个（没有真正的 OK 绷 CC0 录音） |
| 黏土 | `clay_tack_roll_451416`（14.8s 搓黏土胶成球、捏、扯）、`dough_squish_403915`（19.3s 揉面团挤压） | 捏黏土（没有真正 play-doh 的 CC0 录音，这两个最接近） |
| 铅笔 | `pencil_writing_336381`（38s）、`pencil_writing_b_376705`（16s B 铅笔写字）、`pencil_drawing_slow_444676`（17.6s 慢慢画） | 写字、画名片 |
| 闹钟 | `alarm_beep_369880`（24s 电子哔哔，首选）、`alarm_bell_14262`（7.8s 老式双铃，响 4 秒后按掉）、`alarm_clock_185708`（8.6s） | 卧室闹钟 |
| 砝码 | `coins_change_table_243517`（3.4s 硬币放桌）、`coins_wood_table_766410`（2.6s 硬币丢木桌）、`coin_knock_place_580375`（16.7s 金属币敲桌再放下）、`coins_balance_770106`（10s 金币放秤盘） | 纸桥承重放砝码／硬币（没有真正砝码录音，用硬币代替） |

## 用法

- 裁切：`ffmpeg -ss 3 -t 2 -i sfx/脚步/foot_echo_hall_536290.mp3 out.wav`，再在剪接时叠进时间轴。
- 程式里用：`example_D-7/assemble.py` 的 `LIB` 指向音效资料夹，可参考它怎么指定起点、长度、增益。
- 什么时候用 H3 原生音效、什么时候用这里的档：见 `docs/03_规则与踩坑.md` 第 6 节（**看得到脸的镜头不要用原生音效**，角色会自己嘟囔）。
- 要自己新增：到 Freesound 用 `license:"Creative Commons 0"` 筛选，下载后把编号、网址、授权写进 manifest.json。不要放非 CC0 或授权不明的档。
